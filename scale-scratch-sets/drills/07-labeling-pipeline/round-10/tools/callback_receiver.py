"""Tiny customer webhook for trying /consensus by hand (stdlib only).

    python tools/callback_receiver.py                 # listens on :9100, secret "dev-secret"
    python tools/callback_receiver.py --fail-rate 0.3 # also answer 503 to ~30% of requests

Then, in the shell running uvicorn:

    export CALLBACK_URL=http://127.0.0.1:9100/hooks/labels
    export CALLBACK_SECRET=dev-secret

Each request is printed with whether its X-Signature verified. Bad signature -> 401.
"""

import argparse
import hashlib
import hmac
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9100)
    ap.add_argument("--secret", default="dev-secret")
    ap.add_argument("--fail-rate", type=float, default=0.0)
    args = ap.parse_args()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("content-length") or 0))
            want = "sha256=" + hmac.new(args.secret.encode(), raw, hashlib.sha256).hexdigest()
            ok_sig = hmac.compare_digest(self.headers.get("x-signature", ""), want)
            code = 401 if not ok_sig else 503 if random.random() < args.fail_rate else 200
            key = self.headers.get("idempotency-key")
            print(f"{code}  key={key}  signature={'ok' if ok_sig else 'BAD'}  body={raw.decode(errors='replace')}")
            body = json.dumps({"status": code}).encode()
            self.send_response(code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    print(f"listening on http://127.0.0.1:{args.port}/hooks/labels  (secret={args.secret!r})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
