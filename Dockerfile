# Multi-stage build keeps the final image small.
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.11-alpine-3.19
FROM ${BUILD_FROM} AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --user .

FROM ${BUILD_FROM}

# Non-root user
RUN addgroup -S app && adduser -S app -G app
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
