# Deployment Guide

This guide describes the showcase deployment on a shared production host. It is stateless: it has no database, worker process, account system, or server-side report retention. The validator runs in its own container on the host's pre-existing isolated browser network. Deployments must target only the `validator` service.

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
4. Set resource limits for the service. The production container is limited to 3 GiB memory, 2 CPUs, 256 processes, and 512 MiB shared memory. The application permits one in-process browser task at a time.
5. Add edge rate limiting. The application has a 10-run-per-client-address rolling-hour limit in process memory; it resets on restart and does not replace a proxy or network-edge limit. Configure trusted proxy headers so client addresses are derived only from the proxy.
6. Terminate TLS at the reverse proxy, redirect HTTP to HTTPS, and set HSTS. Keep Uvicorn inaccessible from the public network.
7. Set proxy request-size and response-time limits. PDF rendering accepts report HTML up to 1,000,000 characters and smoke runs have a 240-second execution budget; allow a reasonable buffer above those limits.
8. Keep logs free of request bodies, report HTML, secrets, and database URLs. Use short retention and restrict log access.

## Deploying an instance

1. Create a dedicated, unprivileged service account and a supported Linux host with sufficient memory and disk for the application and browser binaries.
2. Configure inbound access for SSH from trusted administrator addresses and HTTPS through the reverse proxy. Keep the application port private.
3. Configure outbound restrictions from the browser process or VM so public websites can be visited while private and metadata destinations remain blocked.
4. On the host, clone the reviewed `main` branch of `monkey-white/agentic-website-smoke-validator-showcase` into a dedicated checkout. The public repository requires no deployment credential to fetch. Never store write credentials on the host.
5. Record the current image ID for rollback and tag it `agentic-website-smoke-validator:rollback-current`. Build the showcase image with both `APP_COMMIT_SHA` and `VALIDATOR_IMAGE_TAG` set to the exact reviewed commit SHA. Keep the previous image tag until the rollback window expires.
6. Start a staging container on the existing browser network under a separate name and alias. Set `APP_ENV=production`, `VALIDATOR_DNS_URL=http://resolver:8053`, and `VALIDATOR_HTTP_PROXY=http://egress:3128`; apply the same user, seccomp profile, read-only root, dropped capabilities, and resource limits as production.
7. Run `python /app/check_network.py` inside that staging container. It must confirm direct egress is blocked, the proxy denies private/reserved/metadata destinations while allowing public HTTPS, and all three browsers are sandboxed and obey that policy. Do not route public requests to a build that fails any check.
8. Set `COMPOSE_PROJECT_NAME` to the existing host stack name and `VALIDATOR_BROWSER_NETWORK` to its pre-existing isolated browser network. Replace only the `validator` service with `APP_COMMIT_SHA=<full-sha> VALIDATOR_IMAGE_TAG=<full-sha> docker compose -p "$COMPOSE_PROJECT_NAME" -f compose.production.yaml up -d --no-deps validator`. Do not run a broad host stack update.
9. Verify `GET /health` reports the showcase repository and the exact full commit SHA. Confirm the validator is healthy, the Caddy route still reaches it, and a representative smoke run and PDF download work. Re-run the network check in the production container.
10. Keep the previous image ID available for rollback. If verification fails, set `VALIDATOR_IMAGE_TAG=rollback-current` and restart only the validator service; do not remove the preserved image until the new deployment is accepted.

## Configuration and data

`OPENAI_API_KEY` is the only application secret currently used. The application does not need a database URL or persistent volume. Report HTML is sent back by the browser for one-time PDF rendering, with JavaScript disabled and browser network requests blocked; it is not stored by the application.

Do not commit `.env` files, API keys, SSH keys, server addresses, service-unit contents, or provider credentials. `deploy/seccomp_profile.json` is the reviewed host-tested syscall policy; `deploy/check_network.py` contains live checks and no credentials. The `compose.production.yaml` file defines only the validator service and connects to a pre-existing isolated browser network supplied by the host.
