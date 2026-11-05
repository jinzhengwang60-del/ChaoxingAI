"""Protocol registration uses an isolated key, never the real URL association."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path('outputs').resolve()))
import launcher
import page_bridge as bridge


class LinkTests(unittest.TestCase):
    def test_only_fixed_start_links_and_no_injected_arguments(self):
        for uri in ('chaoxingai://start', 'chaoxingai://start/'):
            self.assertEqual(launcher.parse_arguments(['--open-url', uri]).open_url, uri)
        for uri in ('https://example.com', 'chaoxingai://stop', 'chaoxingai://start?key=x',
                    'chaoxingai://start#x', 'chaoxingai://start/evil', 'chaoxingai://start%22',
                    'chaoxingai://start" --self-test-output "x', 'chaoxingai://start\n'):
            with self.assertRaises(ValueError):
                launcher.parse_arguments(['--open-url', uri])
        for extra in (['--data-dir', 'elsewhere'], ['--self-test-output', 'x']):
            with self.assertRaises(ValueError):
                launcher.parse_arguments(['--open-url', bridge.START_URL] + extra)
        for argv in (['--open-url=' + bridge.START_URL], ['--open-url'],
                     ['--open-url', bridge.START_URL, '--open-url', bridge.START_URL]):
            with self.assertRaises(ValueError):
                launcher.parse_arguments(argv)
        with self.assertRaises(SystemExit), patch('sys.stderr'):
            launcher.parse_arguments(['--open-u', bridge.START_URL])

    def test_packaged_command_quotes_executable_and_url_without_shell(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', r'C:\Program Files\中文助手\Launcher.exe'):
            command = bridge.command()
        self.assertTrue(command.startswith('"'))
        self.assertTrue(command.endswith(' --open-url "%1"'))
        self.assertNotIn('cmd.exe', command)
        self.assertNotIn('powershell', command.lower())


@unittest.skipUnless(os.name == 'nt', 'Windows per-user registration')
class RegistrationTests(unittest.TestCase):
    def setUp(self):
        import winreg
        self.registry = winreg
        self.key_path = 'Software\\ChaoxingAI\\PageLaunchTests\\' + uuid.uuid4().hex
        self.command = patch.object(bridge, 'command', return_value='"C:\\测试 路径\\Launcher.exe" --open-url "%1"')
        self.command.start()

    def tearDown(self):
        self.command.stop()
        for suffix in (r'\shell\open\command', r'\shell\open', r'\shell', ''):
            try:
                self.registry.DeleteKey(self.registry.HKEY_CURRENT_USER, self.key_path + suffix)
            except FileNotFoundError:
                pass

    def test_register_repair_and_remove_only_owned_association(self):
        self.assertFalse(bridge.registration_matches(key_path=self.key_path))
        bridge.register(key_path=self.key_path)
        self.assertTrue(bridge.registration_matches(key_path=self.key_path))
        with patch.object(bridge, 'command', return_value='"C:\\moved.exe" --open-url "%1"'):
            self.assertFalse(bridge.registration_matches(key_path=self.key_path))
            bridge.register(key_path=self.key_path)
            self.assertTrue(bridge.registration_matches(key_path=self.key_path))
            bridge.unregister(key_path=self.key_path)
        self.assertFalse(bridge.registration_matches(key_path=self.key_path))

    def test_foreign_registration_is_preserved(self):
        registry = self.registry
        with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, self.key_path) as key:
            registry.SetValueEx(key, '', 0, registry.REG_SZ, 'another application')
        with self.assertRaises(RuntimeError):
            bridge.register(key_path=self.key_path)
        with self.assertRaises(RuntimeError):
            bridge.unregister(key_path=self.key_path)
        with registry.OpenKey(registry.HKEY_CURRENT_USER, self.key_path) as key:
            self.assertEqual(registry.QueryValueEx(key, '')[0], 'another application')
