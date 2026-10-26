import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.routes import intake, report, smoke_plan


load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(override=True)

app = FastAPI(title="Agentic Website Smoke Validator")


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'"
    )
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(intake.router)
app.include_router(smoke_plan.router)
app.include_router(report.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "repository": os.getenv("APP_REPOSITORY", "unknown").strip() or "unknown",
        "commit": os.getenv("APP_COMMIT_SHA", "unknown").strip() or "unknown",
    }
