FROM ollama/ollama:0.34.0

# Ollama's pinned image supplies the native CPU/GPU runtime and its libraries.
RUN apt-get update && apt-get install -y --no-install-recommends python3 git zstd nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 station \
    && mkdir -p /data /app /projects \
    && chown -R station:station /data /app /projects
WORKDIR /app
COPY --chown=station:station residual /app/residual
COPY --chown=station:station ai_providers /app/ai_providers
COPY --chown=station:station observation_layer /app/observation_layer
COPY --chown=station:station vendor /app/vendor
USER station
ENV RESIDUAL_DATA=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1
EXPOSE 8765
HEALTHCHECK --interval=20s --start-period=20s --timeout=4s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap', timeout=3)"
ENTRYPOINT ["python3", "-m", "residual.station.server"]
CMD ["--host", "0.0.0.0", "--port", "8765", "--start-ollama"]
