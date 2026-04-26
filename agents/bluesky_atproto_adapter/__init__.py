"""Orchestrator adapter for V5 BlueskyPublisher.

Translates a ``PreprintArtifact`` arriving from
``publish_orchestrator.SURFACE_REGISTRY`` into the V5 publisher's
``PublisherPayload`` shape, calls the publisher, and maps the
``PublisherResult`` back to the orchestrator's documented result
string vocabulary (``ok | denied | auth_error | error``).

Credentials resolved from env vars set by hapax-secrets.service:

- ``HAPAX_BLUESKY_HANDLE`` (preferred) or ``HAPAX_BLUESKY_DID``
  (fallback — atproto createSession accepts either as identifier)
- ``HAPAX_BLUESKY_APP_PASSWORD`` from pass ``bluesky/operator-app-password``

Wires the surface slug ``bluesky-atproto-multi-identity`` per
``agents/publication_bus/wire_status.py``. Phase 1: single identity
(operator). Multi-identity (oudepode) is a follow-up.
"""

from __future__ import annotations

import logging
import os

from agents.publication_bus.bluesky_publisher import BlueskyPublisher
from agents.publication_bus.publisher_kit import PublisherPayload
from shared.preprint_artifact import PreprintArtifact

log = logging.getLogger(__name__)

HANDLE_ENV = "HAPAX_BLUESKY_HANDLE"
DID_ENV = "HAPAX_BLUESKY_DID"
APP_PASSWORD_ENV = "HAPAX_BLUESKY_APP_PASSWORD"


def _resolve_identifier() -> str:
    handle = os.environ.get(HANDLE_ENV, "").strip()
    if handle:
        return handle
    return os.environ.get(DID_ENV, "").strip()


def publish_artifact(artifact: PreprintArtifact) -> str:
    identifier = _resolve_identifier()
    app_password = os.environ.get(APP_PASSWORD_ENV, "").strip()

    if not identifier or not app_password:
        log.info(
            "Bluesky creds not in env (handle/DID + app-password); refusing dispatch for %s",
            artifact.slug,
        )
        return "auth_error"

    publisher = BlueskyPublisher(handle=identifier, app_password=app_password)

    payload = PublisherPayload(
        target=artifact.slug,
        text=_compose_post_text(artifact),
        metadata={"title": artifact.title},
    )

    result = publisher.publish(payload)

    if result.ok:
        return "ok"
    if result.refused:
        if "credentials" in (result.detail or "").lower():
            return "auth_error"
        return "denied"
    if result.error:
        return "error"
    log.warning("publication_bus.bluesky: result with no flag set: %r", result)
    return "error"


def _compose_post_text(artifact: PreprintArtifact) -> str:
    title = (artifact.title or "").strip()
    abstract = (artifact.abstract or "").strip()
    if title and abstract:
        candidate = f"{title}\n\n{abstract}"
    else:
        candidate = title or abstract or artifact.slug

    if len(candidate) > 280:
        candidate = candidate[:277].rstrip() + "..."
    return candidate


__all__ = ["APP_PASSWORD_ENV", "DID_ENV", "HANDLE_ENV", "publish_artifact"]
