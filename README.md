# Agentic Website Smoke Validator

A portfolio proof of concept for running bounded, read-only smoke checks against public business websites. It uses FastAPI and Playwright to inspect a homepage, execute a small deterministic test plan, and return an HTML report with an optional PDF download.

**Status:** Prototype. The production validator now runs from this showcase repository. Public report submissions are paused at the reverse proxy until edge rate limiting is configured and verified; the homepage and health endpoint remain available.

## What it does

- Validates public HTTP(S) website URLs before browser navigation.
- Discovers a bounded set of visible page signals, such as the title, headings, links, forms, and footer.
- Runs five deterministic smoke cases in Chromium, Firefox, or WebKit.
- Records bounded console and network error evidence.
- Renders a self-contained HTML report and a one-time PDF download.
- Optionally uses a server-side OpenAI API key to explain selected diagnostics. The analyzer receives bounded diagnostic text, not page HTML, links, screenshots, or browser access. AI output cannot change deterministic results.

The default plan is intentionally small and fixed. Adaptive test selection and richer failure evidence are roadmap items, not current features.

## Safety and privacy boundaries

- The standard report workflow accepts public websites only; it does not authenticate, submit forms, or change site data.
- Navigation is bounded to the submitted homepage and up to three same-origin links, with sensitive paths excluded.
- Reports are not retained by the application. Report data is held in the browser tab; PDF rendering is a one-time request.
- Production URL checks resolve through the host's internal resolver and route browser traffic through an isolated egress proxy. The proxy and host network must continue blocking private, loopback, link-local, reserved, and cloud metadata destinations, including redirects and subresources.
- Public report and PDF endpoints are currently blocked at the reverse proxy until edge rate limiting is in place. The app's in-process run limit alone is not sufficient for public access.
- Chromium sandboxing must be explicitly enabled and verified in the deployment environment. Review [the deployment guide](docs/DEPLOYMENT.md) before exposing an instance to public traffic.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Process health and configured repository/commit identity |
| `GET` | `/` | Report runner UI |
| `POST` | `/api/intake` | Normalize a submitted URL and return a site profile |
| `POST` | `/api/test-plan` | Return the default deterministic smoke plan |
| `POST` | `/api/report` | Execute the smoke plan and return an HTML report; currently paused in production |
| `POST` | `/api/report.pdf` | Render submitted report HTML as a PDF without retaining it; currently paused in production |

## Run locally

Requires Python 3.12 or later. Playwright browser binaries are installed separately from the Python packages.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium firefox webkit
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. On Windows, activate the virtual environment with `.venv\\Scripts\\activate`.

To run the test suite:

```bash
python -m pytest -q
```

The optional diagnostic analyzer is disabled unless `OPENAI_API_KEY` is set in the server environment. Set `APP_REPOSITORY` and `APP_COMMIT_SHA` from the deployed source to identify the running build through `/health`. Never commit a populated `.env` file or paste a key into source, issues, or logs.

## Architecture

- **FastAPI** routes and Pydantic request models
- **Service layer** for URL validation, navigation, browser execution, planning, diagnostics, and report rendering
- **Playwright** for server-side Chromium, Firefox, and WebKit
- **Jinja2** templates for the runner and report
- **GitHub Actions** for tests on Python 3.12, 3.13, and 3.14

See [the deployment guide](docs/DEPLOYMENT.md) for operational requirements and launch controls.

## License

No license has been selected yet. Until a license is added, do not assume the code is available for reuse or redistribution.
