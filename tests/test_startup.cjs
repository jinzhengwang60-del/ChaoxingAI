const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('outputs/auto-ai.js','utf8');
function boot(withGrants){
 const nodes=[];
 const document={cookie:'',createElement:()=>({style:{},isConnected:false}),body:{appendChild:n=>{nodes.push(n);n.isConnected=true;}}};
 const context={document,console:{error:()=>{}},setInterval:()=>{},setTimeout:()=>{},clearInterval:()=>{}};
 if(withGrants){
  const win={document,location:{href:'https://mooc1.chaoxing.com/diagnostic',pathname:'/diagnostic',search:'',protocol:'https:',host:'mooc1.chaoxing.com'},navigator:{userAgent:'test'}};win.top=win;
  Object.assign(context,{unsafeWindow:win,GM_info:{scriptHandler:'ScriptCat'},GM_getValue:(_,fallback)=>fallback,GM_setValue:()=>{}});
 }
 vm.createContext(context);vm.runInContext(source,context,{timeout:2000});
 return nodes[0].textContent;
}
assert(boot(false).includes('运行中断：GM_getValue is not defined'));
assert(boot(true).includes('初始化完成；当前页面：/diagnostic'));
console.log('PASS: entire script boots with valid grants; missing grants produce visible startup error.');
