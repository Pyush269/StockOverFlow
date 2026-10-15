# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4
FROM ${PYTHON_IMAGE} AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.lock.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install -r requirements.lock.txt \
    && /opt/venv/bin/pip check

FROM dependencies AS tests
ENV PATH="/opt/venv/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-dev.lock.txt ./
RUN /opt/venv/bin/pip install -r requirements-dev.lock.txt && /opt/venv/bin/pip check
RUN addgroup -S -g 10001 stockflow && adduser -S -D -H -u 10001 -G stockflow stockflow
WORKDIR /app
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini pytest.ini ./
COPY tests ./tests
USER 10001:10001
CMD ["python", "-m", "pytest", "-v", "-p", "no:cacheprovider"]

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN addgroup -S -g 10001 stockflow \
    && adduser -S -D -H -u 10001 -G stockflow stockflow
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 alembic ./alembic
COPY --chown=10001:10001 alembic.ini ./
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=12 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
