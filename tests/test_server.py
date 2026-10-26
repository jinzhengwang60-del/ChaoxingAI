import sys, unittest, tempfile, threading, json
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0, str(Path('outputs').resolve()))
import server

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = server.CACHE
        server.CACHE = Path(self.temp.name)/'cache.sqlite3'
        self.data = {'question':'1+1=?','type':'单选题','options':[{'label':'A','text':'2'},{'label':'B','text':'3'}]}
        self.result = {'recommended_options':['A'],'confidence':0.9,'explanation':'加法计算得到 2。'}
    def tearDown(self):
        server.CACHE = self.old
        self.temp.cleanup()
    def test_cache_and_key(self):
        with patch.object(server,'call_model',return_value=self.result) as mock:
            self.assertFalse(server.analyze(self.data)['cached'])
            self.assertTrue(server.analyze(self.data)['cached'])
            for field,value in [('question','2+2=?'),('type','多选题'),('options',[{'label':'A','text':'4'},{'label':'B','text':'5'}])]:
                server.analyze(dict(self.data,**{field:value}))
            with patch.object(server,'MODEL','another-model'):
                server.analyze(self.data)
            self.assertEqual(mock.call_count,5)
    def test_bad_model_output(self):
        for change in [{'recommended_options':['C']},{'recommended_options':['A','B']},{'confidence':float('nan')},{'confidence':True},{'explanation':''}]:
            with self.assertRaises(server.ServiceError):
                server.check_result(dict(self.result,**change),self.data)
    def test_missing_key(self):
        with patch.object(server,'CONFIG',{}):
            with self.assertRaises(server.ServiceError) as error:
                server.analyze(self.data)
            self.assertEqual(error.exception.status,503)
    def test_http(self):
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=http.serve_forever,daemon=True); thread.start()
        url='http://127.0.0.1:'+str(http.server_port)
        def post(body, headers=None):
            return urlopen(Request(url+'/analyze',data=body,headers=headers or {'Content-Type':'application/json','X-Chaoxing-AI':'1'}))
        try:
            self.assertTrue(json.load(urlopen(url+'/health'))['ok'])
            with patch.object(server,'call_model',return_value=self.result):
                self.assertFalse(json.load(post(json.dumps(self.data).encode()))['cached'])
                self.assertTrue(json.load(post(json.dumps(self.data).encode()))['cached'])
            for body,headers,status in [(b'{',None,400),(b'[]',None,400),(b'{}',{'Content-Type':'application/json'},403)]:
                with self.assertRaises(HTTPError) as error: post(body,headers)
                self.assertEqual(error.exception.code,status)
            with patch.object(server,'call_model',side_effect=server.ServiceError(504,'模拟超时')):
                with self.assertRaises(HTTPError) as error:
                    post(json.dumps(dict(self.data,question='uncached')).encode())
                self.assertEqual(error.exception.code,504)
                detail = json.load(error.exception)
                self.assertEqual(detail['error'], '模拟超时')
                self.assertIn('retryable', detail)
                self.assertEqual(detail['attempts'], 1)
        finally:
            http.shutdown(); http.server_close(); thread.join()

if __name__ == '__main__':
    unittest.main(verbosity=2)
