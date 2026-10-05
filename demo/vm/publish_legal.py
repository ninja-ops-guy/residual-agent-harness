#!/usr/bin/env python3
"""Publish reviewed legal pages before Pages identity is recorded; fail closed.

This is a bounded publication check, NOT a legal-compliance certification.
Do not copy site/legal templates directly into an unreviewed public artifact.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ('privacy.html', 'terms.html', 'cookies.html', 'accessibility.html')
ASSETS = ('legal.css', 'choices.js', 'site-links.js')
ROUTES = {'index.html': './legal/', 'walkthrough/index.html': '../legal/',
          'demo/index.html': '../legal/', 'provider/index.html': '../legal/'}
BEGIN = '<!-- RESIDUAL_LEGAL_V1 -->'
END = '<!-- /RESIDUAL_LEGAL_V1 -->'


def validate_config(config: dict) -> None:
    if config.get('schema_version') != 1 or config.get('owner_review_complete') is not True:
        raise ValueError('LEGAL_PUBLICATION_HOLD: owner review is incomplete; see docs/WEBSITE_COMPLIANCE_REVIEW.md')
    for field in ('operator_name', 'privacy_email', 'effective_date', 'runtime_disclosure', 'international_processing'):
        value = config.get(field)
        if not isinstance(value, str) or not value.strip() or any(x in value.lower() for x in ('{{', 'todo', 'tbd', 'replace me')):
            raise ValueError(f'LEGAL_PUBLICATION_HOLD: missing or unfinished {field}')
    email = config['privacy_email']
    if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}', email):
        raise ValueError('LEGAL_PUBLICATION_HOLD: a valid private contact email is required')
    domain = email.rsplit('@', 1)[-1].lower()
    if domain in ('example.com', 'example.org', 'example.net') or domain.endswith(('.invalid', '.test', '.example', '.localhost')):
        raise ValueError('LEGAL_PUBLICATION_HOLD: placeholder contact address')
    date.fromisoformat(config['effective_date'])


def replace_once(text: str, anchor: str, replacement: str) -> str:
    if text.count(anchor) != 1:
        raise ValueError(f'LEGAL_PUBLICATION_HOLD: expected one anchor: {anchor[:70]}')
    return text.replace(anchor, replacement, 1)


def guard_provider(source: str) -> str:
    if '// RESIDUAL_PROVIDER_PRIVACY_V1' in source:
        if any(source.count(marker) != 1 for marker in (
                "import {installProviderPrivacy} from './provider-privacy.js';",
                'const providerPrivacy = installProviderPrivacy(',
                'if (!providerPrivacy.allowLoad())')):
            raise ValueError('LEGAL_PUBLICATION_HOLD: provider privacy guard drift')
        return source
    source = "// RESIDUAL_PROVIDER_PRIVACY_V1\nimport {installProviderPrivacy} from './provider-privacy.js';\n" + source
    anchor = 'let channel, sdk, grant = null, busy = false, modelCatalog = null, sdkLoadPromise = null, loadGeneration = 0;'
    source = replace_once(source, anchor, anchor + "\nconst providerPrivacy = installProviderPrivacy({onWithdraw: () => { grant = null; sdk = null; send({kind: 'state', connected: false}); }});")
    anchor = 'function loadSdk(restoring = false) {'
    return replace_once(source, anchor, anchor + "\n  if (!providerPrivacy.allowLoad()) return Promise.reject(new Error('provider_consent_required'));")


def add_footer(text: str, prefix: str, demo: bool = False) -> str:
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise ValueError('LEGAL_PUBLICATION_HOLD: duplicate legal footer')
        start, stop = text.index(BEGIN), text.index(END) + len(END)
        text = text[:start] + text[stop:]
    attrs = ' target="_blank" rel="noopener noreferrer"' if demo else ''
    suffix = ' (new tab)' if demo else ''
    links = [('privacy.html', 'Privacy policy'), ('cookies.html', 'Storage choices'),
             ('terms.html', 'Terms &amp; licenses'), ('accessibility.html', 'Accessibility &amp; contact')]
    footer = BEGIN + '<footer class="residual-legal-footer" data-residual-legal aria-label="Legal and privacy">' + ''.join(
        f'<a href="{prefix}{path}"{attrs}>{label}{suffix}</a>' for path, label in links) + '</footer>'
    footer += f'<link rel="stylesheet" href="{prefix}legal.css"><script src="{prefix}site-links.js" defer></script>' + END
    return replace_once(text, '</body>', footer + '</body>')


def publish_legal(site: Path, *, commit: str, templates: Path | None = None,
                  config: dict | None = None) -> dict:
    """Validate all inputs before writing. Tests use isolated temporary artifacts."""
    site = Path(site)
    templates = templates or ROOT / 'site' / 'legal'
    config = config if config is not None else json.loads((templates / 'publication.json').read_text(encoding='utf-8'))
    validate_config(config)
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('LEGAL_PUBLICATION_HOLD: exact source commit required')
    output: dict[str, str] = {}
    for name in PAGES:
        content = (templates / name).read_text(encoding='utf-8')
        for key, value in config.items():
            if isinstance(value, str):
                content = content.replace('{{' + key + '}}', html.escape(value, quote=True))
        if '{{' in content or '}}' in content:
            raise ValueError(f'LEGAL_PUBLICATION_HOLD: unresolved template in {name}')
        output['legal/' + name] = content
    for name in ASSETS:
        output['legal/' + name] = (templates / name).read_text(encoding='utf-8')
    for route, prefix in ROUTES.items():
        output[route] = add_footer((site / route).read_text(encoding='utf-8'), prefix, route == 'demo/index.html')
    provider = output['provider/index.html']
    for marker in ('id="provider-privacy-choice"', 'id="provider-privacy-withdraw"', 'name="referrer" content="origin"'):
        if marker not in provider:
            raise ValueError(f'LEGAL_PUBLICATION_HOLD: provider notice missing {marker}')
    output['provider/provider.js'] = guard_provider((site / 'provider/provider.js').read_text(encoding='utf-8'))
    output['provider/provider-privacy.js'] = (templates / 'provider-privacy.js').read_text(encoding='utf-8')
    persistence = (site / 'walkthrough/persist.js').read_text(encoding='utf-8')
    if 'residual.walkthrough.consent.v1' not in persistence:
        raise ValueError('LEGAL_PUBLICATION_HOLD: walkthrough privacy control missing')
    output['walkthrough/persist.js'] = persistence
    # No file is touched before source/config/patch anchors have been validated.
    for relative, content in output.items():
        destination = site / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding='utf-8')
    manifest = {'schema': 'residual.website-legal.v1', 'source_commit': commit,
                'effective_date': config['effective_date'],
                'configuration_sha256': hashlib.sha256(json.dumps(config, sort_keys=True).encode('utf-8')).hexdigest(),
                'claim': 'reviewed notices published; not legal or runtime certification',
                'sha256': {path: hashlib.sha256(content.encode('utf-8')).hexdigest()
                           for path, content in sorted(output.items())}}
    (site / 'legal/build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest
