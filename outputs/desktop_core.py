"""Windows launcher storage and service lifecycle; no GUI or UI-thread work."""
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import threading
from urllib.error import URLError
from urllib.request import build_opener, ProxyHandler

import server

APP_VERSION = '1.0.1'
DEFAULT_MODEL = 'deepseek-flash'
SCRIPT_URL = 'https://scriptcat.org/zh-CN/script-show-page/8102'
KEY_URL = 'https://platform.deepseek.com/api_keys'


def default_data_dir():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ChaoxingAI'


def validate_settings(key, model):
    key, model = key.strip(), model.strip()
    if not key or key == 'your_deepseek_api_key_here':
        raise ValueError('请先粘贴你在 DeepSeek 平台创建的 API 密钥。')
    if len(key) > 512 or any(c.isspace() for c in key) or not key.isascii():
        raise ValueError('密钥中含有空格、换行或非英文字符，请重新复制。')
    if not model or len(model) > 128 or any(c.isspace() for c in model) or not model.isascii():
        raise ValueError('模型名称无效，请检查高级设置。')
    return {'DEEPSEEK_API_KEY': key, 'DEEPSEEK_MODEL': model}


class DataBlob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('本启动器的加密保存功能需要 Windows。')
    crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DataBlob), wintypes.LPCWSTR,
        ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob)]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_void_p,
        ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob)]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    incoming, outgoing = DataBlob(len(data), buffer), DataBlob()
    if decrypt:
        ok = crypt32.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing))
    else:
        ok = crypt32.CryptProtectData(ctypes.byref(incoming), 'ChaoxingAI API key', None, None, None, 1, ctypes.byref(outgoing))
    if not ok:
        raise RuntimeError('无法加密或读取密钥；请在原 Windows 账号中打开，或重新填写密钥。')
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(outgoing.pbData)


class SettingsStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'settings.json'

    def load(self):
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            if raw.get('format') != 1:
                raise ValueError()
            key = _dpapi(base64.b64decode(raw['key_protected'], validate=True), decrypt=True).decode('utf-8')
            return validate_settings(key, raw['model'])
        except (ValueError, KeyError, TypeError, UnicodeError, RuntimeError) as error:
            raise RuntimeError('已保存配置无法读取。请重新粘贴密钥并测试，不会自动使用损坏配置。') from error

    def save(self, settings):
        settings = validate_settings(settings['DEEPSEEK_API_KEY'], settings['DEEPSEEK_MODEL'])
        protected = base64.b64encode(_dpapi(settings['DEEPSEEK_API_KEY'].encode('utf-8'))).decode('ascii')
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory / 'settings.json.tmp'
        temporary.write_text(json.dumps({'format': 1, 'model': settings['DEEPSEEK_MODEL'],
            'key_protected': protected}, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)


def test_connection(settings):
    """A real, tiny analysis request, deliberately bypassing the answer cache."""
    data = {'question': '连接测试：1 + 1 等于多少？', 'type': '单选题',
            'options': [{'label': 'A', 'text': '2'}, {'label': 'B', 'text': '3'}]}
    result = server.call_model(data, config=dict(settings))
    if result['recommended_options'] != ['A']:
        raise server.ServiceError(502, '已连通，但模型没有返回有效的示例答案；请重试或更换模型。')
    return result


class ServiceController:
    def __init__(self, directory, *, port=8787):
        self.directory = Path(directory)
        self.port = port
        self.http = None
        self.thread = None

    def probe(self):
        # A local connection must never be routed through an environment proxy.
        try:
            with build_opener(ProxyHandler({})).open('http://127.0.0.1:' + str(self.port) + '/health', timeout=2) as response:
                data = json.load(response)
            if data.get('service') == server.SERVICE_ID:
                return 'ours'
            if data.get('ok') is True and 'model' in data and 'configured' in data:
                return 'legacy'
            return 'other'
        except (URLError, TimeoutError, OSError):
            return 'unavailable'
        except (ValueError, TypeError, AttributeError):
            return 'other'

    @property
    def running(self):
        return bool(self.http and self.thread and self.thread.is_alive())

    def start(self, settings):
        if self.running:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            http = server.make_http_server(settings, self.directory / 'cache.sqlite3', port=self.port)
        except OSError as error:
            state = self.probe()
            if state in ('ours', 'legacy'):
                raise RuntimeError('已有本地服务正在运行。请在原服务窗口停止它，再点击“启动服务”；不会自动结束其他进程。') from error
            raise RuntimeError('本地服务端口已被占用。请关闭占用该端口的程序后重试。') from error
        self.http = http
        self.port = http.server_port
        self.thread = threading.Thread(target=http.serve_forever, name='ChaoxingAI HTTP', daemon=True)
        self.thread.start()

    def stop(self):
        http, thread = self.http, self.thread
        if http:
            http.shutdown()
            http.server_close()
        if thread:
            thread.join(timeout=3)
        self.http = self.thread = None


class SingleInstance:
    """A per-user-data-directory Windows mutex; no stale lock files."""
    def __init__(self, directory):
        self.handle = None
        if os.name != 'nt':
            return
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        identity = hashlib.sha256(str(Path(directory).resolve()).lower().encode()).hexdigest()[:24]
        self.handle = self.kernel.CreateMutexW(None, False, 'Local\\ChaoxingAI-' + identity)
        if not self.handle:
            raise RuntimeError('无法检查启动器运行状态，请重试。')
        if ctypes.get_last_error() == 183:
            self.close()
            raise RuntimeError('ChaoxingAI 启动器已经打开，请使用已有窗口。')

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
