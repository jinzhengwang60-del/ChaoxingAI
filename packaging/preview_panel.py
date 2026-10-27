"""Serve an isolated course fixture; all userscript requests are mocked in the frame."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DATA = {'defaults': {'clazzId': 'demo-class', 'knowledgeid': 'demo-chapter',
        'reportUrl': '/preview-only', 'userid': 'demo-user', 'fid': 'demo-school', 'ktoken': 'demo'},
    'attachments': [
        {'type': 'video', 'job': True, 'jobid': 'demo-video', 'isPassed': False,
         'property': {'name': '金融如何支持实体经济.mp4', 'objectid': 'demo-object', 'module': 'video', 'doublespeed': 1}},
        {'type': 'document', 'job': True, 'jobid': 'demo-document', 'isPassed': True, 'property': {'name': '本节学习资料'}},
        {'type': 'workid', 'job': True, 'jobid': 'work-demo', 'isPassed': False, 'enc': 'demo-only',
         'property': {'name': '章节测验', 'title': '本节知识巩固', 'workid': 'demo'}}]}

MOCKS = r'''
window.unsafeWindow=window;
window.GM_info={scriptHandler:'ScriptCat'};
const saved={unrivalrate:'1',unrivalreview:'0',unrivalAiAssistEnabled:'1'};
window.GM_getValue=(key,fallback)=>Object.hasOwn(saved,key)?saved[key]:fallback;
window.GM_setValue=(key,value)=>{saved[key]=value};
window.GM_addValueChangeListener=()=>0;
window.top.unrivalScriptList=['preview'];
window.top.unrivalReviewMode='0';
window.top.jump=false;
window.GM_xmlhttpRequest=request=>{
  if(request.url==='http://127.0.0.1:8787/health'){
    request.onload({status:200,responseText:JSON.stringify({ok:true,service:'ChaoxingAI',configured:true,version:'1.0.1'})});
  }else if(request.url.includes('/ananas/status/')){
    request.onload({status:200,responseText:JSON.stringify({duration:960,dtoken:'preview-only'})});
  }
  // No request is sent to a course platform, local AI service, or DeepSeek.
  return {abort(){}};
};
const realInterval=window.setInterval.bind(window);
window.setInterval=(callback,delay,...args)=>{
  if(callback.name==='refreshChapterPanel')return 0;
  return realInterval(callback,delay,...args);
};
function showPreview(state='video'){
  const panel=window.cxaiPreviewPanel;
  if(!panel){setTimeout(()=>showPreview(state),30);return}
  const tasks=[{type:'video',name:'金融如何支持实体经济.mp4',state:'running'},
    {type:'document',name:'本节学习资料',state:'done'},
    {type:'work',name:'本节知识巩固',state:'queued'}];
  if(state==='work'){tasks[0].state='done';tasks[2].state='running'}
  if(state==='complete')tasks.forEach(task=>task.state='done');
  if(state==='hold'){tasks[0].state='done';tasks[2].state='hold';tasks[2].detail='AI 辅助已关闭，开启后刷新课程页重新识别。'}
  if(state==='empty')tasks.length=0;
  panel.update({tasks,ready:true,jump:false});
  panel.logger.logArry.length=0;
  panel.logger.addLog('已识别本页课程任务。');
  panel.logger.addLog('本节学习资料已完成。','green');
  panel.logger.addLog(state==='work'?'正在获取章节测验的 AI 建议。':state==='complete'?'本页任务已完成。':state==='hold'?'有测验任务需要手动处理。':'视频任务进行中，进度以课程平台记录为准。',state==='complete'?'green':'black');
  document.querySelector('#cxai-notice').hidden=true;
  if(state==='error'){
    panel.logger.addLog('DeepSeek 响应超时；已尝试 3 次。恢复后可在题目页重试失败题目。','red');
    document.querySelector('#cxai-health-text').textContent='本地服务 · 已连接';
  }
}
window.addEventListener('message',event=>{if(event.origin===location.origin&&event.data?.kind==='cxai-preview')showPreview(event.data.state)});
setTimeout(showPreview,650);
'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        content_type = 'text/html; charset=utf-8'
        if path in ('/', '/preview.html'):
            body = (ROOT / 'ui/preview.html').read_text(encoding='utf-8')
        elif path == '/knowledge/cards':
            argument = 'mArg = "";\ntry{\n    mArg = ' + json.dumps(DATA, ensure_ascii=False) + ';\n}catch(e){\n}'
            body = '<!doctype html><html><head><meta charset="utf-8"></head><body><script>' + argument + '</script><script>' + MOCKS + '</script><script src="/assets/userscript.js"></script></body></html>'
        elif path == '/assets/userscript.js':
            body = (ROOT / 'outputs/auto-ai.js').read_text(encoding='utf-8')
            before = 'const chapterPanel = createChapterPanel(_d, {version: AI_SCRIPT_VERSION});'
            body = body.replace(before, before + '\n        window.cxaiPreviewPanel = chapterPanel;', 1)
            content_type = 'text/javascript; charset=utf-8'
        elif path.startswith('/work/'):
            body = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><body style="font:14px system-ui;color:#7c8da7;padding:30px">章节测验预览区域；此处不加载真实课程。</body></html>'
        else:
            self.send_error(404)
            return
        raw = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8879)
    args = parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as http:
        print('Isolated panel preview: http://127.0.0.1:' + str(http.server_port), flush=True)
        http.serve_forever()


if __name__ == '__main__':
    main()
