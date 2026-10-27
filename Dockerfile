FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    APP_ENV=production

ARG APP_COMMIT_SHA=unknown
ENV APP_REPOSITORY=monkey-white/agentic-website-smoke-validator-showcase \
    APP_COMMIT_SHA=${APP_COMMIT_SHA}

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY deploy/check_network.py ./check_network.py

USER pwuser
EXPOSE 8010
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips=*"]
