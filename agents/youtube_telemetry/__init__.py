"""YouTube Analytics → CompositionalImpingement emitter (ytb-005).

Polls the YouTube Analytics + Reporting APIs at a 3-min cadence
(480 req/day, well under the 500-req/day soft cap). Each tick reads
realtime concurrent-viewer + engagement signals, computes a deviation
score against a 24h rolling-median baseline, and emits a
``CompositionalImpingement`` (intent_family ``youtube.telemetry``) on
the existing ``/dev/shm/hapax-dmn/impingements.jsonl`` bus.

Salience reflects deviation magnitude; the AffordancePipeline decides
whether to recruit on the impingement. No expert-system rules — this
is environmental stimulus, not a control signal.
"""
