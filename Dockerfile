# Multi-stage build keeps the final image small.
# Using the official multi-arch Python base (Docker Hub) so we don't depend
# on HA's base-image tag rotation. Works on linux/amd64, linux/arm64, linux/arm/v7.
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --user .

FROM python:3.11-slim-bookworm

# Runs as root inside the container. HA Supervisor bind-mounts /data from the host
# and owns that mount as root; trying to drop privileges to a non-root user breaks
# writes to /data (the in-image chown is overridden by the host mount).
COPY --from=builder /root/.local /root/.local
COPY --from=builder /build/src /app/src
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    DATA_DIR=/data

WORKDIR /app

EXPOSE 8765
CMD ["uvicorn", "wall_dashboard.web:app", "--host", "0.0.0.0", "--port", "8765"]
