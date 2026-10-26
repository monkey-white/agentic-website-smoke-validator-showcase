# Deployment Guide

This is an operational checklist for a future deployment. It does not describe an active production host. The application is stateless: it has no database, worker process, account system, or server-side report retention.

## Runtime contract

- ASGI application: `app.main:app`
- One Uvicorn worker. Browser concurrency and rate-limit counters are process-local.
- Bind Uvicorn to loopback behind a TLS-terminating reverse proxy.
- Install the Playwright browsers for the exact pinned Playwright version in `requirements.txt`.
- Keep browser processes under a dedicated unprivileged service account with explicit CPU and memory limits.

## Public deployment gates

The application opens visitor-supplied URLs. Complete and verify all of the following before routing public traffic to it:

1. Enable Chromium sandboxing at each Chromium launch site. Playwright's `chromium_sandbox` option defaults to false, and this project must explicitly opt in. Do not work around host restrictions with `--no-sandbox` or by globally disabling OS namespace protections.
2. Apply host or cloud-network egress rules that block loopback, private, link-local, reserved, and cloud metadata destinations for IPv4 and IPv6. Cover DNS changes, redirects, and browser subresources, not only the initial URL validation.
3. Run the browsers as an unprivileged account. Verify Chromium, Firefox, and WebKit under the actual service account and operating system before offering each engine.
4. Set resource limits for the service. The application permits one in-process browser task at a time, but that alone does not bound memory or CPU use on the host.
5. Add edge rate limiting. The application has a 10-run-per-client-address rolling-hour limit in process memory; it resets on restart and does not replace a proxy or network-edge limit. Configure trusted proxy headers so client addresses are derived only from the proxy.
6. Terminate TLS at the reverse proxy, redirect HTTP to HTTPS, and set HSTS. Keep Uvicorn inaccessible from the public network.
7. Set proxy request-size and response-time limits. PDF rendering accepts report HTML up to 1,000,000 characters and smoke runs have a 240-second execution budget; allow a reasonable buffer above those limits.
8. Keep logs free of request bodies, report HTML, secrets, and database URLs. Use short retention and restrict log access.

## Deploying an instance

1. Create a dedicated, unprivileged service account and a supported Linux host with sufficient memory and disk for the application and browser binaries.
2. Configure inbound access for SSH from trusted administrator addresses and HTTPS through the reverse proxy. Keep the application port private.
3. Configure outbound restrictions from the browser process or VM so public websites can be visited while private and metadata destinations remain blocked.
4. Check out the reviewed `main` branch using a read-only deployment credential. Do not store credentials in the repository.
5. Create a virtual environment, install `requirements.txt`, and install the supported Playwright browsers and OS libraries.
6. Store `OPENAI_API_KEY` in a protected service environment only if optional diagnostic analysis is enabled. Reports remain available without the key.
7. Configure one Uvicorn worker behind the reverse proxy. Apply service resource limits and restart-on-failure behavior.
8. Set `APP_REPOSITORY` to the canonical owner/repository and `APP_COMMIT_SHA` to the exact checked-out revision before starting the service.
9. Run the full test suite on the host. Verify `GET /health` reports the expected repository and full commit SHA, then verify one representative smoke run, PDF download, and each browser engine offered in the UI.
10. Verify that private, loopback, link-local, and metadata-style destinations are blocked from browser traffic; verify rate limits, concurrency limits, proxy timeouts, and logs.
11. Point the public domain to the instance only after these checks pass. Keep the prior deployment available during a short rollback window.

## Configuration and data

`OPENAI_API_KEY` is the only application secret currently used. The application does not need a database URL or persistent volume. Report HTML is sent back by the browser for one-time PDF rendering, with JavaScript disabled and browser network requests blocked; it is not stored by the application.

Do not commit `.env` files, API keys, SSH keys, server addresses, service-unit contents, or provider credentials. Use a repository-specific read-only deploy key or a protected CI secret for deployment access.
