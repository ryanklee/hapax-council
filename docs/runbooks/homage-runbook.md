# HOMAGE runbook

Operational notes for the HOMAGE framework (spec
`docs/superpowers/specs/2026-04-18-homage-framework-design.md`).

## Changelog

- **2026-04-18 — Phase 12 (task #120) — go-live.**
  - `HAPAX_HOMAGE_ACTIVE` default flipped from OFF to ON. Unset env
    resolves to active. Rollback requires an explicit falsy value.
  - Consent-safe variant registered: `bitchx_consent_safe`. Engaged by
    the choreographer when `/dev/shm/hapax-compositor/consent-safe-active.json`
    is present. Palette collapses to pure grey; signature artefact
    corpus stripped.
  - Signature artefact emission wired through the choreographer: one
    random artefact from the package corpus per rotation cycle, weighted
    by `SignatureArtefact.weight`. Published to
    `/dev/shm/hapax-compositor/homage-active-artefact.json`; counter
    `hapax_homage_signature_artefact_emitted_total` incremented.

## Rollback

Emergency: flip the flag back to off and restart the compositor.

```fish
export HAPAX_HOMAGE_ACTIVE=0
systemctl --user restart studio-compositor.service
```

Verify: no homage coupling payload should appear in
`/dev/shm/hapax-imagination/uniforms.json` under the
`signal.homage_custom_*` keys, and
`hapax_homage_package_active{package="bitchx"}` should read 0 on
Prometheus.

## Consent-safe engagement

The consent-live-egress guard writes the flag file when a non-operator
face is detected with no active consent contract. The choreographer
reads the file every reconcile tick; flipping happens within one tick
(~100 ms at the default cadence).

Manual engage (testing only):

```fish
mkdir -p /dev/shm/hapax-compositor
echo '{"consent_safe": true}' > /dev/shm/hapax-compositor/consent-safe-active.json
```

Manual disengage:

```fish
rm -f /dev/shm/hapax-compositor/consent-safe-active.json
```

## Observability

- Prometheus:
  - `hapax_homage_package_active{package}` — 1 when the named package
    is the one reconciled this tick.
  - `hapax_homage_transition_total{package,transition_name}` — transitions
    applied.
  - `hapax_homage_choreographer_rejection_total{reason}` — pending
    transitions the choreographer declined.
  - `hapax_homage_signature_artefact_emitted_total{package,form}` —
    signature artefacts rotated.
  - `hapax_homage_violation_total{package,kind}` — render-time paste /
    anti-pattern violations.
- Grafana panel: `Homage — Transitions & Violations` under the
  existing director dashboard.
