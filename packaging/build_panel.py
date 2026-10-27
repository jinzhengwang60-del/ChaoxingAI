"""Bundle first-party panel assets into the standalone browser userscript."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN = '    // BEGIN BUNDLED CHAPTER PANEL\n'
END = '    // END BUNDLED CHAPTER PANEL\n'


def bundle():
    css = (ROOT / 'ui/chapter-panel.css').read_text(encoding='utf-8')
    js = (ROOT / 'ui/chapter-panel.js').read_text(encoding='utf-8')
    return BEGIN + '    const CHAPTER_PANEL_CSS = ' + json.dumps(css, ensure_ascii=False) + ';\n' + js + END


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, help='Also write a standalone .user.js install file.')
    args = parser.parse_args()
    target = ROOT / 'outputs/auto-ai.js'
    source = target.read_text(encoding='utf-8')
    if BEGIN not in source or END not in source:
        raise SystemExit('Panel bundle markers are missing.')
    start, end = source.index(BEGIN), source.index(END) + len(END)
    updated = source[:start] + bundle() + source[end:]
    if args.check:
        if source != updated:
            raise SystemExit('Panel assets differ from userscript; run packaging/build_panel.py.')
        print('PASS: embedded panel assets match the first-party UI sources.')
    else:
        target.write_text(updated, encoding='utf-8', newline='\n')
        print('Panel assets bundled into outputs/auto-ai.js.')
    if args.output:
        output = args.output.resolve()
        if output.suffixes[-2:] != ['.user', '.js']:
            raise SystemExit('The install file must end with .user.js.')
        if output == target.resolve() or ROOT / 'source' in output.parents:
            raise SystemExit('Choose an install artifact path outside the source files.')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(updated, encoding='utf-8', newline='\n')
        print(json.dumps({'userscript': str(output), 'bytes': output.stat().st_size,
                          'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
