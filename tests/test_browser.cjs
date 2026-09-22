const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const src = fs.readFileSync('outputs/auto-ai.js','utf8').replace(/\r\n/g,'\n');
const original = fs.readFileSync('source/auto.js','utf8').replace(/\r\n/g,'\n');
assert(!src.includes("GM_setValue('unrivalautosubmit', '1')"));
assert(!src.includes('_w.confirm ='));
assert(src.includes('randomDo = 0'));
const extract = s => s.slice(s.indexOf('        var questionList = [],'),s.indexOf('        var qu = null,') >= 0 ? s.indexOf('        var qu = null,') : s.indexOf("        aiStartupStatus('已识别 " ));
assert.equal(extract(src).replace("'elementIndex': i,\n                ",''),extract(original));
const start = src.indexOf('        async function selectRecommendations');
const end = src.indexOf('        (async () => {',start);
const fn = 'let aiSelectionPaused = false;\n' + src.slice(start,end);
(async () => {
  for (const mode of ['success','invalid','error','timeout','abort','throw']) {
    const boxes=[];
    let clicks=0;
    const context={_d:{createElement:()=>({style:{},textContent:''}),body:{appendChild:b=>boxes.push(b)}},
      questionsElement:[{appendChild:b=>boxes.push(b),click:()=>clicks++,addEventListener:()=>{},removeEventListener:()=>{}}],
      GM_xmlhttpRequest:request=>{
        assert.equal(request.url,'http://127.0.0.1:8787/analyze');
        const body=JSON.parse(request.data); assert.equal(body.question,'test');
        if(mode==='throw') throw Error();
        if(mode==='success') request.onload({status:200,responseText:JSON.stringify({recommended_options:['A'],confidence:.8,explanation:'<img onerror=alert(1)>'})});
        if(mode==='invalid') request.onload({status:200,responseText:'{}'});
        if(mode==='error') request.onerror();
        if(mode==='timeout') request.ontimeout();
        if(mode==='abort') request.onabort();
      }};
    vm.createContext(context);
    vm.runInContext(fn,context);
    await context.analyzeQuestion({question:'test',type:'单选题',options:{length:2,'one':{value:'A'},'two':{value:'B'}}},0);
    assert.equal(clicks,0); assert.equal(boxes.length,1);
    assert(boxes[0].textContent.includes(mode==='success'?'AI 推荐：A':'AI 暂无建议'));
    assert(!('innerHTML' in boxes[0]));
  }
  console.log('PASS: preserved extraction; six display-only response scenarios.');
})();
