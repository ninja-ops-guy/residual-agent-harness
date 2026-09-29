FROM python:3.12-slim
RUN useradd --create-home --uid 10001 gateway \
    && mkdir -p /app /state \
    && chown -R gateway:gateway /app /state
WORKDIR /app
COPY --chown=gateway:gateway demo/cloud_gateway/server.py /app/server.py
ENV PYTHONUNBUFFERED=1 PORT=8080 RESIDUAL_DEMO_DB=/state/gateway.sqlite3
EXPOSE 8080
USER gateway
CMD ["python3", "/app/server.py"]
