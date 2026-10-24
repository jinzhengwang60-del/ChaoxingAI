"""Verify the executable with Python/Conda paths removed from the child process."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent


def main():
    executable = ROOT / 'dist' / 'ChaoxingAI-Launcher.exe'
    output = ROOT / 'work' / ('bundled-check-' + uuid.uuid4().hex + '.json')
    environment = dict(os.environ)
    windows = environment.get('SystemRoot', r'C:\Windows')
    environment['PATH'] = str(Path(windows) / 'System32') + os.pathsep + windows
    for name in ['PYTHONHOME', 'PYTHONPATH', 'TCL_LIBRARY', 'TK_LIBRARY', 'CONDA_PREFIX', 'VIRTUAL_ENV']:
        environment.pop(name, None)
    result = subprocess.run([str(executable), '--self-test-output', str(output)],
                            cwd=ROOT / 'dist', env=environment, timeout=45)
    if result.returncode or not output.is_file():
        raise SystemExit('Bundled self-test did not complete successfully.')
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['ok'] and report['bundled'] and not report['api_called']
    from PyInstaller.archive.readers import CArchiveReader
    entries = CArchiveReader(str(executable)).toc
    assert not any(Path(name).name in {'.env', 'settings.json', 'cache.sqlite3'} for name in entries)
    report['no_local_secrets_packaged'] = True
    report['without_python_path'] = True
    (ROOT / 'work' / 'launcher-bundled-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
