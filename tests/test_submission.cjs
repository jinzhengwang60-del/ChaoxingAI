const fs=require('fs'),vm=require('vm'),assert=require('assert');
const s=fs.readFileSync('outputs/auto-ai.js','utf8');
const fn=s.slice(s.indexOf('        async function submitVerifiedAnswers'),s.indexOf('        (async () => {',s.indexOf('        async function submitVerifiedAnswers')));
async function run({bad=false,missing=false,duplicate=false,pause=false,changed=false,denied=false,throwing=false,storage=false,incomplete=false}={}) {
 let calls=[],timers=0,checked=true;
 const status={textContent:'',isConnected:true};
 const c={aiSelectionPaused:false,questionNum:1,questionsElement:{length:1},questionList:incomplete?[]:[{questionid:'answer1',aiVerify:()=>!bad&&checked}],courseId:'c',classId:'x',wid:'w',getQueryVariable:()=> 'w',selectionStatus:status,console:{error:()=>{}},
  setTimeout:(cb,ms)=>{if(ms===1000){timers++;if(pause)c.aiSelectionPaused=true;if(changed)checked=false;cb();}},
  _w:{sessionStorage:{getItem:()=>{if(storage)throw Error();return duplicate?'attempted':null;},setItem:()=>calls.push('persist')},submitCheckTimes:()=>{calls.push('check');return !denied;},escapeBlank:()=>{calls.push('blank');return true;},submitAction:()=>{calls.push('submit');if(throwing)throw Error();}}};
 if(missing)delete c._w.submitAction;
 vm.createContext(c);vm.runInContext(fn,c);await c.submitVerifiedAnswers();
 return {calls,timers,status};
}
(async()=>{
 const ok=await run();assert.deepEqual(ok.calls,['persist','check','blank','submit']);assert.equal(ok.timers,5);
 for(const settings of [{bad:true},{missing:true},{duplicate:true},{pause:true},{changed:true},{storage:true},{incomplete:true}])assert(!(await run(settings)).calls.includes('submit'));
 assert.deepEqual((await run({denied:true})).calls,['persist','check']);
 assert((await run({throwing:true})).status.textContent.includes('尚未确认成功'));
 assert(!s.includes("_w.confirm ="));
 console.log('PASS: one verified submission, countdown, invalid/incomplete/paused/changed answers block, storage/retry protection, website rejection and exception handling.');
})();
