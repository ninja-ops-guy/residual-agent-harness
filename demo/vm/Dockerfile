FROM --platform=linux/386 docker.io/i386/debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates git python3 python3-pip python3-venv less procps \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash residual \
    && mkdir -p /home/user/documents \
    && chmod 0755 /home/user /home/user/documents

COPY --chown=residual:residual residual-src/ /opt/residual/

RUN python3 -m pip install --break-system-packages --no-deps -e /opt/residual \
    && printf '%s\n' \
      'stty sane 2>/dev/null || true' \
      'stty echo 2>/dev/null || true' \
      'export PS1="\[\033[01;32m\]residual@demo\[\033[00m\]:\[\033[01;34m\]~/residual-agent-harness\[\033[00m\]$ "' \
      'alias mission="python3 -m residual.workbench"' \
      'alias demo="python3 -m residual demo --output runs/demo"' \
      'alias verify-demo="python3 -m residual verify-trace runs/demo/trace.jsonl --result runs/demo/result.json"' \
      'cloud-demo() { printf "Legacy cloud-demo transport is retired in this WebVM. Use Mission Control > Connect provider > Run mission.\\n"; return 2; }' \
      'printf "\\033[1;32mRESIDUAL // LIVE SYSTEM\\033[0m\\n"' \
      'printf "Disposable browser VM · Debian · Python 3 · repository preloaded\\n\\n"' \
      'printf "Try:\\n  mission audit --stream --files README.md residual/cli.py\\n  demo  # scripted tutorial\\n  verify-demo\\n  mission --help   # live workbench usage\\n\\n"' \
      'printf "LIVE PROMPTS: use Mission Control and its separate provider setup tab. Authentication stays outside the VM.\\n\\n"' \
      'printf "Inspect the actual repo, traces, receipts, and verifier output.\\n\\n"' \
      >> /home/residual/.bashrc \
    && printf '%s\n' 'if [ -f ~/.bashrc ]; then . ~/.bashrc; fi' > /home/residual/.bash_profile \
    && printf '%s\n' \
      '#!/bin/bash' \
      'export HOME=/home/residual USER=residual SHELL=/bin/bash TERM=xterm LANG=C LC_ALL=C PYTHONUNBUFFERED=1 RESIDUAL_WEBVM_SLEEP_BACKEND=legacy-nanosleep' \
      'cd /opt/residual || { echo "RESIDUAL BOOT ERROR: /opt/residual missing"; exec /bin/bash -i; }' \
      'stty sane 2>/dev/null || true' \
      'stty echo 2>/dev/null || true' \
      'echo "RESIDUAL BOOT: guest process attached"' \
      'printf "user="; id -un 2>/dev/null || true' \
      'printf "cwd="; pwd' \
      'test -f pyproject.toml && echo "repo=present" || echo "repo=MISSING"' \
      'exec /bin/bash --noprofile --rcfile /home/residual/.bashrc -i' \
      > /usr/local/bin/residual-demo-shell \
    && chmod 0755 /usr/local/bin/residual-demo-shell \
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
    PYTHONUNBUFFERED=1 \
    RESIDUAL_WEBVM_SLEEP_BACKEND=legacy-nanosleep

CMD ["/usr/local/bin/residual-demo-shell"]
