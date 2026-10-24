"""Exercise the actual Tk callbacks with simulated AI responses and a private port."""
import os
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path('outputs').resolve()))
import desktop_core as core
import launcher
import server


@unittest.skipUnless(os.name == 'nt', 'Windows launcher')
class LauncherUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = launcher.Launcher(self.root, self.temp.name)
        self.app.service = core.ServiceController(self.temp.name, port=0)
        self.root.update()

    def tearDown(self):
        self.app.shutdown()
        self.root.destroy()
        self.temp.cleanup()

    def wait_for_worker(self):
        deadline = time.monotonic() + 5
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertFalse(self.app.busy)

    def test_first_run_input_and_advanced_settings(self):
        self.app.test_button.invoke()
        self.assertIn('粘贴', self.app.status.get())
        self.assertFalse(self.app.busy)
        self.app.toggle_advanced()
        self.assertEqual(self.app.advanced.winfo_manager(), 'grid')
        self.app.toggle_advanced()
        self.assertEqual(self.app.advanced.winfo_manager(), '')

    def test_test_save_start_stop_and_restart(self):
        self.app.key.set('test-not-a-real-key')
        with patch.object(core, 'test_connection', return_value={'recommended_options': ['A']}):
            self.app.test_button.invoke()
            self.wait_for_worker()
        self.assertTrue(self.app.service.running)
        self.assertEqual(self.app.badge.get(), '服务运行中')
        self.assertEqual(self.app.saved['DEEPSEEK_API_KEY'], 'test-not-a-real-key')
        self.app.stop_button.invoke()
        self.wait_for_worker()
        self.assertFalse(self.app.service.running)
        self.app.start_button.invoke()
        self.wait_for_worker()
        self.assertTrue(self.app.service.running)

    def test_failed_connection_does_not_save_or_start(self):
        self.app.key.set('invalid-test-key')
        with patch.object(core, 'test_connection', side_effect=server.ServiceError(502, 'API 密钥无效')):
            self.app.test_button.invoke()
            self.wait_for_worker()
        self.assertIn('密钥无效', self.app.status.get())
        self.assertIsNone(self.app.store.load())
        self.assertFalse(self.app.service.running)

    def test_saved_configuration_autostarts_without_an_api_test(self):
        self.app.shutdown()
        self.root.destroy()
        core.SettingsStore(self.temp.name).save({'DEEPSEEK_API_KEY': 'saved-test-key', 'DEEPSEEK_MODEL': core.DEFAULT_MODEL})
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = launcher.Launcher(self.root, self.temp.name)
        self.app.service = core.ServiceController(self.temp.name, port=0)
        with patch.object(core, 'test_connection') as api:
            deadline = time.monotonic() + 5
            while (not self.app.service.running or self.app.busy) and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
            self.assertTrue(self.app.service.running)
            self.assertFalse(self.app.busy)
            api.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
