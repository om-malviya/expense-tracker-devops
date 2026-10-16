# Expense Tracker API image.
# python:3.12-slim keeps the attack surface (and the Trivy finding count) small compared to the
# full Debian image, while still shipping the libc that psycopg[binary] wheels need.
FROM python:3.12-slim

# Do not write .pyc files; flush stdout so container logs show up immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
# After installing, pip/setuptools/wheel are removed from the image: Trivy flagged CVEs in the
# libraries pip vendors (and nothing at runtime needs pip), so dropping them keeps the image
# scan clean. This is deliberate - do not "fix" it by re-adding pip.
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall -y pip setuptools wheel

# Only what the server needs: migrations + application code (tests stay out via .dockerignore).
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Run as an unprivileged, numeric UID so Kubernetes `runAsNonRoot` can verify it.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001

EXPOSE 8000

# The slim image has no curl, so the liveness check uses the standard library instead.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# Apply pending migrations, then serve. Running Alembic here (instead of create_all in the app)
# means the schema is versioned and every container start converges the database.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
