# ── AJSON — Agent JSON Compiler ──────────────────────────────
# https://github.com/narko4u/ajson
# ghcr.io/narko4u/ajson

FROM python:3.12-slim AS builder

WORKDIR /app
RUN pip install --no-cache-dir ajson-spec==0.1.1

# ── Runtime ─────────────────────────────────────────────────
FROM python:3.12-slim

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/ajson /usr/local/bin/ajson

ENTRYPOINT ["ajson"]
CMD ["--help"]
