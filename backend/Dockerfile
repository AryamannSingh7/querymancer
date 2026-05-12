# syntax=docker/dockerfile:1.7
# ---------- builder ----------
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY pyproject.toml ./

# Read [project.dependencies] out of pyproject.toml (tomllib is stdlib on 3.11)
# and install them into a venv. We don't install the project package itself —
# the app is run from /home/user/app at runtime, with CWD on sys.path.
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/python -c "import tomllib,sys; \
deps=tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; \
open('/tmp/requirements.txt','w').write('\n'.join(deps))" \
 && /opt/venv/bin/pip install -r /tmp/requirements.txt

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# HF Spaces convention: a non-root `user` with UID 1000 owns the workspace.
RUN useradd --create-home --uid 1000 user

COPY --from=builder /opt/venv /opt/venv

WORKDIR /home/user/app

COPY --chown=user:user app ./app
COPY --chown=user:user cli ./cli
COPY --chown=user:user databases ./databases

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
