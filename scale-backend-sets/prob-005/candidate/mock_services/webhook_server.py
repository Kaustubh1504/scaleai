"""Run the mock webhook receiver as a local HTTP server.

    python -m mock_services.webhook_server --port 9100 [--secret whsec_tasks --fail-first 2 --default-status 200]

It accepts POSTs on any path; GET /_deliveries lists what it received.
"""

import mock_services  # noqa: F401
from shared.mock_webhook_receiver.__main__ import main

if __name__ == "__main__":
    main()
