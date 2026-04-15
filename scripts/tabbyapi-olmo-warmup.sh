#!/usr/bin/env bash
# tabbyapi-olmo-warmup.sh — Pre-trigger OLMo 3-7B TabbyAPI JIT compile on
# service start so the first real research-tier call does not pay the
# cold-start penalty. Called from tabbyapi-olmo.service ExecStartPost.
#
# Parallel twin of tabbyapi-warmup.sh (which targets the primary :5000
# Qwen3.5-9B instance). This script targets :5001 + OLMo-2-1124-7B.
#
# Queue #211 / drop #62 §17 Option C parallel backend deploy:
# primary TabbyAPI on :5000 serves Qwen3.5-9B for production traffic;
# this parallel instance on :5001 serves OLMo 3-7B for the claim-shaikh
# research arm + grounding-capable substrate coverage (see queue #210
# RIFTS baseline finding that Qwen never asks clarifying questions).
#
# Flow mirrors the primary warmup:
#   1. ExecStart boots python3 main.py; model load happens async
#      (~30-40 s for OLMo 3-7B at 5.0bpw).
#   2. Curl a no-op completion with --retry-connrefused so curl waits
#      for the HTTP listener to bind.
#   3. Exit 0 unconditionally — best-effort warmup.

set -o pipefail

curl -s \
    --max-time 180 \
    --retry 60 \
    --retry-delay 3 \
    --retry-connrefused \
    -X POST http://localhost:5001/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
          "model": "OLMo-2-1124-7B-Instruct-exl3-5.00bpw",
          "messages": [{"role": "user", "content": "hi"}],
          "max_tokens": 1,
          "stream": false
        }' \
    > /dev/null 2>&1

exit 0
