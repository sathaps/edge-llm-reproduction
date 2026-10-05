#!/usr/bin/env bash
# Install the latest 0.3.x Ollama release that installs, starts and runs the given models.
# usage: install_ollama_period.sh MODEL [MODEL ...]
# Writes out/env.txt (the version that worked) and out/ollama_install.log. Exits 1 if no release works.
mkdir -p out
: > out/ollama_install.log
{ echo "date_utc: $(date -u +%FT%TZ)"; echo "commit: $GITHUB_SHA"; nproc; free -g; } | tee out/env.txt
for v in 0.3.14 0.3.13 0.3.12 0.3.11 0.3.10 0.3.9; do
  echo "== trying $v" | tee -a out/ollama_install.log
  sudo systemctl stop ollama 2>/dev/null; sudo pkill -x ollama 2>/dev/null; sleep 1
  curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=$v sh >> out/ollama_install.log 2>&1 || { echo "install of $v failed" | tee -a out/ollama_install.log; continue; }
  sudo systemctl stop ollama 2>/dev/null; sleep 1
  (OLLAMA_NUM_PARALLEL=1 ollama serve > out/ollama_serve.log 2>&1 &)
  for i in $(seq 1 30); do curl -s localhost:11434/api/version | grep -q version && break; sleep 1; done
  got=$(curl -s localhost:11434/api/version)
  echo "server says: $got" | tee -a out/ollama_install.log
  ok=1
  for m in "$@"; do ollama pull "$m" >> out/ollama_install.log 2>&1 || { echo "pull of $m failed on $v" | tee -a out/ollama_install.log; ok=0; break; }; done
  if [ $ok = 1 ]; then
    case "$1" in
      *minilm*|*mxbai*) curl -sf localhost:11434/api/embed -d "{\"model\":\"$1\",\"input\":\"hello\"}" > /dev/null || ok=0 ;;
      *) curl -sf localhost:11434/api/chat -d "{\"model\":\"$1\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"options\":{\"num_predict\":1}}" > /dev/null || ok=0 ;;
    esac
  fi
  if [ $ok = 1 ]; then
    echo "ollama_version_installed: $v" | tee -a out/env.txt; echo "ollama_version_reported: $got" | tee -a out/env.txt
    ollama --version 2>&1 | tail -1 | tee -a out/env.txt
    exit 0
  fi
  echo "release $v did not work; trying the next" | tee -a out/ollama_install.log
  sudo pkill -x ollama 2>/dev/null
done
echo "no 0.3.x release worked" | tee -a out/ollama_install.log
exit 1
