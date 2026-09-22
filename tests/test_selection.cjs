const fs=require('fs'),vm=require('vm'),assert=require('assert');
const s=fs.readFileSync('outputs/auto-ai.js','utf8');
assert(!s.includes("GM_setValue('unrivalautosubmit', '1')"));
const fn=s.slice(s.indexOf('        async function selectRecommendations'),s.indexOf('        async function analyzeQuestion'));
async function run(type,labels,{existing=false,touched=false,paused=false,bad=false,noEffect=false,shuffled=false,wrongClick=false,textMismatch=false,judgmentTexts=null}={}){
 let clicks=[];
 const options=type==='判断题'?['true','false']:['A','B','C'];
 const rows=options.map((label,i)=>({
  active:existing&&i===0,
  innerText:type==='判断题'?(judgmentTexts?judgmentTexts[i]:(i===0?'正确':'错误')):(bad?'A':label)+' '+(textMismatch?'changed':['one','two','three'][i]),
  getAttribute:k=>k==='id-param'?'1':label,
  getElementsByTagName:()=>[{innerText:type==='判断题'?(judgmentTexts?['A','B'][i]:(i===0?'正确':'错误')):(bad?'A':label),getAttribute:()=>shuffled?options[(i+1)%options.length]:label}],
  classList:{contains:()=>rows[i].active},querySelector:()=>null,matches:()=>false,
  click:()=>{clicks.push(label);if(!noEffect){if(type!=='多选题')rows.forEach(r=>r.active=false);const target=rows[wrongClick?(i+1)%rows.length:i];target.active=type==='多选题'?!target.active:true;}}
 }));
 const c={trim:text=>text.trim(),aiSelectionPaused:paused,setTimeout:cb=>cb()};vm.createContext(c);vm.runInContext(fn,c);
 const q={type,questionid:'answer1',options:{length:3,one:{value:'A'},two:{value:'B'},three:{value:'C'}}};
 const result=await c.selectRecommendations(q,labels,{isConnected:true,getElementsByTagName:()=>rows},()=>touched);
 return {clicks,result};
}
(async()=>{
 assert.deepEqual((await run('单选题',['B'])).clicks,['B']);
 assert.deepEqual((await run('多选题',['A','C'])).clicks,['A','C']);
 assert.deepEqual((await run('判断题',['false'])).clicks,['false']);
 for(const settings of [{touched:true},{paused:true},{bad:true}])assert.equal((await run('多选题',['A','C'],settings)).clicks.length,0);
 for(const labels of [[],['Z'],['A','A']])assert.equal((await run('多选题',labels)).clicks.length,0);
 assert.equal((await run('单选题',['A','B'])).clicks.length,0);
 const failed=await run('多选题',['A','C'],{noEffect:true});assert.deepEqual(failed.clicks,['A']);assert(failed.result.includes('未确认'));
 const shuffled=await run('单选题',['A'],{shuffled:true});assert.deepEqual(shuffled.clicks,['A']);assert(shuffled.result.includes('A one'));
 assert.equal((await run('单选题',['A'],{textMismatch:true})).clicks.length,0);
 const wrong=await run('单选题',['A'],{wrongClick:true});assert(wrong.result.includes('实际选中：B two'));assert(wrong.result.includes('暂停'));
 assert.deepEqual((await run('单选题',['B'],{existing:true})).clicks,['B']);
 assert.deepEqual((await run('判断题',['false'],{existing:true})).clicks,['false']);
 const replace=await run('多选题',['B','C'],{existing:true});assert.deepEqual(replace.clicks,['A','B','C']);assert(replace.result.includes('实际选中：B two；C three'));
 assert.deepEqual((await run('多选题',['A','C'],{existing:true})).clicks,['C']);
 assert.deepEqual((await run('单选题',['A'],{existing:true})).clicks,[]);
 const deselectFail=await run('多选题',['B'],{existing:true,noEffect:true});assert.deepEqual(deselectFail.clicks,['A']);assert(deselectFail.result.includes('暂停'));
 for (const judgmentTexts of [['A 对','B 错'],['A.正确','B.错误'],['A\n对','B\n错'],['A√','B×']]) {
 assert.deepEqual((await run('判断题',['true'],{judgmentTexts})).clicks,['true']);
 assert.deepEqual((await run('判断题',['false'],{judgmentTexts,existing:true})).clicks,['false']);
 }
 assert.deepEqual((await run('判断题',['true'],{judgmentTexts:['A 错','B 对']})).clicks,['false']);
 for(const judgmentTexts of [['A 对','B 对'],['A 不确定','B 错']]) assert.equal((await run('判断题',['true'],{judgmentTexts})).clicks.length,0);
 console.log('PASS: single/multiple/true-false selection; existing/manual/pause/mismatch/no-answer guards; failed click stops.');
})();
