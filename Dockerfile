# Multi-stage build keeps the final image small.
# Using the official multi-arch Python base (Docker Hub) so we don't depend
# on HA's base-image tag rotation. Works on linux/amd64, linux/arm64, linux/arm/v7.
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --user .

FROM python:3.11-slim-bookworm

# Non-root user (Debian/Ubuntu syntax — different from Alpine's addgroup -S)
RUN groupadd --system app \
 && useradd --system --gid app --home-dir /home/app --create-home app

COPY --from=builder /root/.local /home/app/.local
COPY --from=builder /build/src /app/src
ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    DATA_DIR=/data

RUN mkdir -p /data && chown app:app /data
USER app
WORKDIR /app

EXPOSE 8765
CMD ["uvicorn", "wall_dashboard.web:app", "--host", "0.0.0.0", "--port", "8765"]
