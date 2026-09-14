FROM --platform=linux/386 docker.io/i386/debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates git python3 python3-pip python3-venv less procps \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash residual

COPY --chown=residual:residual residual-src/ /opt/residual/

RUN python3 -m pip install --break-system-packages --no-deps -e /opt/residual \
    && printf '%s\n' \
      'stty sane 2>/dev/null || true' \
      'stty echo 2>/dev/null || true' \
      'export PS1="\[\033[01;32m\]residual@demo\[\033[00m\]:\[\033[01;34m\]~/residual-agent-harness\[\033[00m\]$ "' \
      'alias demo="python3 -m residual demo --output runs/demo"' \
      'alias verify-demo="python3 -m residual verify-trace runs/demo/trace.jsonl --result runs/demo/result.json"' \
      'alias cloud-demo="bash examples/onboarding/cloud_demo.sh"' \
      'clear' \
      'printf "\\033[1;32mRESIDUAL // LIVE SYSTEM\\033[0m\\n"' \
      'printf "Disposable browser VM · Debian · Python 3 · repository preloaded\\n\\n"' \
      'printf "Try:\\n  demo\\n  verify-demo\\n  cloud-demo   # available when an ephemeral cloud session was provisioned\\n\\n"' \
      'if [ -n "${LLM_API_KEY:-}" ]; then printf "\\033[1;32mCLOUD SESSION: READY\\033[0m · bounded ephemeral gateway\\n\\n"; else printf "CLOUD SESSION: OFFLINE FALLBACK\\n\\n"; fi' \
      'printf "Inspect the actual repo, traces, receipts, and verifier output.\\n\\n"' \
      >> /home/residual/.bashrc \
    && printf '%s\n' 'if [ -f ~/.bashrc ]; then . ~/.bashrc; fi' > /home/residual/.bash_profile \
    && chown residual:residual /home/residual/.bashrc /home/residual/.bash_profile

USER residual
WORKDIR /opt/residual
ENV HOME=/home/residual \
    TERM=xterm \
    USER=residual \
    SHELL=/bin/bash \
    EDITOR=vi \
    LANG=C \
    LC_ALL=C \
    PYTHONUNBUFFERED=1

CMD ["/bin/bash", "--noprofile", "--rcfile", "/home/residual/.bashrc", "-i"]
