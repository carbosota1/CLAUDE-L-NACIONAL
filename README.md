# 🎯 CLAUDE L-NACIONAL

Sistema de análisis estadístico para **Gana Más** y **Nacional Noche** (República Dominicana).
Corre 100% en **GitHub Actions** — sin servidor, sin costo.

---

## 🧠 Métodos de Análisis (9 + WMA)

| # | Método | Librería | Descripción |
|---|--------|----------|-------------|
| 1 | Rating de Rentabilidad | Python puro | Fórmula dominicana: 1ra=60pts, 2da=8pts, 3ra=4pts |
| 2 | Overdue / Gap Analysis | Python puro | Sorteos desde la última aparición |
| 3 | Co-ocurrencia | Python puro | Probabilidad de transición entre sorteos |
| 4 | Sum Analysis | NumPy | Rango histórico de sumas |
| 5 | Chi² | `scipy.stats.chisquare` | Validación estadística real (p-value) |
| 6 | Mutual Information | `sklearn.metrics` | Dependencia real entre sorteos consecutivos |
| 7 | Markov Chain | NumPy matrices | Transición 1-paso + 2-paso superpuesta |
| 8 | Inferencia Bayesiana | SciPy Dirichlet | Sistema auto-aprendiente |
| 9 | Monte Carlo | NumPy RNG | 10,000 simulaciones de sorteos virtuales |
| + | WMA | NumPy | Capa transversal: sorteos recientes pesan más |

**Pesos del score compuesto:**
Rating 15% · Overdue 10% · Co-ocurrencia 10% · Sum 5% · Chi² 15% · MI 15% · Markov 15% · Bayes 10% · Monte Carlo 5%

---

## 🚀 Setup (una sola vez)

### 1. Crea el repositorio en GitHub
```bash
git clone https://github.com/TU_USUARIO/claude-l-nacional.git
cd claude-l-nacional
```

### 2. Configura los Secrets de GitHub
Ve a tu repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|--------|-------|
| `TELEGRAM_BOT_TOKEN` | Token de tu bot (obtenlo con @BotFather) |
| `TELEGRAM_CHAT_ID` | Tu Chat ID (obtenlo con @userinfobot) |

### 3. Activa GitHub Actions
Ve a tu repo → **Actions → Enable workflows**

### 4. Habilita permisos de escritura
Ve a **Settings → Actions → General → Workflow permissions** → selecciona **"Read and write permissions"**

### 5. Sube el código
```bash
git add .
git commit -m "🚀 CLAUDE L-NACIONAL v1.0"
git push origin main
```

---

## 📲 Cómo configurar Telegram

1. Abre Telegram → busca **@BotFather** → envía `/newbot`
2. Sigue las instrucciones → copia el **Bot Token**
3. Busca **@userinfobot** → envía `/start` → copia tu **ID**
4. Agrega ambos como Secrets en GitHub (paso 2 arriba)

---

## 🔄 Flujo de uso diario

```
⏰ 2:30 PM → GitHub Action corre automáticamente
             → Análisis con 9 métodos
             → Genera picks
             → Envía mensaje a Telegram
             → Guarda en data/picks_log.json (commit al repo)

👀 Ves el sorteo real en TV/web

📥 Vas a GitHub → Actions → "Ingresar Resultado Real" → Run workflow
   → Ingresas: Lotería, p1, p2, p3
   → Sistema verifica tu pick
   → Actualiza performance.json
   → Envía mensaje de verificación a Telegram
   → Commit automático al repo

⏰ 9:00 PM → Mismo proceso para Nacional Noche
```

---

## ▶️ Correr manualmente

### Generar picks ahora
GitHub → **Actions → "GANA MÁS — Picks Automáticos"** → **Run workflow**

### Ingresar resultado real
GitHub → **Actions → "Ingresar Resultado Real"** → **Run workflow** → llena los campos

---

## 📁 Estructura del repositorio

```
claude-l-nacional/
│
├── data/
│   ├── history.json        ← Historial completo de sorteos
│   ├── picks_log.json      ← Log de picks generados y verificados
│   └── performance.json    ← Estadísticas de performance
│
├── src/
│   ├── engine.py           ← Los 9 métodos de análisis + WMA
│   └── telegram_bot.py     ← Mensajes de Telegram
│
├── generate_picks.py       ← Script principal de picks
├── add_result.py           ← Script para ingresar resultados
├── seed_history.py         ← Inicializador de datos (correr 1 vez)
├── requirements.txt
│
└── .github/workflows/
    ├── gana_mas.yml        ← Automático 2:30 PM (18:30 UTC)
    ├── nacional_noche.yml  ← Automático 9:00 PM (01:00 UTC)
    └── add_result.yml      ← Manual desde Actions UI
```

---

## 📊 Estructura de los datos

### history.json
```json
{
  "history": [
    {
      "id": "r_20240430_143000",
      "date": "2024-04-30",
      "day_name": "Martes",
      "lottery": "Gana Más",
      "p1": "47",
      "p2": "23",
      "p3": "08"
    }
  ]
}
```

### picks_log.json
```json
{
  "picks": [
    {
      "id": "p_20240430_143000",
      "date": "2024-04-30",
      "lottery": "Gana Más",
      "p1": "47", "p2": "23", "p3": "08",
      "method": "Sistema",
      "status": "verified",
      "result": "1ra",
      "payout": 0
    }
  ]
}
```

---

## ⚠️ Disclaimer

Este sistema es exclusivamente para **análisis estadístico**.  
La lotería es un juego de azar — ningún método garantiza predicciones.  
Juega responsablemente con montos que puedas permitirte perder.

---

**CLAUDE L-NACIONAL v1.0** · Python + GitHub Actions · 9 métodos estadísticos
