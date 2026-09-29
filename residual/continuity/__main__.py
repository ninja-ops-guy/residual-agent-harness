"""Operator surface: python -m residual.continuity --root STATION ..."""
import argparse
import json
from pathlib import Path

from ai_providers import ChatRequest, Message, Role
from residual.core import ContractError, strict_json
from residual.modular import normalize_profile, make_adapter
from residual.station.models import save_settings, credentials_for
from residual.station.store import Store
from . import Continuity

PROBE_SCHEMA = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
                'required': ['ready'], 'additionalProperties': False}


def probe_request(model):
    return ChatRequest(model, (Message(Role.USER, 'Return exactly {"ready":true}.'),),
                       max_tokens=32, response_schema=PROBE_SCHEMA)


def validate_probe(response):
    if response.finish_reason != 'stop' or response.tool_calls or strict_json(response.content) != {'ready': True}:
        raise ContractError('readiness_protocol_failure')


def configured_profiles(settings):
    return [normalize_profile(p, 'remote') for p in
            [settings['cloud']] + settings.get('cloud_fallbacks', [])]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    config = commands.add_parser('configure')
    config.add_argument('settings', type=Path)
    commands.add_parser('inspect')
    qualify = commands.add_parser('qualify')
    qualify.add_argument('--route', required=True)
    qualify.add_argument('--admission-context', type=Path, required=True)
    probe = commands.add_parser('half-open')
    probe.add_argument('--route', required=True)
    args = parser.parse_args(argv)
    store = Store(args.root)
    if args.command == 'configure':
        save_settings(store, json.loads(args.settings.read_text()))
    settings = store.settings()
    profiles = configured_profiles(settings)
    journal = Continuity(store)
    if args.command in {'qualify', 'half-open'}:
        profile = next((p for p in profiles if p['route_id'] == args.route), None)
        if profile is None:
            parser.error('Route is not configured')
        if args.command == 'qualify':
            journal.qualify(profile, json.loads(args.admission_context.read_text()),
                            make_adapter(profile, credentials_for(settings, profile['kind'],
                                         credential_ref=profile['credential_ref'])),
                            probe_request(profile['model']), validate_probe)
        else:
            journal.half_open(profile)
    print(json.dumps(journal.inspect(profiles, settings.get('fallback_mode', 'OFF')), indent=2))


if __name__ == '__main__':
    main()
