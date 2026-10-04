from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
root = Path(__file__).resolve().parents[1] / 'website'
errors = []
class Check(HTMLParser):
    def __init__(self, file):
        super().__init__()
        self.file = file
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            errors.append(f'Unexpected script: {self.file}')
        for attr in ('src', 'href'):
            value = attrs.get(attr, '')
            url = urlsplit(value)
            if value and not url.scheme and url.path:
                target = (self.file.parent / unquote(url.path)).resolve()
                if not target.exists():
                    errors.append(f'Missing {target}')
for page in root.rglob('*.html'):
    Check(page).feed(page.read_text('utf-8'))
if errors:
    raise SystemExit('\n'.join(errors))
print('PASS: all static page links/assets exist; no scripts.')
