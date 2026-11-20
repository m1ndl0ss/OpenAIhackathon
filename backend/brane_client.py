"""Matvei's BRANE entry point. The bootstrap probe reads the team policy only."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def live_config():
    base_url = os.getenv("BRANE_BASE_URL", "https://brane.ai-z.io/api/v1").rstrip("/")
    address = urlsplit(base_url)
    if (address.scheme != "https" or not address.hostname or address.username is not None
            or address.password is not None or address.query or address.fragment):
        raise RuntimeError("BRANE_BASE_URL must be the assigned HTTPS API base URL.")
    token = os.getenv("BRANE_API_KEY") or os.getenv("BRANE_TOKEN")
    if not token:
        raise RuntimeError("Set BRANE_API_KEY to the AI-Z team credential before running the live check.")
    return base_url, token


def check_policy():
    base_url, token = live_config()
    request = Request(base_url + "/policy", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with build_opener(_NoRedirect()).open(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError("BRANE did not return the team policy.")
            policy = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"BRANE policy check returned HTTP {error.code}.") from None
    except (ValueError, URLError, TimeoutError, OSError):
        raise RuntimeError("BRANE policy check unavailable. Check the assigned host and network.") from None
    if not isinstance(policy, dict) or not any(field in policy for field in ("categories", "summary", "routingMode")):
        raise RuntimeError("BRANE response did not contain a recognised team policy.")
