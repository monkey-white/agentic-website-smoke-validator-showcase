"""Live checks from the isolated validator container, not configuration assertions."""
import http.client
import socket
from urllib.request import ProxyHandler, build_opener
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright
from app.services.browser_policy import browser_launch_options
from app.services.url_validator import validate_public_url


def require(value, message):
    if not value:
        raise RuntimeError(message)


def check_proxy():
    proxy = build_opener(ProxyHandler({"http": "http://egress:3128", "https": "http://egress:3128"}))
    for target in (
        "http://127.0.0.1/", "http://10.0.0.1/", "http://100.100.100.200/",
        "http://169.254.169.254/latest/meta-data/", "http://172.16.0.1/",
        "http://192.168.0.1/", "http://[::1]/", "http://[fd00::1]/",
        "http://resolver/", "http://example.com:22/",
    ):
        try:
            proxy.open(target, timeout=10).close()
        except HTTPError as error:
            require(error.code == 403, f"Expected policy denial for {target}, got {error.code}")
        else:
            raise RuntimeError(f"Proxy did not deny {target}")
        print("PASS: proxy denied", target, flush=True)
    for target, port in (("169.254.169.254", 443), ("example.com", 22)):
        connection = http.client.HTTPConnection("egress", 3128, timeout=10)
        try:
            connection.set_tunnel(target, port)
            try:
                connection.connect()
            except OSError as error:
                require("403" in str(error), f"Expected CONNECT denial, got {error}")
            else:
                raise RuntimeError("Forbidden CONNECT tunnel opened")
        finally:
            connection.close()
        print(f"PASS: CONNECT denied {target}:{port}", flush=True)
    with proxy.open("https://example.com/", timeout=30) as response:
        require(response.status == 200, "Public HTTPS proxy check failed")
        require(b"Example Domain" in response.read(65536), "Unexpected public HTTPS body")
    print("PASS: proxy permits verified public HTTPS", flush=True)


def check_direct():
    for target, port in (("1.1.1.1", 443), ("169.254.169.254", 80), ("10.0.0.1", 22)):
        try:
            connection = socket.create_connection((target, port), timeout=3)
        except OSError:
            print(f"PASS: direct connection unavailable {target}:{port}", flush=True)
        else:
            connection.close()
            raise RuntimeError(f"Direct route unexpectedly available {target}:{port}")


def check_browsers():
    with sync_playwright() as runtime:
        for engine in ("chromium", "firefox", "webkit"):
            print("START: actual browser proxy policy", engine, flush=True)
            browser = getattr(runtime, engine).launch(**browser_launch_options(engine), timeout=20000)
            try:
                page = browser.new_page()
                response = page.goto("https://example.com/", timeout=30000, wait_until="domcontentloaded")
                require(response and response.status == 200, engine + " public navigation failed")
                require("Example Domain" in page.title(), engine + " unexpected title")
                response = page.goto("http://169.254.169.254/", timeout=15000, wait_until="domcontentloaded")
                require(response and response.status == 403, engine + " metadata policy denial missing")
            finally:
                browser.close()
            print("PASS:", engine, "public website allowed, metadata denied", flush=True)


if __name__ == "__main__":
    check_direct()
    check_proxy()
    require(validate_public_url("https://example.com") == "https://example.com", "Application DNS failed")
    try:
        validate_public_url("http://169.254.169.254")
    except ValueError:
        print("PASS: application DNS/URL validation rejects metadata", flush=True)
    else:
        raise RuntimeError("Application URL validation accepted metadata")
    check_browsers()
    print("PASS: all isolation checks finished.", flush=True)
