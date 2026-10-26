const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('outputs/auto-ai.js', 'utf8');
const start = source.indexOf('        async function selectRecommendations');
const functions = source.slice(start, source.indexOf('        (async () => {', start));
const success = {recommended_options: ['A'], confidence: .9, explanation: '2'};

function fixture(respond) {
  const boxes = [], requests = [], submissions = [];
  const roots = [0, 1].map(() => ({isConnected: true, listeners: {},
    addEventListener(name, fn) { this.listeners[name] = fn; },
    appendChild(box) { boxes.push(box); }}));
  const questions = [0, 1].map(index => ({question: 'question' + index, type: '单选题',
    questionid: 'answer' + index, elementIndex: index, options: {length: 2, two: {value: 'A'}, three: {value: 'B'}}}));
  const stored = new Map();
  const context = {aiSelectionPaused: false, aiAnalysisRunning: false, questionsElement: roots,
    questionList: questions, questionNum: 2, selectionStatus: {textContent: '', isConnected: true},
    retryControl: {disabled: true}, courseId: 'c', classId: 'x', wid: 'w', getQueryVariable: () => 'w',
    _d: {createElement: () => ({style: {}, textContent: ''}), body: {appendChild: box => boxes.push(box)}},
    _w: {sessionStorage: {getItem: key => stored.get(key), setItem: (key, value) => stored.set(key, value)},
      submitCheckTimes: () => true, escapeBlank: () => true, submitAction: () => submissions.push('submit')},
    setTimeout: (fn, ms) => { if (ms !== 30000) fn(); }, console,
    GM_xmlhttpRequest: request => {
      assert.equal(request.timeout, 270000);
      assert.equal(request.url, 'http://127.0.0.1:8787/analyze');
      requests.push(JSON.parse(request.data).question);
      respond(request, requests.length);
    }};
  vm.createContext(context);
  vm.runInContext(functions, context);
  // Selection itself is covered by test_selection.cjs; exercise recovery and submission here.
  context.selectRecommendations = async (question, labels, root, touched) => {
    if (context.aiSelectionPaused || touched() || !root.isConnected) return '已暂停';
    question.aiVerify = () => !context.aiSelectionPaused && !touched() && root.isConnected;
    return '已核对';
  };
  return {context, boxes, requests, submissions, roots, questions};
}

(async () => {
  const recovered = fixture((request, count) => {
    request.onload({status: count === 1 ? 504 : 200, responseText: JSON.stringify(count === 1 ?
      {error: 'DeepSeek 响应超时；已尝试 3 次', code: 'upstream_timeout', retryable: true, attempts: 3} : success)});
  });
  await recovered.context.runAnalysisBatch();
  assert.equal(recovered.submissions.length, 0);
  assert.equal(recovered.context.retryControl.disabled, false);
  assert(recovered.boxes[0].textContent.includes('已尝试 3 次'));
  await recovered.context.runAnalysisBatch(true);
  assert.deepEqual(recovered.requests, ['question0', 'question1', 'question0']);
  assert.equal(recovered.boxes.length, 2, 'retry must reuse each existing message box');
  assert.equal(recovered.submissions.length, 1, 'submit only after the failed question recovers');
  assert.equal(recovered.context.retryControl.disabled, true);
  await recovered.context.runAnalysisBatch(true);
  assert.equal(recovered.submissions.length, 1);

  for (const mode of ['error', 'timeout', 'abort', 'throw', 'invalid']) {
    const failed = fixture(request => {
      if (mode === 'throw') throw Error();
      if (mode === 'invalid') request.onload({status: 200, responseText: '{}'});
      if (mode === 'error') request.onerror();
      if (mode === 'timeout') {
        request.ontimeout();
        // A late callback must not apply an answer after the request has settled.
        request.onload({status: 200, responseText: JSON.stringify(success)});
      }
      if (mode === 'abort') request.onabort();
    });
    await failed.context.runAnalysisBatch();
    assert.equal(failed.submissions.length, 0);
    assert(failed.questions.every(question => question.aiRequestFailed && !question.aiVerify));
    assert.equal(failed.requests.length, 2, 'browser must not multiply upstream automatic retries');
  }

  const manual = fixture((request, count) => count === 1 ? request.onerror() :
    request.onload({status: 200, responseText: JSON.stringify(success)}));
  await manual.context.runAnalysisBatch();
  manual.roots[0].listeners.click({isTrusted: true});
  await manual.context.runAnalysisBatch(true);
  assert.equal(manual.submissions.length, 0, 'manual changes made between attempts must remain protected');
  assert(manual.questions[0].aiTouched);

  let pending;
  const concurrent = fixture(request => { pending = request; });
  concurrent.context.questionList.length = 1;
  const running = concurrent.context.runAnalysisBatch();
  await concurrent.context.runAnalysisBatch(true);
  assert.equal(concurrent.requests.length, 1, 'double clicking cannot start a second batch');
  concurrent.context.aiSelectionPaused = true;
  pending.onerror();
  await running;
  await concurrent.context.runAnalysisBatch(true);
  assert.equal(concurrent.requests.length, 1);
  assert.equal(concurrent.submissions.length, 0);
  assert.equal(concurrent.context.retryControl.disabled, true);
  console.log('PASS: failure-only recovery, no repeated successful requests, bounded errors, late callbacks, manual changes, pause and duplicate guards.');
})().catch(error => { console.error(error); process.exitCode = 1; });
