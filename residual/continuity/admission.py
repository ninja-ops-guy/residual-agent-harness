"""BL-006 Candidate B boundary; no synthetic telemetry or implicit WARN approval."""
from datetime import datetime, timezone

from residual.core import ContractError, digest, canonical
from .vendor import bl006


def consume(store, profile, context, assignment, request=None):
    """Evaluate current inputs and consume once with an unconditional manifest digest.

    Candidate B is retained byte-for-byte. This wrapper additionally rejects
    REJECT before consume and serializes its multi-statement consume transaction.
    Remote placement does not claim that this host measures upstream inference.
    """
    try:
        manifest = bl006.ManifestRow(**context['manifest'])
        telemetry = bl006.TelemetrySnapshot(**context['telemetry'])
        host = context['host_identity']
        if manifest.model_identity != profile['model'] or not host:
            raise ValueError('identity')
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(
            telemetry.collected_at.replace('Z', '+00:00'))).total_seconds()
        if not 0 <= age <= bl006.TELEMETRY_FRESHNESS_SECONDS:
            raise ValueError('freshness')
        numeric = (manifest.footprint_bytes, manifest.kv_per_token_bytes,
                   manifest.runtime_overhead_bytes, telemetry.available_ram_bytes,
                   telemetry.resident_runtime_rss_sum)
        if any(type(n) is not int or n < 0 for n in numeric):
            raise ValueError('invalid resource measurement')
        if telemetry.core_count < 1 or telemetry.load1 < 0:
            raise ValueError('invalid telemetry')
        context_tokens = context['requested_context_tokens']
        max_tokens = request.max_tokens if request else context['requested_max_tokens']
        if type(context_tokens) is not int or context_tokens < 1 or type(max_tokens) is not int or max_tokens < 1:
            raise ValueError('invalid token limit')
        if max_tokens > context['requested_max_tokens']:
            raise ValueError('output outside admission context')
        # Conservative UTF-8 bound for text-only prompts; never pretend to have
        # measured a provider tokenizer. Operators must supply sufficient context.
        if request and sum(len(m.content.encode()) for m in request.messages) + len(canonical(request.response_schema).encode()) > context_tokens:
            raise ValueError('prompt outside admission context')
        route_binding = digest({'route': profile, 'assignment': assignment})
        envelope = bl006.create_envelope(
            manifest.model_identity, manifest.quantization,
            context_tokens, max_tokens,
            host, 'bl006-candidate-b/1', assignment_binding=route_binding,
            device_class=manifest.device_class)
        verdict, reasons, _ = bl006.AdmissionEvaluator('bl006-candidate-b/1').evaluate(
            envelope, telemetry, manifest)
    except (KeyError, TypeError, ValueError):
        raise ContractError('admission_failure') from None
    evidence = bl006.EvidenceStore(str(store.root / 'provider-admission.sqlite3'))
    try:
        receipt = evidence.insert_evaluation(envelope, telemetry, manifest, verdict, reasons)
        if verdict != 'PASS':
            # WARN confirmation belongs to an explicit operator workflow, never
            # to automatic fallback. This bounded path accepts PASS only.
            raise ContractError('admission_failure')
        evidence.conn.execute('BEGIN IMMEDIATE')
        ok, consumed = evidence.consume(envelope.admission_id, host, manifest.digest())
        if not ok:
            raise ContractError('admission_failure')
        return {'admission_id': envelope.admission_id, 'receipt_digest': receipt,
                'consume_receipt_digest': consumed, 'manifest_digest': manifest.digest(),
                'expires_at': envelope.expires_at, 'verdict': verdict, 'route_binding': route_binding,
                'requested_context_tokens': context_tokens, 'requested_max_tokens': max_tokens}
    finally:
        evidence.conn.close()
