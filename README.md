# CryptoEdge Pro v2.2

Plataforma HFT para Binance Futures com trailing stop progressivo L1-L6, confluência de indicadores e gestão de risco.

## Stack
Node.js + Express | Python 3.12 | SQLite | Docker/EasyPanel | Telegram Bot

## Módulos
- `hft_strategy.py` — Engine principal (sinais, trail, ordens)
- `hft_indicators.py` — Indicadores técnicos (pure functions, testado)
- `hft_trail.py` — Trail stop logic (pure functions, testado)
- `gridbot.py` — WebSocket, Telegram, lifecycle
- `server.js` — API REST, auth, dashboard

## Sinais — Confluência 4 Etapas
1. HTF Trend (EMA30/80 + slope) → define direção
2. S/R Levels (swing points) → zona de interesse
3. 9 Indicadores (min 3 concordam) → confluência
4. Structure (higher lows / lower highs) → confirmação

## Trail Stop L1-L6
L1=0.30% (custos) → L2=0.50% → L3=0.80% → L4=1.20% (dinâmico) → L5=2.00% → L6=3.00%

## Testes
```bash
python3 bot/tests/run_tests.py  # 45 testes
```

## Comandos Telegram
`/start` `/stop` `/status` `/ajuda`

## Deploy
```bash
git push origin main --force  # EasyPanel auto-build
```
