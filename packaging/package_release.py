"""Build an allowlisted release archive, never copying local settings or caches."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
VERSION = '1.0.0'


def main():
    exe = DIST / 'ChaoxingAI-Launcher.exe'
    if not exe.is_file():
        raise SystemExit('Build the launcher first.')
    public_sources = ['README.md', 'LICENSE', 'NOTICE.md', '.gitignore',
        'outputs/launcher.py', 'outputs/desktop_core.py', 'outputs/server.py',
        'outputs/launcher_help.html', 'outputs/auto-ai.js', 'outputs/.env.example',
        'outputs/安装说明.md', 'source/auto.js', 'packaging/requirements-build.txt',
        'packaging/ChaoxingAI.spec', 'packaging/build_windows.ps1', 'packaging/package_release.py',
        'packaging/verify_windows.py', 'packaging/RELEASE-v1.0.0.md']
    public_sources += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'tests').glob('test_*')) if p.is_file()]
    license_files = sorted((ROOT / 'packaging' / 'licenses').glob('*.txt'))
    public_sources += [p.relative_to(ROOT).as_posix() for p in license_files]
    source_archive = DIST / 'ChaoxingAI-source-v1.0.0.zip'
    with zipfile.ZipFile(source_archive, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in public_sources:
            archive.write(ROOT / name, 'ChaoxingAI-source/' + name)
    quickstart = '''ChaoxingAI Windows 启动器 1.0.0

1. 将本压缩包完整解压到任意普通文件夹。
2. 双击 ChaoxingAI-Launcher.exe，无需安装 Python。
3. 首次使用点击“获取 API 密钥”，在 DeepSeek 官方平台创建密钥。
4. 将密钥粘贴到启动器，点击“测试并保存，启动服务”。
5. 点击“安装 / 更新浏览器脚本”，安装普通脚本，再打开学习通。

以后只要双击启动器，服务会自动启动。可以最小化，退出会停止服务。
密钥在 Windows 当前用户账号下加密保存，不随本压缩包分发。
AI API 可能收费；连接测试会发送一道示例题，可能产生少量费用。
已有 server.py 服务时，请先在原窗口按 Ctrl+C 停止，再启动本工具。
此前 .env 可以通过“导入原 .env”读取，原文件不会修改。
source-code.zip 中提供与本构建对应的完整项目源码和构建脚本。
本程序尚未进行发布者代码签名。请仅使用项目发布的文件。

项目：https://github.com/jinzhengwang60-del/ChaoxingAI
脚本：https://scriptcat.org/zh-CN/script-show-page/8102
'''
    package = DIST / ('ChaoxingAI-Windows-v' + VERSION + '.zip')
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        prefix = 'ChaoxingAI-Windows/'
        archive.write(exe, prefix + exe.name)
        archive.writestr(prefix + '快速开始.txt', quickstart.encode('utf-8-sig'))
        archive.write(ROOT / 'LICENSE', prefix + 'LICENSE.txt')
        archive.write(ROOT / 'NOTICE.md', prefix + 'NOTICE.md')
        for license_file in license_files:
            archive.write(license_file, prefix + 'third_party_licenses/' + license_file.name)
        archive.write(source_archive, prefix + 'source-code.zip')
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (DIST / 'SHA256SUMS.txt').write_text(digest + '  ' + package.name + '\n', encoding='ascii')
    print(json.dumps({'package': str(package), 'bytes': package.stat().st_size,
                      'sha256': digest, 'source_files': len(public_sources)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
