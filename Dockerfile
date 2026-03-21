# ============================================================
# CryptoEdge Pro v2.0.1 — Production Build
# ============================================================

FROM node:20-slim

WORKDIR /app

# Sistema: openssl (bcrypt), python3 + pip (bot), wget (healthcheck)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      openssl wget python3 python3-pip python3-venv procps && \
    rm -rf /var/lib/apt/lists/*

# Dependências Node
COPY package.json package-lock.json* ./
RUN npm install --omit=dev 2>/dev/null || npm install

# Dependências Python (bot) — sem venv, direto no sistema
COPY bot/requirements.txt ./bot/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages \
      python-binance==1.0.19 \
      python-dotenv==1.0.1 \
      requests==2.31.0 \
      websocket-client==1.7.0 && \
    python3 -c "from binance.client import Client; print('✅ python-binance OK')"

# Código da aplicação
COPY server.js db.js ./
COPY public/ ./public/
COPY bot/ ./bot/
COPY templates/ ./templates/
COPY integrations/ ./integrations/
COPY healthcheck.sh ./

RUN mkdir -p /data && chmod 777 /data

ENV NODE_ENV=production
ENV PORT=3000
ENV DB_PATH=/data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD wget -qO- http://localhost:3000/api/health || exit 1

# Fix permissões do volume montado + inicia Node
CMD ["sh", "-c", "chmod -R 777 /data 2>/dev/null; node server.js"]
