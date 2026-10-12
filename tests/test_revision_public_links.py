"""Resolve the real copied guide links in their public-site context."""
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit, unquote
import pytest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('session-revision-plan.md', 'session-revisions.md', 'session-revision-result.md')


def destination(href, name):
    url = urlsplit(urljoin('https://aitrustid.com/reference/' + name, href))
    if url.scheme == 'https' and url.netloc == 'github.com':
        prefix = '/knwvmbrr/aitrust-id/blob/main/'
        assert url.path.startswith(prefix), 'Unexpected repository destination'
        target = ROOT / unquote(url.path[len(prefix):])
    else:
        assert url.scheme == 'https' and url.netloc == 'aitrustid.com'
        target = ROOT / 'site/public' / unquote(url.path).lstrip('/')
    assert target.resolve().is_relative_to(ROOT) and target.is_file() and not target.is_symlink(), \
        'Published Markdown link destination missing'
    return target


@pytest.mark.parametrize('name', NAMES)
def test_real_copied_guide_links_resolve_to_published_or_repository_files(name):
    text = (ROOT / 'site/public/reference' / name).read_text()
    for href in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
        destination(href, name)


def test_original_relative_receipt_link_is_refused_in_public_context():
    with pytest.raises(AssertionError, match='destination missing'):
        destination('../runs/2026-10-12-session-revision-local.json', 'session-revision-result.md')
