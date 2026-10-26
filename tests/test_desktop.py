import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

sys.path.insert(0, str(Path('outputs').resolve()))
import desktop_core as core
import server


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.settings = {'DEEPSEEK_API_KEY': 'test-credential-only', 'DEEPSEEK_MODEL': core.DEFAULT_MODEL}

    def tearDown(self):
        self.temp.cleanup()

    def test_input_validation(self):
        self.assertEqual(core.validate_settings(' key ', ' model ')['DEEPSEEK_API_KEY'], 'key')
        for key, model in [('', 'model'), ('your_deepseek_api_key_here', 'model'), ('abc\ndef', 'model'),
                           ('非英文', 'model'), ('key', ''), ('key', 'bad model')]:
            with self.assertRaises(ValueError):
                core.validate_settings(key, model)

    @unittest.skipUnless(os.name == 'nt', 'Windows encryption')
    def test_encrypted_storage_roundtrip_and_corruption(self):
        store = core.SettingsStore(self.directory)
        self.assertIsNone(store.load())
        store.save(self.settings)
        self.assertEqual(store.load(), self.settings)
        self.assertNotIn(self.settings['DEEPSEEK_API_KEY'], store.path.read_text())
        store.path.write_text('{"format": 1, "key_protected": "damaged", "model": "x"}')
        with self.assertRaises(RuntimeError):
            store.load()

    @unittest.skipUnless(os.name == 'nt', 'Windows single-instance mutex')
    def test_duplicate_launcher_and_release(self):
        instance = core.SingleInstance(self.directory)
        try:
            with self.assertRaises(RuntimeError):
                core.SingleInstance(self.directory)
        finally:
            instance.close()
        second = core.SingleInstance(self.directory)
        second.close()

    def test_connection_is_real_request_not_cached(self):
        with patch.object(server, 'call_model', return_value={'recommended_options': ['A']}) as request:
            core.test_connection(self.settings)
            request.assert_called_once()
            self.assertEqual(request.call_args.kwargs['config'], self.settings)
        with patch.object(server, 'call_model', return_value={'recommended_options': []}):
            with self.assertRaises(server.ServiceError):
                core.test_connection(self.settings)

    def test_service_start_stop_health_and_bound_configuration(self):
        controller = core.ServiceController(self.directory, port=0)
        opener = build_opener(ProxyHandler({}))
        original = dict(server.CONFIG)
        result = {'recommended_options': ['A'], 'confidence': .9, 'explanation': '测试解释'}
        try:
            controller.start(self.settings)
            port = controller.port
            controller.start({'DEEPSEEK_API_KEY': 'different', 'DEEPSEEK_MODEL': 'other'})
            self.assertEqual(controller.port, port)
            self.assertTrue(controller.running)
            self.assertEqual(controller.probe(), 'ours')
            url = 'http://127.0.0.1:' + str(port)
            with opener.open(url + '/health') as response:
                health = json.load(response)
            self.assertEqual(health['model'], core.DEFAULT_MODEL)
            self.assertNotIn(self.settings['DEEPSEEK_API_KEY'], json.dumps(health))
            data = {'question': '1+1?', 'type': '单选题', 'options': [{'label': 'A', 'text': '2'}, {'label': 'B', 'text': '3'}]}
            def request():
                with opener.open(Request(url + '/analyze', data=json.dumps(data).encode(),
                        headers={'Content-Type': 'application/json', 'X-Chaoxing-AI': '1'})) as response:
                    return json.load(response)
            with patch.object(server, 'call_model', return_value=result) as ai:
                self.assertFalse(request()['cached'])
                self.assertTrue(request()['cached'])
                self.assertEqual(ai.call_count, 1)
                self.assertEqual(ai.call_args.kwargs['config'], self.settings)
            self.assertEqual(server.CONFIG, original)
            duplicate = core.ServiceController(self.directory, port=port)
            with self.assertRaisesRegex(RuntimeError, '已有本地服务'):
                duplicate.start(self.settings)
            self.assertTrue(controller.running)
        finally:
            controller.stop()
            controller.stop()
        self.assertFalse(controller.running)

    def test_upstream_errors_are_readable_without_leaking_response(self):
        data = {'question': 'x', 'type': '单选题', 'options': [{'label': 'A', 'text': 'x'}, {'label': 'B', 'text': 'y'}]}
        for status, expected in [(401, '密钥无效'), (402, '余额或额度不足'), (404, '模型不存在'), (429, '过于频繁')]:
            with patch.object(server.time, 'sleep'), patch.object(server, 'urlopen', side_effect=HTTPError('https://api.deepseek.com', status, 'secret upstream body', None, None)):
                with self.assertRaises(server.ServiceError) as error:
                    server.call_model(data, config=self.settings)
                self.assertIn(expected, error.exception.message)
                self.assertNotIn('secret', error.exception.message)


if __name__ == '__main__':
    unittest.main(verbosity=2)
