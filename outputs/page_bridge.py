"""Opt-in, per-user Windows URL handler for the single fixed start action."""
import os
from pathlib import Path
import subprocess
import sys

START_URL = 'chaoxingai://start'
REGISTRY_KEY = r'Software\Classes\chaoxingai'
OWNER = 'ChaoxingAI.PageLaunch.v1'


def validate_url(value):
    # Never interpret query strings, paths, file names, or commands from a website.
    if value not in (START_URL, START_URL + '/'):
        raise ValueError('页面启动链接无效。请使用学习通页面上的“启动并连接”。')
    return 'start'


def command():
    executable = Path(sys.executable).resolve()
    if getattr(sys, 'frozen', False):
        arguments = [str(executable)]
    else:
        windowed = executable.with_name('pythonw.exe')
        if not windowed.is_file():
            raise RuntimeError('未找到 pythonw.exe，请使用完整的 Windows 启动器发布包。')
        arguments = [str(windowed), str(Path(__file__).with_name('launcher.py').resolve())]
    # Windows launches the executable directly; no cmd, PowerShell, or shell=True.
    return subprocess.list2cmdline(arguments) + ' --open-url "%1"'


def _registry():
    if os.name != 'nt':
        raise RuntimeError('页面启动目前支持 Windows；其他系统请手动启动本地服务。')
    import winreg
    return winreg


def registration_matches(*, key_path=REGISTRY_KEY):
    registry = _registry()
    try:
        with registry.OpenKey(registry.HKEY_CURRENT_USER, key_path) as key:
            if registry.QueryValueEx(key, 'ChaoxingAIOwner')[0] != OWNER:
                return False
            registry.QueryValueEx(key, 'URL Protocol')
        with registry.OpenKey(registry.HKEY_CURRENT_USER, key_path + r'\shell\open\command') as key:
            return registry.QueryValueEx(key, '')[0] == command()
    except (OSError, RuntimeError):
        return False


def register(*, key_path=REGISTRY_KEY):
    registry = _registry()
    launch_command = command()
    try:
        with registry.OpenKey(registry.HKEY_CURRENT_USER, key_path) as key:
            try:
                owner = registry.QueryValueEx(key, 'ChaoxingAIOwner')[0]
            except FileNotFoundError:
                owner = None
            if owner != OWNER:
                raise RuntimeError('此页面启动名称已被其他程序使用，未覆盖原设置。')
    except FileNotFoundError:
        pass
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, key_path) as key:
        registry.SetValueEx(key, '', 0, registry.REG_SZ, 'URL:ChaoxingAI')
        registry.SetValueEx(key, 'URL Protocol', 0, registry.REG_SZ, '')
        registry.SetValueEx(key, 'ChaoxingAIOwner', 0, registry.REG_SZ, OWNER)
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, key_path + r'\shell\open\command') as key:
        registry.SetValueEx(key, '', 0, registry.REG_SZ, launch_command)


def unregister(*, key_path=REGISTRY_KEY):
    registry = _registry()
    if not registration_matches(key_path=key_path):
        raise RuntimeError('当前关联不属于这个启动器，未修改其他程序的设置。')
    for suffix in (r'\shell\open\command', r'\shell\open', r'\shell', ''):
        registry.DeleteKey(registry.HKEY_CURRENT_USER, key_path + suffix)
