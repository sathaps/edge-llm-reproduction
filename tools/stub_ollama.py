#!/usr/bin/env python3
"""A fake Ollama endpoint for tests. It returns hashed bag-of-words embeddings and canned chat text.

usage: stub_ollama.py [--port 11500]
Nothing it produces is a result; it only exercises the plumbing.
"""
import argparse, hashlib, json, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIMS = {"mxbai-embed-large": 1024, "all-minilm": 384}


def embed(text, dim):
    v = [0.0] * dim
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % dim] += 1.0 if (h >> 64) % 2 else -1.0
    n = sum(x * x for x in v) ** 0.5 or 1.0
    return [x / n for x in v]


class Stub(ThreadingHTTPServer):
    def __init__(self, addr, reply=None):
        super().__init__(addr, Handler)
        self.requests = []
        self.reply = reply or (lambda path, body: "stub answer")
        self.context_length = 4096
        self.loaded = "llama3:latest"
        self.prompt_tokens = 100


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            data = b""
            while True:
                size = int(self.rfile.readline().strip(), 16)
                if size == 0:
                    self.rfile.readline()
                    return data
                data += self.rfile.read(size)
                self.rfile.readline()
        return self.rfile.read(int(self.headers["Content-Length"]))

    def do_GET(self):
        if self.path == "/api/version":
            return self.send({"version": "stub"})
        if self.path == "/api/tags":
            return self.send({"models": [{"name": m, "digest": hashlib.sha256(m.encode()).hexdigest(), "size": 1}
                                         for m in list(DIMS) + ["llama3:latest", "mistral:latest", "tinyllama:latest"]]})
        if self.path == "/api/ps":
            return self.send({"models": [{"name": self.server.loaded, "context_length": self.server.context_length}]})
        self.send_error(404)

    def do_POST(self):
        body = json.loads(self.read_body())
        self.server.requests.append((self.path, body))
        if self.path == "/api/embed":
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            dim = DIMS.get(body["model"].split(":")[0], 8)
            return self.send({"model": body["model"], "embeddings": [embed(t, dim) for t in inputs]})
        if self.path == "/api/embeddings":
            dim = DIMS.get(body["model"].split(":")[0], 8)
            return self.send({"embedding": embed(body["prompt"], dim)})
        if self.path in ("/api/chat", "/api/generate"):
            self.server.loaded = body["model"]
            text = self.server.reply(self.path, body)
            out = {"model": body["model"], "created_at": "2026-01-01T00:00:00Z", "done": True, "done_reason": "stop",
                   "prompt_eval_count": self.server.prompt_tokens, "prompt_eval_duration": 1,
                   "eval_count": max(1, len(text.split())), "eval_duration": 1, "load_duration": 1, "total_duration": 3}
            if self.path == "/api/chat":
                out["message"] = {"role": "assistant", "content": text}
            else:
                out["response"] = text
            return self.send(out)
        self.send_error(404)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=11500)
    a = ap.parse_args()
    Stub(("127.0.0.1", a.port)).serve_forever()
