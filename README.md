# 🎯 CLAUDE L-NACIONAL v2

Sistema de análisis estadístico para **Gana Más** y **Nacional Noche**.
Corre 100% en **GitHub Actions** — sin servidor, sin costo.

## 🔄 Flujo automático

Cada vez que el Action corre (12 PM y 4 PM RD):

```
1. Carga data/history.xlsx (tu historial real desde 2020)
2. Verifica si la última fecha está actualizada
3. Si falta algún resultado → lo scrapes de loteriasdominicanas.com
4. Corre los 9 métodos estadísticos + WMA
5. Genera los picks para el próximo sorteo
6. Envía mensaje a Telegram
7. Hace commit del historial actualizado al repo
```

## 📁 Estructura

```
claude-l-nacional/
├── data/
│   ├── history.xlsx       ← Tu historial real (nunca se pierde)
│   ├── picks_log.json     ← Log de picks generados
│   └── performance.json   ← Stats de performance
├── src/
│   ├── loader.py          ← Lee Excel, detecta feriados, scrapes faltantes
│   ├── engine.py          ← Los 9 métodos de análisis + WMA
│   └── telegram_bot.py    ← Mensajes de Telegram
├── generate_picks.py      ← Script principal
└── .github/workflows/
    └── picks.yml          ← Action (12 PM + 4 PM automático)
```

## 🚀 Setup

```bash
git init && git add . && git commit -m "CLAUDE L-NACIONAL v2"
git remote add origin https://github.com/TU_USUARIO/claude-l-nacional.git
git push -u origin main
```

**Settings → Secrets:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

**Settings → Actions → "Read and write permissions"**

## 🧠 Métodos (9 + WMA)

| # | Método | Librería |
|---|--------|----------|
| 1 | Rating de Rentabilidad (fórmula dominicana) | Python |
| 2 | Overdue / Gap Analysis | Python |
| 3 | Co-ocurrencia | Python |
| 4 | Sum Analysis | NumPy |
| 5 | Chi² | SciPy |
| 6 | Mutual Information | Sklearn |
| 7 | Markov Chain (1-paso + 2-paso) | NumPy |
| 8 | Inferencia Bayesiana (Dirichlet) | SciPy |
| 9 | Monte Carlo (10k simulaciones) | NumPy |
| + | WMA transversal | NumPy |

## ⚠️ Días feriados

El sistema detecta automáticamente cuando el sitio repite los números
del día anterior (patrón de feriado) y los omite del análisis.

## ⚠️ Disclaimer

Solo para análisis estadístico. Juega responsablemente.
