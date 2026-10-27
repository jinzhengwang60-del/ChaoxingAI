const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('ui/chapter-panel.js','utf8');
const css=fs.readFileSync('ui/chapter-panel.css','utf8');
const userscript=fs.readFileSync('outputs/auto-ai.js','utf8');
function fixture(responseMode='success') {
  const nodes=new Map();
  const make=()=>({style:{},dataset:{},textContent:'',value:'',innerHTML:'',disabled:false,hidden:false,
    attrs:{},setAttribute(k,v){this.attrs[k]=v;}});
  const doc={activeElement:null,getElementById:id=>{if(!nodes.has(id))nodes.set(id,make());return nodes.get(id);},
    createElement:()=>{const node=make();Object.defineProperty(node,'innerHTML',{set(value){this.value=value.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');}});return node;}};
  const c={};vm.createContext(c);vm.runInContext('const CHAPTER_PANEL_CSS='+JSON.stringify(css)+';\n'+source,c);
  const panel=c.createChapterPanel(doc,{version:'4.1.0-ai'}), calls=[];
  const requestHealth=request=>{
    calls.push(request);
    assert.equal(request.url,'http://127.0.0.1:8787/health');assert.equal(request.method,'GET');
    if(responseMode==='success')request.onload({status:200,responseText:JSON.stringify({ok:true,service:'ChaoxingAI',configured:true})});
    if(responseMode==='configuration')request.onload({status:200,responseText:JSON.stringify({ok:true,service:'ChaoxingAI',configured:false})});
    if(responseMode==='wrong-service')request.onload({status:200,responseText:'{"ok":true,"service":"other"}'});
    if(responseMode==='invalid')request.onload({status:200,responseText:'{'});
    if(responseMode==='error')request.onerror();
    if(responseMode==='timeout')request.ontimeout();
    if(responseMode==='abort')request.onabort();
    if(responseMode==='throw')throw Error();
  };
  panel.mount({requestHealth});
  return{panel,doc,nodes,calls,get:id=>doc.getElementById(id)};
}
const ready=fixture();
assert(ready.get('cxai-health-text').textContent.includes('已连接'));
assert(!ready.get('cxai-health-text').textContent.includes('AI 已连接'));
for(const mode of ['configuration','wrong-service','invalid','error','timeout','abort','throw']){
  const f=fixture(mode);assert(!f.get('cxai-health-text').textContent.includes('已连接'));assert.equal(f.get('cxai-health-check').disabled,false);
}
const waiting=fixture('pending');waiting.get('cxai-health-check').onclick();assert.equal(waiting.calls.length,1);
waiting.calls[0].ontimeout();waiting.calls[0].onload({status:200,responseText:'{"ok":true,"service":"ChaoxingAI","configured":true}'});
assert(waiting.get('cxai-health-text').textContent.includes('检测超时'));
waiting.get('cxai-health-check').onclick();assert.equal(waiting.calls.length,2);
const tasks=[{type:'video',name:'课程视频',state:'done'},{type:'work',name:'章节测验',state:'running'},{type:'document',name:'讲义',state:'queued'}];
ready.panel.update({tasks,ready:true});
assert.equal(ready.get('cxai-progress').value,1);assert.equal(ready.get('cxai-progress').max,3);
assert.equal(ready.get('cxai-count-running').textContent,'1');assert.equal(ready.get('cxai-count-pending').textContent,'1');
assert.equal(ready.get('cxai-status-title').textContent,'正在处理章节测验');
ready.panel.update({tasks:[{type:'work',name:'<img src=x onerror=alert(1)>',state:'hold',detail:'缺少必要信息'}],ready:true});
assert(ready.get('joblist').innerHTML.includes('&lt;img'));
assert(!ready.get('joblist').innerHTML.includes('<img'));
assert(ready.get('cxai-status-title').textContent.includes('手动处理'));
ready.panel.update({tasks:[],ready:false,error:'任务数据解析失败'});assert(!ready.get('cxai-status-title').textContent.includes('完成'));
ready.panel.update({tasks:[],ready:true,jump:true});assert(ready.get('cxai-status-title').textContent.includes('没有待处理'));
ready.panel.update({tasks:[{type:'video',name:'视频',state:'done'}],ready:true});assert.equal(ready.get('cxai-status-title').textContent,'本页任务已完成');
ready.panel.settings({rate:1,review:false,assist:true});
ready.get('unrivalRate').value='2';ready.panel.settings({rate:1,review:false,assist:true});assert.equal(ready.get('unrivalRate').value,'2','periodic rendering must preserve an unsaved edit');
ready.doc.activeElement=ready.get('unrivalRate');ready.panel.settings({rate:3,review:true,assist:false});assert.equal(ready.get('unrivalRate').value,'2');
ready.doc.activeElement=null;ready.panel.settings({rate:3,review:true,assist:false});assert.equal(ready.get('unrivalRate').value,'3');
assert.equal(ready.get('reviewModeButton').attrs['aria-checked'],'true');assert.equal(ready.get('autoDoWorkButton').attrs['aria-checked'],'false');
for(let i=0;i<54;i++)ready.panel.logger.addLog('message '+i,'green');
assert.equal(ready.panel.logger.logArry.length,50);
assert.equal((ready.get('cxai-log-preview').innerHTML.match(/cxai-log-entry/g)||[]).length,3);
assert(ready.get('cxai-log-preview').innerHTML.indexOf('message 53')<ready.get('cxai-log-preview').innerHTML.indexOf('message 52'));
ready.panel.logger.addLog('<img src=x onerror=alert(1)>连接失败','red');assert.equal(ready.get('cxai-notice').hidden,false);
assert(!ready.get('log').innerHTML.includes('<img'));ready.get('cxai-dismiss-notice').onclick();assert.equal(ready.get('cxai-notice').hidden,true);
ready.panel.rateFeedback('倍速无效',true);assert.equal(ready.get('cxai-rate-feedback').dataset.tone,'error');
assert(ready.panel.html.includes('role="switch"'));assert(ready.panel.html.includes('title="当前章节测验"'));
assert(!ready.panel.html.includes('accuracy'));assert(!userscript.includes("getElementById('autoSubmitButton')"));
assert(!userscript.includes('等待手动作答'));assert(!userscript.includes("GM_getValue('accuracy'"));
console.log('PASS: task states and counts, error/empty states, local-only health checks, retry deduplication, edit preservation, safe text, log history and obsolete controls.');
