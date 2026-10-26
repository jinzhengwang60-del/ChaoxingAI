"""ChaoxingAI Windows setup wizard. No Python installation needed in the bundle."""
import argparse
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

import desktop_core as core
import server

TITLE = 'ChaoxingAI 启动器'


class Launcher:
    def __init__(self, root, data_dir):
        self.root = root
        self.store = core.SettingsStore(data_dir)
        self.service = core.ServiceController(data_dir)
        self.events = queue.Queue()
        self.closed = False
        self.busy = False
        self.saved = None
        self.poll_job = None
        self.autostart_job = None
        self.key = tk.StringVar()
        self.model = tk.StringVar(value=core.DEFAULT_MODEL)
        self.reveal = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='首次使用：获取密钥，粘贴后点击“测试并保存”。')
        self.badge = tk.StringVar(value='等待配置')
        self._build()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.report_callback_exception = self._callback_error
        try:
            self.saved = self.store.load()
        except (OSError, RuntimeError) as error:
            self._status(str(error), 'error')
        if self.saved:
            self.key.set(self.saved['DEEPSEEK_API_KEY'])
            self.model.set(self.saved['DEEPSEEK_MODEL'])
            self._status('已读取本机加密配置，正在启动服务……')
            self.autostart_job = self.root.after(120, self.start_saved)
        self.key.trace_add('write', self._edited)
        self.model.trace_add('write', self._edited)
        self.poll_job = self.root.after(100, self._drain)

    def _build(self):
        self.root.title(TITLE)
        height = min(880, max(620, self.root.winfo_screenheight() - 120))
        self.root.geometry('880x' + str(height))
        self.root.minsize(800, 600)
        self.root.configure(bg='#f3f6fb')
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        style.configure('TFrame', background='#f3f6fb')
        style.configure('Card.TFrame', background='white')
        style.configure('TLabel', background='#f3f6fb', foreground='#23344d')
        style.configure('Card.TLabel', background='white', foreground='#23344d')
        style.configure('Muted.TLabel', background='#f3f6fb', foreground='#62718a')
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 23, 'bold'), foreground='#122a4a')
        style.configure('Step.TLabel', font=('Microsoft YaHei UI', 13, 'bold'), background='white')
        style.configure('TButton', padding=(12, 8))
        style.configure('Primary.TButton', background='#2563eb', foreground='white', borderwidth=0)
        style.map('Primary.TButton', background=[('disabled', '#a9bce8'), ('active', '#1d4ed8')], foreground=[('disabled', 'white')])
        style.configure('TEntry', padding=9, fieldbackground='white')
        style.configure('Card.TCheckbutton', background='white')
        style.configure('Badge.TLabel', background='#e8efff', foreground='#2455a5', padding=(12, 6))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        canvas = tk.Canvas(self.root, background='#f3f6fb', highlightthickness=0)
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(self.root, orient='vertical', command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scrollbar.set)
        body = ttk.Frame(canvas, padding=(28, 24))
        window = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        def resize(event):
            canvas.itemconfigure(window, width=event.width)
            self.status_label.configure(wraplength=max(550, event.width - 60))
        canvas.bind('<Configure>', resize)
        self.root.bind('<MouseWheel>', lambda event: canvas.yview_scroll(int(-event.delta / 120), 'units'))
        body.columnconfigure(0, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='ChaoxingAI', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(header, textvariable=self.badge, style='Badge.TLabel').grid(row=0, column=1, sticky='e')
        ttk.Label(body, text='本地连接助手  /  配置一次，以后双击启动', style='Muted.TLabel').grid(row=1, column=0, sticky='w', pady=(4, 18))

        card = ttk.Frame(body, style='Card.TFrame', padding=22)
        card.grid(row=2, column=0, sticky='ew')
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text='01  连接你的 DeepSeek', style='Step.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(card, text='还没有密钥？在官方平台创建 API 密钥后，复制到这里。', style='Card.TLabel').grid(row=1, column=0, sticky='w', pady=(8, 12))
        actions = ttk.Frame(card, style='Card.TFrame')
        actions.grid(row=2, column=0, sticky='w', pady=(0, 14))
        ttk.Button(actions, text='获取 API 密钥', command=lambda: webbrowser.open(core.KEY_URL)).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text='查看配置教程', command=self.open_help).pack(side='left', padx=(0, 8))
        self.import_button = ttk.Button(actions, text='导入原 .env', command=self.import_env)
        self.import_button.pack(side='left')
        ttk.Label(card, text='API 密钥', style='Card.TLabel').grid(row=3, column=0, sticky='w')
        field = ttk.Frame(card, style='Card.TFrame')
        field.grid(row=4, column=0, sticky='ew', pady=(6, 6))
        field.columnconfigure(0, weight=1)
        self.key_entry = ttk.Entry(field, textvariable=self.key, show='•')
        self.key_entry.grid(row=0, column=0, sticky='ew')
        ttk.Checkbutton(field, text='显示', variable=self.reveal, style='Card.TCheckbutton',
                        command=lambda: self.key_entry.configure(show='' if self.reveal.get() else '•')).grid(row=0, column=1, padx=(12, 0))
        ttk.Label(card, text='密钥使用 Windows 当前账号加密保存；不会写入浏览器脚本。', style='Card.TLabel').grid(row=5, column=0, sticky='w')
        self.advanced = ttk.Frame(card, style='Card.TFrame')
        self.advanced.columnconfigure(1, weight=1)
        self.model_entry = ttk.Entry(self.advanced, textvariable=self.model)
        ttk.Label(self.advanced, text='模型名称', style='Card.TLabel').grid(row=0, column=0, padx=(0, 12))
        self.model_entry.grid(row=0, column=1, sticky='ew')
        self.advanced_button = ttk.Button(card, text='高级设置 ▸', command=self.toggle_advanced)
        self.advanced_button.grid(row=6, column=0, sticky='w', pady=(10, 0))
        self.test_button = ttk.Button(card, text='测试并保存，启动服务', style='Primary.TButton', command=self.test_and_save)
        self.test_button.grid(row=8, column=0, sticky='ew', pady=(14, 6))
        ttk.Label(card, text='连接测试会向 DeepSeek 发送一道示例题，可能产生少量 API 费用。', style='Card.TLabel').grid(row=9, column=0, sticky='w')

        service_card = ttk.Frame(body, style='Card.TFrame', padding=22)
        service_card.grid(row=3, column=0, sticky='ew', pady=(16, 0))
        service_card.columnconfigure(0, weight=1)
        ttk.Label(service_card, text='02  安装脚本，打开课程', style='Step.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(service_card, text='从脚本猫安装普通脚本，或更新已有脚本，再刷新学习通页面。', style='Card.TLabel').grid(row=1, column=0, sticky='w', pady=(8, 12))
        links = ttk.Frame(service_card, style='Card.TFrame')
        links.grid(row=2, column=0, sticky='w')
        ttk.Button(links, text='安装 / 更新浏览器脚本', command=lambda: webbrowser.open(core.SCRIPT_URL)).pack(side='left', padx=(0, 8))
        ttk.Button(links, text='打开学习通', command=lambda: webbrowser.open('https://i.chaoxing.com/')).pack(side='left')

        footer = ttk.Frame(self.root, padding=(28, 12, 28, 20))
        footer.grid(row=1, column=0, columnspan=2, sticky='ew')
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, textvariable=self.status, wraplength=785, justify='left')
        self.status_label.grid(row=0, column=0, sticky='w')
        self.progress = ttk.Progressbar(footer, mode='indeterminate')
        self.progress.grid(row=1, column=0, sticky='ew', pady=(10, 8))
        controls = ttk.Frame(footer)
        controls.grid(row=2, column=0, sticky='ew')
        self.start_button = ttk.Button(controls, text='启动服务', command=self.start_saved)
        self.start_button.pack(side='left', padx=(0, 8))
        self.stop_button = ttk.Button(controls, text='停止服务', command=self.stop_service, state='disabled')
        self.stop_button.pack(side='left')
        ttk.Label(controls, text='最小化可继续运行 · 退出会停止服务', style='Muted.TLabel').pack(side='right')

    def _status(self, text, tone='normal'):
        self.status.set(text)
        self.status_label.configure(foreground={'error': '#b42336', 'success': '#167149'}.get(tone, '#344b68'))

    def _callback_error(self, *_):
        self._status('操作未完成。请重试；如果仍失败，请关闭启动器后重新打开。', 'error')

    def _edited(self, *_):
        if not self.busy:
            self._status('配置已修改，请点击“测试并保存”后生效。' + ('当前服务继续使用已保存配置。' if self.service.running else ''))

    def toggle_advanced(self):
        if self.advanced.winfo_manager():
            self.advanced.grid_remove()
            self.advanced_button.configure(text='高级设置 ▸')
        else:
            self.advanced.grid(row=7, column=0, sticky='ew', pady=(10, 0))
            self.advanced_button.configure(text='高级设置 ▾')

    def import_env(self):
        filename = filedialog.askopenfilename(title='选择原来的 .env 配置文件', filetypes=[('环境配置', '*.env .env'), ('所有文件', '*.*')])
        if not filename:
            return
        try:
            settings = server.load_env(Path(filename))
            settings = core.validate_settings(settings.get('DEEPSEEK_API_KEY', ''), settings.get('DEEPSEEK_MODEL', core.DEFAULT_MODEL))
            self.key.set(settings['DEEPSEEK_API_KEY'])
            self.model.set(settings['DEEPSEEK_MODEL'])
            self._status('配置已导入到输入框，测试成功后才会加密保存。')
        except (OSError, UnicodeError, ValueError):
            self._status('无法读取有效配置，请检查文件，或直接粘贴 API 密钥。', 'error')

    def open_help(self):
        filename = Path(__file__).resolve().parent / 'launcher_help.html'
        if filename.exists():
            webbrowser.open(filename.as_uri())
        else:
            webbrowser.open('https://github.com/jinzhengwang60-del/ChaoxingAI#快速开始')

    def _work(self, action, operation):
        if self.busy or self.closed:
            return
        self.busy = True
        self.progress.start(12)
        for widget in (self.test_button, self.start_button, self.stop_button, self.key_entry, self.model_entry, self.import_button):
            widget.configure(state='disabled')
        def task():
            try:
                result = operation()
                self.events.put((action, result, None))
            except (server.ServiceError, ValueError, RuntimeError, OSError) as error:
                text = error.message if isinstance(error, server.ServiceError) else str(error)
                self.events.put((action, None, text))
            except Exception:
                self.events.put((action, None, '操作失败，请检查网络和本机配置目录后重试。'))
        threading.Thread(target=task, name='ChaoxingAI setup', daemon=True).start()

    def test_and_save(self):
        try:
            settings = core.validate_settings(self.key.get(), self.model.get())
        except ValueError as error:
            self._status(str(error), 'error')
            return
        self._status('正在真实测试 API 连接；网络波动时会自动重试，最多尝试 3 次，请稍候……')
        self.badge.set('连接测试中')
        def operation():
            core.test_connection(settings)
            if self.closed:
                return None
            self.store.save(settings)
            self.service.stop()
            if not self.closed:
                self.service.start(settings)
            return settings
        self._work('configured', operation)

    def start_saved(self):
        self.autostart_job = None
        if not self.saved:
            self._status('请先填写 API 密钥，点击“测试并保存”。')
            return
        settings = dict(self.saved)
        self._status('正在启动本地服务……')
        def operation():
            if not self.closed:
                self.service.start(settings)
            return settings
        self._work('started', operation)

    def stop_service(self):
        self._status('正在停止本地服务……')
        self._work('stopped', self.service.stop)

    def _drain(self):
        if self.closed:
            return
        try:
            while True:
                action, settings, error = self.events.get_nowait()
                self.busy = False
                self.progress.stop()
                for widget in (self.test_button, self.key_entry, self.model_entry, self.import_button):
                    widget.configure(state='normal')
                # A saved, tested key remains available even when an old service holds the port.
                try:
                    self.saved = self.store.load()
                except (OSError, RuntimeError):
                    pass
                self.start_button.configure(state='normal' if self.saved and not self.service.running else 'disabled')
                self.stop_button.configure(state='normal' if self.service.running else 'disabled')
                if error:
                    self.badge.set('需要处理' if not self.service.running else '服务运行中')
                    self._status(error, 'error')
                elif action == 'stopped':
                    self.badge.set('服务已停止')
                    self._status('服务已停止。配置已保留，下次可直接启动。')
                else:
                    self.badge.set('服务运行中')
                    self._status('已就绪：可以打开学习通。保持启动器运行，最小化即可。', 'success')
        except queue.Empty:
            pass
        self.poll_job = self.root.after(100, self._drain)

    def shutdown(self):
        self.closed = True
        for job in (self.poll_job, self.autostart_job):
            if job:
                self.root.after_cancel(job)
        self.poll_job = self.autostart_job = None
        self.service.stop()

    def close(self):
        if self.closed:
            return
        if (self.service.running or self.busy) and not messagebox.askyesno('退出启动器', '退出会停止本地 AI 服务，未完成的分析可能中断。\n继续运行可将窗口最小化。\n\n确定退出吗？', parent=self.root):
            return
        self.shutdown()
        self.root.destroy()


