#!/usr/bin/env bash
# usage: runner_probe.sh <model> <out-dir>
# Timings are Ollama's own response fields plus wall-clock around each call.
set -uo pipefail
MODEL="$1"; OUT="$2"; mkdir -p "$OUT"
SAFE="${MODEL//[:\/]/_}"
PROMPT="In one sentence, what does a pressure relief valve do?"

now() { date +%s.%N; }

t0=$(now)
ollama pull "$MODEL" >"$OUT/$SAFE.pull.log" 2>&1; pull_rc=$?
t1=$(now)
pull_s=$(echo "$t1 - $t0" | bc -l)

digest=$(curl -s localhost:11434/api/tags | jq -r --arg m "$MODEL" '.models[] | select(.name==$m) | .digest')
size=$(curl -s localhost:11434/api/tags | jq -r --arg m "$MODEL" '.models[] | select(.name==$m) | .size')

call() { # label
  local s e body
  s=$(now)
  body=$(curl -s --max-time 900 localhost:11434/api/generate -d "$(jq -n --arg m "$MODEL" --arg p "$PROMPT" \
    '{model:$m,prompt:$p,stream:false,options:{temperature:0,seed:42}}')")
  e=$(now)
  echo "$body" | jq --arg label "$1" --argjson wall "$(echo "$e - $s" | bc -l)" \
    '{label:$label, wall_s:$wall, response:.response, total_ns:.total_duration, load_ns:.load_duration,
      prompt_eval_count:.prompt_eval_count, prompt_eval_ns:.prompt_eval_duration,
      eval_count:.eval_count, eval_ns:.eval_duration, error:.error}'
}

cold=$(call cold)
warm=$(call warm)
ps=$(curl -s localhost:11434/api/ps | jq -c '[.models[]? | {name, size, size_vram, context_length}]')
jq -n --arg model "$MODEL" --arg digest "$digest" --argjson size "${size:-null}" \
  --argjson pull_rc "$pull_rc" --argjson pull_s "$pull_s" --arg prompt "$PROMPT" \
  --argjson cold "$cold" --argjson warm "$warm" --argjson ps "$ps" \
  '{model:$model,digest:$digest,size_bytes:$size,pull_rc:$pull_rc,pull_wall_s:$pull_s,prompt:$prompt,cold:$cold,warm:$warm,ps_after_warm:$ps}' \
  >"$OUT/$SAFE.json"
cat "$OUT/$SAFE.json"
free -m >"$OUT/$SAFE.free_after.txt"
