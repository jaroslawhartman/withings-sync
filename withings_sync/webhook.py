"""Module to send Withings measurements data to a generic webhook endpoint."""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("withings-sync")


def send_webhook(
    url: str,
    payload: dict[str, Any],
    secret: str | None = None,
    timeout: int = 30,
) -> bool:
    """Send measurement data payload to a generic webhook endpoint via HTTP POST.

    Supports authentication via a secret token (sent both as 'X-Webhook-Secret'
    HTTP header and inside the JSON payload), and handles HTTP redirects
    (such as Google Apps Script 302 redirects).

    Args:
        url: Webhook endpoint URL.
        payload: Dictionary containing measurement data and metadata.
        secret: Optional secret string or token for authentication.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        True if the request succeeded (HTTP 2xx or followed redirect), False otherwise.
    """
    if not url:
        log.warning("No webhook URL specified. Skipping webhook send.")
        return False

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "withings-sync",
    }

    # Ensure secret is included in payload if provided and not yet present
    if secret:
        headers["X-Webhook-Secret"] = secret
        if isinstance(payload, dict) and "secret" not in payload:
            payload["secret"] = secret

    try:
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers=headers,
            method="POST",
        )

        log.info("Sending payload to webhook: %s (%d bytes)", url, len(data_bytes))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            log.debug("Webhook response code %s: %s", resp.status, resp_body)
            log.info("Successfully sent measurements to webhook.")
            return True

    except urllib.error.HTTPError as e:
        err_body = (
            e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        )
        log.error("Webhook request failed with HTTP %d: %s", e.code, err_body)
        return False
    except urllib.error.URLError as e:
        log.error("Webhook connection failed: %s", e.reason)
        return False
    except Exception as e:  # noqa: BLE001
        log.error("Unexpected error sending webhook: %s", e)
        return False
