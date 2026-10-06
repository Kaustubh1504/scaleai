"""The mock webhook receiver your dispatcher talks to in tests.

    from mock_services.webhooks import WebhookReceiver
    receiver = WebhookReceiver(secret="whsec_tasks", clock=clock)
    receiver.script_event("evt_1", [500, "429:30", 200])   # per-event responses, in order
    receiver.script([503, "drop"])                         # the next requests, whatever the event
    http = httpx.Client(transport=receiver.transport())    # no network involved
    ...
    receiver.accepted_event_ids()          # ids of 2xx-answered requests, in order
    receiver.attempts_for("evt_1")         # every request for that event (Delivery objects)
    receiver.deliveries[-1].signature_valid / .headers / .json

Scripted responses: an int status; "429:<seconds>" (429 with Retry-After);
"drop" (the client sees httpx.ConnectError); "timeout" (the client sees
httpx.ReadTimeout, but the receiver did get the request). When the scripts run
out it answers ``default_status`` (200). The receiver reads the event id from
the X-Event-Id header (or the body's "id"). See ../../shared/README.md.

Run it as a real HTTP server instead (optional):
    python -m mock_services.webhook_server --port 9100 --secret whsec_tasks --fail-first 2
"""

import mock_services  # noqa: F401  (puts shared/ on sys.path)
from shared.mock_webhook_receiver import SIGNATURE_HEADER, Delivery, WebhookReceiver, sign, verify_signature

__all__ = ["SIGNATURE_HEADER", "Delivery", "WebhookReceiver", "sign", "verify_signature"]
