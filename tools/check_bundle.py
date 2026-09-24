"""Check integrity and local HTML references. Uses only Python's standard library."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and key in {'href', 'src'}:
                self.links.append(value)

def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    lessons = manifest['lessons']
    assert len(lessons) == 6, 'Expected six selected lesson exports'
    assert {p.name for p in (ROOT / 'lessons').glob('*.html')} == {Path(x['path']).name for x in lessons}, 'Unexpected lesson file'
    expected = {}
    for line in (ROOT / 'CHECKSUMS.sha256').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
        expected[relative] = digest
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name != 'CHECKSUMS.sha256' and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.relative_to(ROOT).parts}
    assert actual == set(expected), 'Inventory mismatch'
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, 'Changed file: ' + relative
    for item in lessons + manifest['examples']:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], 'Selected artifact differs: ' + item['path']
    count = 0
    for page in ROOT.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text(encoding='utf-8'))
        for link in parser.links:
            target = urlsplit(link)
            if target.scheme or target.netloc or not target.path:
                continue
            destination = (page.parent / unquote(target.path)).resolve()
            assert destination.is_relative_to(ROOT), 'Link escapes package: ' + link
            assert destination.is_file(), 'Missing local target: ' + link
            count += 1
    print(json.dumps({'status': 'PASS', 'files': len(expected) + 1, 'lessons': len(lessons), 'local_html_references': count, 'scope': 'Inventory, hashes and local HTML links. Not a browser or mathematical review.'}))

if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        sys.exit(1)
