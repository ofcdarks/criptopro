# ============================================================
# CryptoEdge Pro v2.0.1 — Production Build
# ============================================================

FROM node:20-slim AS production

WORKDIR /app

# Sistema: openssl (bcrypt), python3 (bot), wget (healthcheck)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      openssl wget python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Usuário não-root
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Dependências Node
COPY package.json package-lock.json* ./
RUN npm install --omit=dev 2>/dev/null || npm install

# Dependências Python (bot)
COPY bot/requirements.txt ./bot/requirements.txt
RUN python3 -m pip install --no-cache-dir --break-system-packages -r bot/requirements.txt 2>/dev/null || true

# Código da aplicação
COPY server.js db.js ./
COPY public/ ./public/
COPY bot/ ./bot/
COPY templates/ ./templates/
COPY integrations/ ./integrations/
COPY healthcheck.sh ./

# Dados e permissões
RUN mkdir -p /data && chown -R appuser:appgroup /app /data

ENV NODE_ENV=production
ENV PORT=3000
ENV DB_PATH=/data

EXPOSE 3000
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD wget -qO- http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
