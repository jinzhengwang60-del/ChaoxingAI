const fs=require('fs'), vm=require('vm'), assert=require('assert');
const s=fs.readFileSync('outputs/auto-ai.js','utf8').replace(/\r\n/g,'\n');
const helper=s.slice(s.indexOf('        // Identify chapter tests'),s.indexOf("        for (let i = 0, l = pageData['attachments'].length"));
const filter=s.slice(s.indexOf("        for (let i = 0, l = pageData['attachments'].length"),s.indexOf('        var video_getReady'));
const dispatch=s.slice(s.indexOf('        for (let i = 0, l = jobList.length'),s.indexOf('        loopjob();',s.indexOf('        for (let i = 0, l = jobList.length')));
const scheduler='const loopjob = '+s.slice(s.indexOf('            loopjob = () => {')+'            loopjob = '.length,s.indexOf('            readyCheck =')).trim().replace(/,$/,';');
const init=s.split('\n').find(x=>x.includes('_w.top.unrivalDoWork = GM_getValue') || x.includes('_w.top.unrivalDoWork = String'));
assert(init.includes('unrivalAiAssistEnabled'));
function scenario(item,enabled='1') {
  let opened=[],logs=[],rows=[];
  const c={_w:{top:{unrivalDoWork:enabled,unrivalReviewMode:'0',unrivalScriptList:[],jump:false}},
    _d:{createElement:()=>({}),getElementById:()=>({innerHTML:'',appendChild:r=>rows.push(r)})},
    logs:{addLog:m=>logs.push(m)},pageData:{attachments:[item]},jobList:[],missionList:[],
    isCat:true,cVersion:999,stop:false,busyThread:0,jumpType:1,
    setTimeout:()=>{},clearInterval:()=>{},video_getReady:()=>{},doVideo:()=>{},doDocument:()=>{},doWork:x=>opened.push(x)};
  vm.createContext(c);
  vm.runInContext(helper+filter+dispatch+scheduler+'\nloopjob();',c);
  return {c,opened,rows,logs};
}
const base={type:'workid',job:true,isPassed:false,jobid:'work-123',enc:'fixture',property:{workid:'123',title:'章节检测'}};
let r=scenario(base);assert.equal(r.opened.length,1);assert.equal(r.c._w.top.jump,false);
for(const item of [{...base,type:'work'},{...base,type:'new-type'},{...base,job:false},{...base,jobid:undefined},{...base,property:{title:'检测'}}]){
  r=scenario(item);assert.equal(r.opened.length,1);assert.equal(r.c._w.top.jump,false);
}
r=scenario(base,'0');assert.equal(r.opened.length,0);assert.equal(r.rows.length,1);assert.equal(r.c._w.top.jump,false);
r=scenario({...base,enc:undefined});assert.equal(r.opened.length,0);assert.equal(r.c._w.top.jump,false);
r=scenario({type:'unknown',job:true,property:{name:'unknown'}});assert.equal(r.c._w.top.jump,false);assert.equal(r.rows.length,1);
for(const passed of [true,1,'1','true']){
  r=scenario({...base,isPassed:passed});assert.equal(r.opened.length,0);
}
const c={_w:{top:{}},GM_getValue:(key,fallback)=>key==='unrivaldowork'?'0':fallback};vm.createContext(c);vm.runInContext(init,c);assert.equal(c._w.top.unrivalDoWork,'1');
console.log('PASS: chapter detection, disabled/unknown/incomplete tasks hold, completed filtering, legacy disabled setting isolation.');
