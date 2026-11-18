#!/usr/bin/env python3
"""Prepare reviewable AI Trust ID social posts from checked public pages."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess


ORIGIN = 'https://aitrustid.com'
POSTS = (
    (
        'Check before you run a command',
        '/tags/ps/',
        ('On-device preview', 'No account or install needed', 'Independent release validation: pending'),
        'Before you run a command from an AI answer, see what it does. The free AI Trust ID PS preview spots supported patterns that run downloaded or encoded code. Check the explanation on your device.',
    ),
    (
        'Try the preview from your phone',
        '/reference/operate/',
        ('The check runs on your device', 'No account, subscription or answer upload is needed'),
        'Copy an AI answer on your phone and try the free PS preview in your browser. Your answer stays on your device. Start with two practice examples and see what a result means.',
    ),
    (
        'Read the validation rules',
        '/policies/validation/',
        ('Independent accuracy assessment uses a frozen corpus', 'development preview while validation is in progress'),
        'How do we decide when a tag can ship? AI Trust ID publishes what each tag checks, what it misses, and the evidence we need before release. Read the validation policy.',
    ),
)


class PublicPage(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonicals = []
        self.social_urls = []
        self.excluded = False
        self.body = False
        self.hidden = None
        self.text = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'link' and 'canonical' in attributes.get('rel', '').split():
            self.canonicals.append(attributes.get('href'))
        if tag == 'meta':
            if attributes.get('property') == 'og:url':
                self.social_urls.append(attributes.get('content'))
            if attributes.get('name', '').lower() in ('robots', 'googlebot'):
                excluded = 'noindex' in attributes.get('content', '').lower()
                self.excluded = self.excluded or excluded
        if tag == 'body':
            self.body = True
        if tag in ('script', 'style', 'template') and self.hidden is None:
            self.hidden = tag

    def handle_endtag(self, tag):
        if tag == self.hidden:
            self.hidden = None
        if tag == 'body':
            self.body = False

    def handle_data(self, data):
        if self.body and self.hidden is None:
            self.text.append(data)


def read_page(route, site_dir):
    if site_dir:
        return (site_dir / route.strip('/') / 'index.html').read_text(encoding='utf-8')
    result = subprocess.run(
        ['curl', '--fail', '--silent', '--show-error', '--proto', '=https',
         '--max-time', '15', '--max-filesize', '1000000', ORIGIN + route],
        check=True, capture_output=True, encoding='utf-8', timeout=20,
    )
    return result.stdout


def generate(site_dir=None):
    drafts = []
    for title, route, claims, copy in POSTS:
        url = ORIGIN + route
        page = PublicPage(read_page(route, site_dir))
        text = ' '.join(' '.join(page.text).split()).casefold()
        if page.canonicals != [url] or page.social_urls != [url] or page.excluded:
            raise ValueError(f'Public page is missing its expected canonical metadata: {route}')
        if not all(claim.casefold() in text for claim in claims):
            raise ValueError(f'Public claim needs review: {route}')
        message = f'{copy}\n\n{url}'
        if len(message) > 280:
            raise ValueError(f'Short draft exceeds its editorial limit: {route}')
        drafts.append({
            'id': hashlib.sha256(message.encode()).hexdigest()[:16],
            'title': title,
            'text': message,
            'canonical_url': url,
            'checked_public_copy': claims,
        })
    return {
        'schema_version': 1,
        'brand': 'AI Trust ID',
        'status': 'ready_for_review',
        'source': 'local_site_build' if site_dir else 'live_website',
        'drafts': drafts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, help='Verify against a local site build')
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.site_dir), indent=2, ensure_ascii=False))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Social drafts unavailable. {error}\n')


if __name__ == '__main__':
    main()
