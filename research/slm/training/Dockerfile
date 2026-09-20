# Reproducible single-GPU training container for EXP-M6-SLM.
# Machinery only — no training runs before the SLM-00 benchmark freeze.
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Deterministic seed defaults (overridable at runtime).
    SLM_SEED=1337 \
    PYTHONHASHSEED=1337 \
    CUBLAS_WORKSPACE_CONFIG=:4096:8 \
    TORCH_CUDNN_DETERMINISTIC=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY scaffold /app/scaffold
COPY configs /app/configs
COPY entrypoint.sh /app/entrypoint.sh

# Non-root user for all training/eval work.
RUN useradd --create-home --uid 10001 slm \
    && chmod +x /app/entrypoint.sh \
    && mkdir -p /app/runs /app/data \
    && chown -R slm:slm /app
USER slm

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--help"]
