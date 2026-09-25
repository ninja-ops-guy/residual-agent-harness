FROM python:3.12.14-slim-bookworm AS python-runtime

FROM ollama/ollama:0.34.0

# Ollama's pinned image supplies the native CPU/GPU runtime and its libraries.
RUN apt-get update && apt-get install -y --no-install-recommends git zstd nodejs npm \
    libbz2-1.0 libffi8 liblzma5 libsqlite3-0 libssl3t64 zlib1g \
    libreadline8t64 libncursesw6 libgdbm6t64 libexpat1 libuuid1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 station \
    && mkdir -p /data /app /projects \
    && chown -R station:station /data /app /projects
# Keep Ollama's native libraries; use patched upstream Python instead of Ubuntu's 3.12.3.
COPY --from=python-runtime /usr/local/ /usr/local/
RUN ldconfig
WORKDIR /app
COPY --chown=station:station residual /app/residual
COPY --chown=station:station ai_providers /app/ai_providers
COPY --chown=station:station observation_layer /app/observation_layer
COPY --chown=station:station vendor /app/vendor
RUN python3 -c "import bz2, ctypes, lzma, platform, readline, sqlite3, ssl; from residual.station.archive import require_data_filter; require_data_filter(); print(platform.python_version())"
USER station
ENV RESIDUAL_DATA=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1
EXPOSE 8765
HEALTHCHECK --interval=20s --start-period=20s --timeout=4s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/bootstrap', timeout=3)"
ENTRYPOINT ["python3", "-m", "residual.station.server"]
CMD ["--host", "0.0.0.0", "--port", "8765", "--start-ollama"]
