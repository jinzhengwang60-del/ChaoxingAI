// Bundled into the userscript by packaging/build_panel.py. No external UI dependencies.
function createChapterPanel(doc, options = {}) {
    const escape = value => String(value ?? '').replace(/[&<>"']/g, char =>
        ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
    const paths = {
        book: '<path d="M4 4.5h6a3 3 0 0 1 2 1 3 3 0 0 1 2-1h6v15h-6a3 3 0 0 0-2 1 3 3 0 0 0-2-1H4z"/><path d="M12 6v14M7 8h2M15 8h2M7 12h2M15 12h2"/>',
        play: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="m10 8 6 4-6 4z"/>',
        work: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M9 10l2 2 4-4M9 17h6"/>',
        document: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h6"/>',
        check: '<path d="m7 12 3 3 7-7"/><circle cx="12" cy="12" r="9"/>',
        clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
        refresh: '<path d="M20 10a8 8 0 0 0-14-4L3 9m0-5v5h5M4 14a8 8 0 0 0 14 4l3-3m0 5v-5h-5"/>',
        down: '<path d="m7 10 5 5 5-5"/>'
    };
    const icon = name => '<svg viewBox="0 0 24 24" aria-hidden="true">' + (paths[name] || paths.clock) + '</svg>';
    const version = escape(options.version || '4.1.0-ai');
    const html = `<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ChaoxingAI 学习助手</title><style>${CHAPTER_PANEL_CSS}</style></head>
<body class="cxai-panel-body"><main id="cxai-panel" aria-label="ChaoxingAI 学习助手">
  <header class="cxai-header"><div class="cxai-brand"><div class="cxai-brand-mark">${icon('book')}</div><div><h1>ChaoxingAI <span class="cxai-version">v${version}</span></h1><div class="cxai-brand-sub">学习助手 · 专注当前这一节</div></div></div>
    <div class="cxai-health-group"><span class="cxai-health" id="cxai-health" data-tone="neutral"><span class="cxai-dot"></span><span id="cxai-health-text">本地服务 · 待检测</span></span><button type="button" id="cxai-health-check" class="cxai-text-button">${icon('refresh')}检测连接</button></div></header>
  <aside id="cxai-notice" class="cxai-notice" hidden role="status"><span id="cxai-notice-text"></span><button type="button" id="cxai-dismiss-notice" aria-label="收起这条提示">×</button></aside>
  <section class="cxai-overview" aria-label="当前任务状态"><div class="cxai-overview-top"><div class="cxai-state-icon" id="cxai-state-icon">${icon('clock')}</div><div><p class="cxai-eyebrow">当前状态</p><h2 id="cxai-status-title">正在识别本页任务</h2><p id="cxai-status-detail">任务加载后会自动更新，学习通右侧目录仍可正常使用。</p></div></div>
    <div class="cxai-progress-head"><span>本页进度</span><span id="cxai-progress-label">等待任务数据</span></div><progress id="cxai-progress" max="1" value="0" aria-label="本页任务完成情况"></progress>
    <div class="cxai-metrics"><span>任务总数<strong id="cxai-count-total">—</strong></span><span>进行中<strong id="cxai-count-running">—</strong></span><span>待处理<strong id="cxai-count-pending">—</strong></span></div>
  </section>
  <section class="cxai-section" aria-labelledby="cxai-tasks-heading"><div class="cxai-section-head"><h2 id="cxai-tasks-heading">本页任务</h2><span class="cxai-caption" id="cxai-task-caption">按课程任务顺序处理</span></div><div id="joblist"><div class="cxai-empty">${icon('clock')}正在读取任务信息…</div></div></section>
  <section class="cxai-section" id="normalQuery" aria-labelledby="cxai-settings-heading"><div class="cxai-section-head"><h2 id="cxai-settings-heading">常用设置</h2><span class="cxai-caption">设置保存在当前浏览器</span></div>
    <div class="cxai-settings-grid"><div class="cxai-setting"><label for="unrivalRate" class="cxai-setting-title">视频倍速</label><div class="cxai-rate-controls"><div class="cxai-rate-field"><input type="number" min="0.5" max="16" step="0.25" id="unrivalRate" aria-describedby="cxai-rate-feedback"><span class="cxai-rate-unit">×</span></div><button type="button" id="updateRateButton">应用</button></div><div id="cxai-rate-feedback" role="status">建议使用 1 倍速，进度以平台记录为准。</div></div>
      <div class="cxai-setting"><div class="cxai-setting-title" id="cxai-review-label">复习模式</div><div class="cxai-setting-label"><span id="cxai-review-state" class="cxai-setting-state">已关闭</span><button type="button" id="reviewModeButton" class="cxai-switch" role="switch" aria-checked="false" aria-labelledby="cxai-review-label"></button></div><p class="cxai-setting-help">开启后重新处理已完成的视频。</p></div>
      <div class="cxai-setting"><div class="cxai-setting-title" id="cxai-assist-label">AI 辅助测验</div><div class="cxai-setting-label"><span id="cxai-assist-state" class="cxai-setting-state">已开启</span><button type="button" id="autoDoWorkButton" class="cxai-switch" role="switch" aria-checked="true" aria-labelledby="cxai-assist-label"></button></div><p class="cxai-setting-help">显示建议、核对选择并提交。</p></div></div>
    <div class="cxai-policy">${icon('info')}<span>全部题目选择核对通过后，倒计时 5 秒提交；可在题目页暂停。AI 建议不保证正确。</span></div>
    <details class="cxai-more-settings"><summary>更多说明与辅助功能 ${icon('down')}</summary><div class="cxai-more-body"><p>AI 开关对接下来打开的测验生效；已经打开的题目请在题目页暂停。恢复失败请求时，使用题目页的“重试失败题目”。</p><p>“检测连接”只检查本地服务，不调用收费 AI；DeepSeek 的可用性以实际分析结果为准。</p><a id="fuckMeModeButton" class="cxai-secondary-button" href="https://scriptcat.org/script-show-page/379" target="_blank" rel="noopener">后台播放辅助</a><button type="button" id="backGround" class="cxai-secondary-button">激活播放辅助</button><p>播放辅助沿用原脚本功能，不保证最小化后的运行效果。</p></div></details>
  </section>
  <section class="cxai-section" aria-labelledby="cxai-log-heading"><div class="cxai-section-head"><h2 id="cxai-log-heading">运行记录</h2><span class="cxai-caption">最近 3 条</span></div><div id="cxai-log-preview" class="cxai-log-preview"><div class="cxai-empty">准备就绪后，运行记录会显示在这里。</div></div><details id="cxai-log-details"><summary><span>查看完整记录 <span id="cxai-log-count">0</span></span>${icon('down')}</summary><div id="result"><div id="log"></div></div></details></section>
  <section class="cxai-section" id="workPanel" style="display:none;height:1000px"><div class="cxai-section-head"><h2>章节测验</h2><span class="cxai-caption">请留意题目页的核对结果</span></div><div id="workWindow"><iframe id="frame_content" name="frame_content" title="当前章节测验" src="about:blank" scrolling="auto"></iframe></div></section>
  <section class="cxai-section" id="videoTime" style="display:none"><div class="cxai-section-head"><h2>学习进度</h2></div><iframe id="videoTimeContent" title="课程学习进度" src="about:blank"></iframe></section>
  <footer class="cxai-footer"><span>仅展示当前页面识别到的任务 · 进度以课程平台为准</span><a href="https://github.com/jinzhengwang60-del/ChaoxingAI" target="_blank" rel="noopener">使用说明与反馈 ↗</a></footer>
</main></body>`;
    const get = id => doc.getElementById(id);
    let mounted = false, taskFingerprint = '', viewFingerprint = '', latestState = null, refreshingHealth = false, renderedRate;
    const entries = [];
    const typeNames = {video: '课程视频', document: '课程文档', work: '章节测验', workid: '章节测验'};
    const stateNames = {loading: '读取中', queued: '等待中', running: '进行中', done: '已完成', hold: '待处理'};
    const plainText = raw => {
        const text = String(raw ?? '').replace(/<a\b[^>]*href=["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi, (_, url, label) =>
            label.replace(/<[^>]*>/g, '') + (/^(https?:\/\/|unrivalxxtbackground\/)/i.test(url) ? '（' + url + '）' : ''))
            .replace(/<[^>]*>/g, '').replace(/\u00a0/g, ' ');
        const decoder = doc.createElement('textarea');
        decoder.innerHTML = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return decoder.value.slice(0, 2400);
    };
    function renderLogs() {
        if (!get('log')) return;
        const markup = list => list.map(entry => '<div class="cxai-log-entry" data-level="' + entry.level + '"><time class="cxai-log-time">' +
            escape(entry.time) + '</time><span class="cxai-log-body">' + escape(entry.text) + '</span></div>').join('');
        get('log').innerHTML = markup(entries);
        get('cxai-log-preview').innerHTML = markup(entries.slice(-3).reverse());
        get('cxai-log-count').textContent = String(entries.length);
        get('result').scrollTop = get('result').scrollHeight;
    }
    function addLog(message, color = 'black') {
        const level = color === 'red' ? 'error' : color === 'orange' ? 'warning' : color === 'green' ? 'success' : 'info';
        const now = new Date();
        entries.push({text: plainText(message), level, time: [now.getHours(), now.getMinutes(), now.getSeconds()].map(x => String(x).padStart(2, '0')).join(':')});
        if (entries.length > 50) entries.shift();
        renderLogs();
        if (level === 'error' || (level === 'warning' && /暂停|失败|无法|待手动|未就绪|格式|多个/.test(entries[entries.length - 1].text)))
            notice(entries[entries.length - 1].text, level);
    }
    function notice(text, level = 'warning') {
        if (!get('cxai-notice')) return;
        get('cxai-notice').hidden = false;
        get('cxai-notice').dataset.level = level;
        get('cxai-notice-text').textContent = text;
    }
    function settings({rate, review, assist}) {
        if (!get('unrivalRate')) return;
        if (renderedRate !== rate && doc.activeElement !== get('unrivalRate')) {
            get('unrivalRate').value = String(rate);
            renderedRate = rate;
        }
        get('reviewModeButton').setAttribute('aria-checked', String(!!review));
        get('autoDoWorkButton').setAttribute('aria-checked', String(!!assist));
        get('cxai-review-state').textContent = review ? '已开启' : '已关闭';
        get('cxai-assist-state').textContent = assist ? '已开启' : '已关闭';
    }
    function update(state) {
        latestState = state;
        if (!mounted) return;
        const nextView = JSON.stringify(state);
        if (nextView === viewFingerprint) return;
        viewFingerprint = nextView;
        const tasks = state.tasks || [], done = tasks.filter(task => task.state === 'done').length;
        const running = tasks.filter(task => task.state === 'running');
        const held = tasks.filter(task => task.state === 'hold');
        const loading = tasks.some(task => task.state === 'loading') || state.loading;
        const active = running[0];
        let title = '任务已就绪，等待开始', detail = '任务将按当前课程顺序处理。', stateIcon = 'clock';
        if (state.error) { title = '任务信息暂不可用'; detail = state.error; stateIcon = 'info'; }
        else if (active) { title = '正在处理' + (typeNames[active.type] || '课程任务'); detail = active.detail || active.name; stateIcon = active.type === 'work' || active.type === 'workid' ? 'work' : active.type === 'document' ? 'document' : 'play'; }
        else if (held.length) { title = '有任务需要手动处理'; detail = held[0].detail || held[0].name; stateIcon = 'info'; }
        else if (loading) { title = '正在读取任务信息'; detail = '加载完成后，任务状态会自动更新。'; }
        else if (tasks.length && done === tasks.length) { title = '本页任务已完成'; detail = state.jump ? '正在等待进入下一节，进度以课程平台为准。' : '本页识别到的任务均已完成。'; stateIcon = 'check'; }
        else if (state.ready && !tasks.length) { title = '本页没有待处理任务'; detail = state.jump ? '正在等待进入下一节。' : '可以通过课程目录查看其他章节。'; stateIcon = 'check'; }
        get('cxai-status-title').textContent = title;
        get('cxai-status-detail').textContent = detail;
        get('cxai-state-icon').innerHTML = icon(stateIcon);
        get('cxai-count-total').textContent = state.ready ? String(tasks.length) : '—';
        get('cxai-count-running').textContent = state.ready ? String(running.length) : '—';
        get('cxai-count-pending').textContent = state.ready ? String(tasks.length - done - running.length) : '—';
        get('cxai-progress').max = tasks.length || 1;
        get('cxai-progress').value = done;
        get('cxai-progress-label').textContent = state.ready ? (tasks.length ? done + ' / ' + tasks.length + ' 已完成' : '无待处理任务') : '等待任务数据';
        get('cxai-task-caption').textContent = held.length ? held.length + ' 项需要处理' : '按课程任务顺序处理';
        const fingerprint = JSON.stringify([tasks, !!state.ready, state.error]);
        if (fingerprint === taskFingerprint) return;
        taskFingerprint = fingerprint;
        get('joblist').innerHTML = tasks.length ? tasks.map(task => '<div class="cxai-task" data-state="' + escape(task.state) + '" data-type="' + escape(task.type) + '"><span class="cxai-task-icon">' +
            icon(task.state === 'done' ? 'check' : task.type === 'workid' ? 'work' : task.type === 'video' ? 'play' : task.type) + '</span><div class="cxai-task-copy"><div class="cxai-task-name">' + escape(task.name) +
            '</div><div class="cxai-task-detail">' + escape(task.detail || typeNames[task.type] || '课程任务') + '</div></div><span class="cxai-task-badge">' + escape(stateNames[task.state] || '等待中') + '</span></div>').join('') :
            '<div class="cxai-empty">' + icon(state.error ? 'info' : state.ready ? 'check' : 'clock') + escape(state.error || (state.ready ? '本页没有待处理的课程任务。' : '正在读取任务信息…')) + '</div>';
    }
    function mount({requestHealth} = {}) {
        mounted = true;
        get('cxai-dismiss-notice').onclick = () => { get('cxai-notice').hidden = true; };
        const checkHealth = () => {
            if (refreshingHealth || !requestHealth) return;
            refreshingHealth = true;
            const button = get('cxai-health-check');
            button.disabled = true;
            get('cxai-health-text').textContent = '正在检测本地服务';
            let settled = false;
            const finish = (text, tone) => {
                if (settled) return;
                settled = true;
                refreshingHealth = false;
                button.disabled = false;
                get('cxai-health-text').textContent = text;
                get('cxai-health').dataset.tone = tone;
            };
            try {
                requestHealth({method: 'GET', url: 'http://127.0.0.1:8787/health', timeout: 4000,
                    onload: response => {
                        try {
                            const data = JSON.parse(response.responseText);
                            if (response.status !== 200 || data.ok !== true || data.service !== 'ChaoxingAI') { finish('本地服务 · 状态异常', 'warning'); return; }
                            finish(data.configured === false ? '本地服务 · 待配置密钥' : '本地服务 · 已连接', data.configured === false ? 'warning' : 'success');
                        } catch (_) { finish('本地服务 · 响应异常', 'warning'); }
                    },
                    onerror: () => finish('本地服务 · 未连接', 'warning'),
                    ontimeout: () => finish('本地服务 · 检测超时', 'warning'),
                    onabort: () => finish('本地服务 · 检测已取消', 'neutral')});
            } catch (_) { finish('本地服务 · 未连接', 'warning'); }
        };
        get('cxai-health-check').onclick = checkHealth;
        checkHealth();
        renderLogs();
        if (latestState) update(latestState);
    }
    function rateFeedback(text, failed = false) {
        get('cxai-rate-feedback').textContent = text;
        get('cxai-rate-feedback').dataset.tone = failed ? 'error' : 'success';
    }
    return {html, mount, update, settings, notice, rateFeedback, logger: {logArry: entries, addLog}};
}

function styleQuestionControls(doc, selectionControl, retryControl, selectionStatus, onStatus) {
    const style = doc.createElement('style');
    style.textContent = CHAPTER_PANEL_CSS;
    (doc.head || doc.body).appendChild(style);
    const wrapper = doc.createElement('section');
    wrapper.className = 'cxai-question-controls';
    wrapper.setAttribute('aria-label', 'AI 测验操作');
    const actions = doc.createElement('div');
    actions.className = 'cxai-question-actions';
    const label = doc.createElement('strong');
    label.textContent = '章节测验 · AI 辅助';
    actions.append(label, selectionControl, retryControl);
    wrapper.append(actions, selectionStatus);
    doc.body.prepend(wrapper);
    const Observer = doc.defaultView?.MutationObserver;
    if (Observer && onStatus) {
        const report = () => onStatus(selectionControl.disabled ? '自动选择与提交已暂停，请手动核对。' : selectionStatus.textContent);
        const observer = new Observer(report);
        observer.observe(wrapper, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['disabled']});
        report();
    }
}