def self_test(output):
    """Offline packaged-runtime check; never uses a real key or the live 8787 port."""
    from urllib.request import build_opener, ProxyHandler
    with tempfile.TemporaryDirectory(prefix='chaoxingai-check-') as directory:
        store = core.SettingsStore(directory)
        settings = core.validate_settings('self-test-key-not-a-real-credential', core.DEFAULT_MODEL)
        store.save(settings)
        assert store.load() == settings
        assert settings['DEEPSEEK_API_KEY'] not in store.path.read_text(encoding='utf-8')
        service = core.ServiceController(directory, port=0)
        try:
            service.start(settings)
            with build_opener(ProxyHandler({})).open('http://127.0.0.1:' + str(service.port) + '/health', timeout=3) as response:
                health = json.load(response)
            assert health['ok'] and health['service'] == server.SERVICE_ID
        finally:
            service.stop()
        root = tk.Tk()
        root.withdraw()
        root.update()
        tk_version = root.tk.call('info', 'patchlevel')
        root.destroy()
    report = {'ok': True, 'launcher_version': core.APP_VERSION, 'tk_version': tk_version,
              'encrypted_storage': True, 'loopback_service': True, 'api_called': False,
              'bundled': bool(getattr(sys, 'frozen', False))}
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--self-test-output', type=Path)
    args = parser.parse_args()
    if args.self_test_output:
        self_test(args.self_test_output)
        return
    directory = args.data_dir or core.default_data_dir()
    root = tk.Tk()
    root.withdraw()
    try:
        instance = core.SingleInstance(directory)
    except RuntimeError as error:
        messagebox.showinfo(TITLE, str(error), parent=root)
        root.destroy()
        return
    try:
        Launcher(root, directory)
        root.deiconify()
        root.mainloop()
    finally:
        instance.close()


if __name__ == '__main__':
    main()
