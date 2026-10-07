# python:3.12-slim pinned by digest (linux/amd64, resolved via Docker Hub API
# 2026-09-26; arm64 alt sha256:950206c37262dd86c55659797f6ee418fee30535072f65a82ed470d985f5cda5).
FROM python:3.12-slim@sha256:44ff437bba879d4941b710a369a8f19266aea34b29002807f0c487fabc9eec9b
WORKDIR /app
COPY demo/cloud_gateway/server.py /app/server.py
ENV PYTHONUNBUFFERED=1 PORT=8080
EXPOSE 8080
CMD ["python3", "/app/server.py"]
