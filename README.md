# 🎯 CLAUDE L-NACIONAL

Sistema de análisis estadístico para **Gana Más** y **Nacional Noche** (República Dominicana).

## 🧠 Métodos de Análisis (9 + WMA)

| # | Método | Descripción |
|---|--------|-------------|
| 1 | Rating de Rentabilidad | Fórmula dominicana: 1ra=60pts, 2da=8pts, 3ra=4pts, ausente=-1pt |
| 2 | Overdue / Gap Analysis | Números con mayor "deuda estadística" |
| 3 | Co-ocurrencia | Qué números tienden a seguir al sorteo anterior |
| 4 | Sum Analysis | Filtra combinaciones por rango histórico de suma |
| 5 | Chi² | Valida si los patrones son estadísticamente reales |
| 6 | Mutual Information | Mide dependencia real entre sorteos consecutivos |
| 7 | Markov Chain | Matriz de transición 1-paso + 2-paso superpuesta |
| 8 | Inferencia Bayesiana | Sistema auto-aprendiente (Dirichlet-Multinomial) |
| 9 | Monte Carlo | Simulación de 5,000 sorteos virtuales |
| + | WMA | Capa transversal: sorteos recientes pesan más |

## 🚀 Setup Local

```bash
# 1. Clona el repositorio
git clone https://github.com/TU_USUARIO/claude-l-nacional.git
cd claude-l-nacional

# 2. Instala dependencias
npm install

# 3. Corre en modo desarrollo
npm run dev
```

## 🌐 Deploy a GitHub Pages

### Opción A — Automático (recomendado)
El repositorio incluye un workflow de GitHub Actions. Cada vez que hagas push a `main`, se despliega automáticamente.

1. Sube el código a GitHub
2. Ve a **Settings → Pages → Source** y selecciona `gh-pages` branch
3. ¡Listo! Tu app estará en `https://TU_USUARIO.github.io/claude-l-nacional/`

### Opción B — Manual
```bash
npm run deploy
```

> ⚠️ Si cambias el nombre del repositorio, actualiza `base` en `vite.config.js`

## 📲 Configurar Telegram

1. Abre Telegram → busca **@BotFather** → envía `/newbot`
2. Sigue las instrucciones y copia el **Bot Token**
3. Para obtener tu **Chat ID**, busca **@userinfobot** → envía `/start`
4. En la app, ve a **Config** e ingresa ambos valores
5. Prueba con el botón **"Enviar mensaje de prueba"**

## 📋 Flujo de Uso

```
1. Abre la app
2. Dashboard → genera picks para el próximo sorteo
3. Envía los picks a Telegram
4. Espera el sorteo
5. Ve a "Resultado" → ingresa el resultado real
6. El sistema se actualiza automáticamente
7. Ve a "Picks Log" → verifica tu pick
8. Ve a "Performance" → monitorea cómo va el sistema
```

## 💾 Backup de Datos

El historial se guarda en `localStorage` del navegador. Para no perderlo:

- **Config → Exportar backup (JSON)** → guarda el archivo
- En otro dispositivo → **Config → Importar backup (JSON)**

## ⚠️ Disclaimer

Este sistema es exclusivamente para **análisis estadístico**. La lotería es un juego de azar. Ningún método garantiza predicciones. Juega responsablemente con montos que puedas permitirte perder.

---

**CLAUDE L-NACIONAL v1.0** · Desarrollado con React + Vite
