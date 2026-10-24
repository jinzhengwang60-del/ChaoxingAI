from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'outputs' / 'launcher.py')],
    pathex=[str(root / 'outputs')],
    binaries=[],
    datas=[(str(root / 'outputs' / 'launcher_help.html'), '.'),
           (str(root / 'LICENSE'), '.'), (str(root / 'NOTICE.md'), '.'),
           (str(root / 'packaging' / 'licenses'), 'third_party_licenses')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'pandas', 'matplotlib', 'scipy', 'IPython', 'jupyter', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='ChaoxingAI-Launcher', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False, disable_windowed_traceback=False,
          argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)
