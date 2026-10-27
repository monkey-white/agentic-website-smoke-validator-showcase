import ipaddress
import os
import socket
from urllib.parse import urlparse

from app.services.remote_dns import resolve_remote


ALLOWED_PORTS = {80, 443}


def normalize_url(raw_url: str) -> str:
    cleaned_url = raw_url.strip()

    if not cleaned_url:
        raise ValueError("URL is required.")

    initial_parse = urlparse(cleaned_url)

    if initial_parse.scheme and initial_parse.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https.")

    if not initial_parse.scheme:
        cleaned_url = f"https://{cleaned_url}"

    parsed_url = urlparse(cleaned_url)

    if parsed_url.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https.")

    if not parsed_url.netloc:
        raise ValueError("URL must include a valid domain.")

    return cleaned_url.rstrip("/")


def validate_public_url(raw_url: str) -> str:
    normalized_url = normalize_url(raw_url)
    parsed_url = urlparse(normalized_url)

    if parsed_url.username or parsed_url.password:
        raise ValueError("URL must not include credentials.")

    try:
        port = parsed_url.port
    except ValueError as error:
        raise ValueError("URL must include a valid port.") from error

    if port is not None and port not in ALLOWED_PORTS:
        raise ValueError("URL must use the standard HTTP or HTTPS port.")

    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("URL must include a valid domain.")

    if os.getenv("VALIDATOR_DNS_URL"):
        addresses = resolve_remote(hostname)
    elif os.getenv("APP_ENV", "").lower() == "production":
        raise ValueError("URL host could not be resolved.")
    else:
        addresses = _resolve_host_addresses(hostname)
    try:
        contains_non_public_address = any(
            not ipaddress.ip_address(address).is_global for address in addresses
        )
    except ValueError as error:
        raise ValueError("URL host could not be resolved.") from error
    if contains_non_public_address:
        raise ValueError("URL must resolve only to public addresses.")

    return normalized_url


def _resolve_host_addresses(hostname: str) -> set[str]:
    try:
        address_records = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as error:
        raise ValueError("URL host could not be resolved.") from error

    addresses = {record[4][0] for record in address_records}
    if not addresses:
        raise ValueError("URL host could not be resolved.")

    return addresses
