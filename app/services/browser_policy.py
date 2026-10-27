import os


def browser_launch_options(engine: str) -> dict:
    """Return browser options that route all remote traffic through the egress proxy."""
    options = {"headless": True}
    proxy = os.getenv("VALIDATOR_HTTP_PROXY", "").strip()
    if os.getenv("APP_ENV", "").lower() == "production" and not proxy:
        raise RuntimeError("VALIDATOR_HTTP_PROXY is required in production.")
    if proxy:
        options["proxy"] = {"server": proxy}

    if engine == "chromium":
        options["chromium_sandbox"] = True
        if proxy:
            options["proxy"]["bypass"] = "<-loopback>"
    return options
