import json
import os
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener


MAX_RESPONSE_BYTES = 16_384
ALLOWED_RESOLVER = "http://resolver:8053"


def resolve_remote(hostname: str) -> set[str]:
    endpoint = os.getenv("VALIDATOR_DNS_URL", "").rstrip("/")
    if endpoint != ALLOWED_RESOLVER:
        raise ValueError("URL host could not be resolved.")

    request = Request(
        f"{endpoint}/resolve?{urlencode({'host': hostname})}",
        headers={"Accept": "application/json"},
    )
    try:
        # Bypass the browser egress proxy only for the fixed internal resolver.
        with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("URL host could not be resolved.")
        data = json.loads(payload)
        addresses = data.get("addresses")
        if not isinstance(addresses, list) or not addresses:
            raise ValueError("URL host could not be resolved.")
        if any(not isinstance(address, str) for address in addresses):
            raise ValueError("URL host could not be resolved.")
        return set(addresses)
    except (OSError, URLError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("URL host could not be resolved.") from error
