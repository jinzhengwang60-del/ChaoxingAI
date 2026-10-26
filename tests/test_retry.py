"""Network recovery tests use fake credentials and never contact DeepSeek."""
from email.message import Message
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, ProxyHandler

sys.path.insert(0, str(Path('outputs').resolve()))
import server


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.settings = {'DEEPSEEK_API_KEY': 'test-not-a-real-key', 'DEEPSEEK_MODEL': 'deepseek-flash'}
        self.data = {'question': '1+1=?', 'type': '单选题',
                     'options': [{'label': 'A', 'text': '2'}, {'label': 'B', 'text': '3'}]}
        self.result = {'recommended_options': ['A'], 'confidence': .9, 'explanation': '2'}
        self.sleep = patch.object(server.time, 'sleep').start()
        self.addCleanup(patch.stopall)
        patch.object(server.random, 'uniform', return_value=0).start()

    def response(self, content=None):
        raw = {'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(self.result) if content is None else content}}]}
        return BytesIO(b'\n \n' + json.dumps(raw).encode())

    def http_error(self, status, retry_after=None):
        headers = Message()
        if retry_after is not None:
            headers['Retry-After'] = str(retry_after)
        return HTTPError('https://api.deepseek.com', status, 'private-upstream-body', headers, BytesIO())

    def test_timeout_then_success(self):
        response = self.response()
        with patch.object(server, 'urlopen', side_effect=[TimeoutError(), response]) as network:
            self.assertEqual(server.call_model(self.data, config=self.settings), self.result)
        self.assertEqual(network.call_count, 2)
        self.sleep.assert_called_once_with(2)
        self.assertTrue(response.closed)

    def test_transient_http_errors_retry(self):
        for status in (408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                self.sleep.reset_mock()
                error = self.http_error(status)
                with patch.object(server, 'urlopen', side_effect=[error, self.response()]) as network:
                    self.assertEqual(server.call_model(self.data, config=self.settings), self.result)
                self.assertEqual(network.call_count, 2)
                self.sleep.assert_called_once_with(2)
                self.assertTrue(error.fp.closed)

    def test_permanent_errors_do_not_retry(self):
        for status in (400, 401, 402, 403, 404, 422):
            with self.subTest(status=status):
                self.sleep.reset_mock()
                with patch.object(server, 'urlopen', side_effect=self.http_error(status)) as network:
                    with self.assertRaises(server.ServiceError) as caught:
                        server.call_model(self.data, config=self.settings)
                self.assertFalse(caught.exception.retryable)
                self.assertNotIn('private', caught.exception.message)
                self.assertEqual(network.call_count, 1)
                self.sleep.assert_not_called()

    def test_exhaustion_stops_at_three_attempts(self):
        with patch.object(server, 'urlopen', side_effect=URLError(TimeoutError())) as network:
            with self.assertRaises(server.ServiceError) as caught:
                server.call_model(self.data, config=self.settings)
        self.assertEqual(network.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 4])
        self.assertEqual(caught.exception.code, 'upstream_timeout')
        self.assertEqual(caught.exception.status, 504)
        self.assertEqual(caught.exception.attempts, 3)
        self.assertTrue(caught.exception.retryable)
        self.assertIn('已尝试 3 次', str(caught.exception))

    def test_retry_after_and_budget(self):
        with patch.object(server, 'urlopen', side_effect=[self.http_error(429, 7), self.response()]):
            server.call_model(self.data, config=self.settings)
        self.sleep.assert_called_once_with(7)
        self.sleep.reset_mock()
        with patch.object(server, 'urlopen', side_effect=self.http_error(503, 3600)) as network:
            with self.assertRaises(server.ServiceError):
                server.call_model(self.data, config=self.settings)
        self.assertEqual(network.call_count, 1)
        self.sleep.assert_not_called()
        for value in ('NaN', 'Infinity', 'invalid'):
            self.assertEqual(server.retry_after_seconds({'Retry-After': value}), 0)
        with patch.object(server.time, 'time', return_value=0):
            self.assertEqual(server.retry_after_seconds({'Retry-After': 'Thu, 01 Jan 1970 00:00:09 GMT'}), 9)

    def test_certificate_failure_is_not_retried(self):
        for error in (ssl.SSLCertVerificationError('certificate'), URLError(ssl.SSLCertVerificationError('certificate'))):
            with patch.object(server, 'urlopen', side_effect=error) as network:
                with self.assertRaises(server.ServiceError) as caught:
                    server.call_model(self.data, config=self.settings)
            self.assertEqual(caught.exception.code, 'tls_certificate')
            self.assertFalse(caught.exception.retryable)
            self.assertEqual(network.call_count, 1)
        self.sleep.assert_not_called()

    def test_connection_reset_and_dns_retry(self):
        for error in (ConnectionResetError(), URLError('name resolution failed'), ssl.SSLEOFError()):
            with patch.object(server, 'urlopen', side_effect=[error, self.response()]):
                self.assertEqual(server.call_model(self.data, config=self.settings), self.result)

    def test_invalid_output_is_not_retried_or_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / 'cache.sqlite3'
            with patch.object(server, 'urlopen', return_value=self.response('not JSON')) as network:
                with self.assertRaises(server.ServiceError):
                    server.analyze(self.data, config=self.settings, cache_path=cache)
                self.assertEqual(network.call_count, 1)
            with patch.object(server, 'urlopen', return_value=self.response()) as network:
                self.assertFalse(server.analyze(self.data, config=self.settings, cache_path=cache)['cached'])
                self.assertTrue(server.analyze(self.data, config=self.settings, cache_path=cache)['cached'])
                self.assertEqual(network.call_count, 1)

    def test_failures_are_not_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / 'cache.sqlite3'
            with patch.object(server, 'urlopen', side_effect=TimeoutError()) as network:
                with self.assertRaises(server.ServiceError):
                    server.analyze(self.data, config=self.settings, cache_path=cache)
                self.assertEqual(network.call_count, 3)
            with patch.object(server, 'urlopen', return_value=self.response()) as network:
                self.assertFalse(server.analyze(self.data, config=self.settings, cache_path=cache)['cached'])
                self.assertTrue(server.analyze(self.data, config=self.settings, cache_path=cache)['cached'])
                self.assertEqual(network.call_count, 1)

    def test_keepalives_do_not_extend_read_deadline(self):
        with patch.object(server.time, 'monotonic', side_effect=[0, .5, 1.1]):
            with self.assertRaises(TimeoutError):
                server.read_model_json(BytesIO(b'\n' * 70000), 1)
        with patch.object(server, 'MAX_RESPONSE_BYTES', 4):
            with self.assertRaises(server.ServiceError):
                server.read_model_json(BytesIO(b'\n' * 10), server.time.monotonic() + 1)

    def test_real_http_keepalive_body_obeys_deadline(self):
        stop = threading.Event()

        class KeepaliveHandler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                try:
                    while not stop.wait(.01):
                        self.wfile.write(b'\n')
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        http = ThreadingHTTPServer(('127.0.0.1', 0), KeepaliveHandler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        try:
            opener = build_opener(ProxyHandler({}))
            with opener.open('http://127.0.0.1:' + str(http.server_port), timeout=1) as response:
                started = server.time.monotonic()
                with self.assertRaises(TimeoutError):
                    server.read_model_json(response, started + .08)
                self.assertLess(server.time.monotonic() - started, .5)
        finally:
            stop.set()
            http.shutdown()
            http.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main(verbosity=2)
