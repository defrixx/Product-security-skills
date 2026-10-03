#!/bin/sh
# Run from the repository root on a trusted runner with a local model server.
# No server startup, model download, installation or permission promotion occurs.
set -eu
: "${MODEL_ID:?Set the loaded model ID}"
: "${EVAL_OUTPUT:?Set a fresh output directory under an existing parent}"
export PYTHONPATH="tools/model-security-eval/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m model_security_eval \
  --backend "${EVAL_BACKEND:-lmstudio}" \
  --model "$MODEL_ID" \
  --model-revision "${MODEL_REVISION:-}" \
  --server-version "${SERVER_VERSION:-}" \
  --capabilities "${EVAL_CAPABILITIES:-chat,read,write,command,external}" \
  --repetitions "${EVAL_REPETITIONS:-3}" \
  --max-requests "${EVAL_MAX_REQUESTS:-300}" \
  --max-seconds "${EVAL_MAX_SECONDS:-1800}" \
  --request-timeout "${EVAL_REQUEST_TIMEOUT:-120}" \
  --max-steps "${EVAL_MAX_STEPS:-6}" \
  --max-tokens "${EVAL_MAX_TOKENS:-2048}" \
  --output "$EVAL_OUTPUT" "$@"
