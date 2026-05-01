// ─── CLAUDE L-NACIONAL | Telegram Utils ─────────────────────────────────────

const DAYS_ES = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado']
const LOTTERY_TIMES = { 'Gana Más': '2:30 PM', 'Nacional Noche': '9:00 PM' }

export async function sendTelegram(token, chatId, text) {
  const url = `https://api.telegram.org/bot${token}/sendMessage`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' }),
  })
  const data = await res.json()
  if (!data.ok) throw new Error(data.description || 'Error enviando mensaje')
  return data
}

export function buildPickMessage({ lottery, picks, analysis, performance, nextDate }) {
  const d       = nextDate ? new Date(nextDate + 'T12:00:00') : new Date()
  const dayName = DAYS_ES[d.getDay()]
  const dateStr = d.toLocaleDateString('es-DO', { day: '2-digit', month: 'short', year: 'numeric' })
  const time    = LOTTERY_TIMES[lottery] || ''

  const top = picks.slice(0, 3)
  const p1  = top[0]?.num ?? '??'
  const p2  = top[1]?.num ?? '??'
  const p3  = top[2]?.num ?? '??'

  const pales = [
    `${p1}-${p2}`, `${p1}-${p3}`, `${p2}-${p3}`
  ]

  const score       = top[0]?.compositeScore ?? 0
  const markovPct   = analysis?.markovConfidence ?? 0
  const miLevel     = analysis?.miLevel ?? 'N/A'
  const chiValid    = analysis?.chiValid ? '✅' : '⚠️'
  const overdueMax  = analysis?.overdueMax ?? 0
  const totalDraws  = analysis?.total ?? 0

  const hitRate     = performance?.hitRate   ?? 0
  const streak      = performance?.streak    ?? 0
  const roi         = performance?.roi       ?? 0
  const streakEmoji = streak > 0 ? '🔥' : streak < 0 ? '❄️' : '➖'

  return `🎯 <b>CLAUDE L-NACIONAL</b>
━━━━━━━━━━━━━━━━━━━━━
🎰 <b>${lottery.toUpperCase()}</b>
📅 ${dayName} ${dateStr} • ${time}
━━━━━━━━━━━━━━━━━━━━━
🔢 <b>PICKS PRINCIPALES</b>
━━━━━━━━━━━━━━━━━━━━━
🥇 1ra posición  →  <code>${p1}</code>
🥈 2da posición  →  <code>${p2}</code>
🥉 3ra posición  →  <code>${p3}</code>
━━━━━━━━━━━━━━━━━━━━━
📊 <b>ANÁLISIS DEL SISTEMA</b>
━━━━━━━━━━━━━━━━━━━━━
🔥 Score compuesto:  <b>${score}/100</b>
⏳ Overdue máx:      <b>${overdueMax} sorteos</b>
🔗 Markov match:     <b>${markovPct}%</b>
🧪 Chi² validado:    ${chiValid}
📈 MI correlación:   <b>${miLevel}</b>
📂 Historial usado:  <b>${totalDraws} sorteos</b>
━━━━━━━━━━━━━━━━━━━━━
💰 <b>PALÉS SUGERIDOS</b>
━━━━━━━━━━━━━━━━━━━━━
• ${pales[0]}   • ${pales[1]}   • ${pales[2]}
━━━━━━━━━━━━━━━━━━━━━
📉 <b>PERFORMANCE DEL SISTEMA</b>
━━━━━━━━━━━━━━━━━━━━━
Hit rate:      <b>${hitRate}%</b> (últimos 30)
Racha actual:  <b>${streak > 0 ? '+' : ''}${streak}</b> ${streakEmoji}
ROI estimado:  <b>${roi > 0 ? '+' : ''}${roi}%</b>
━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Solo para análisis estadístico</i>
🤖 <i>CLAUDE L-NACIONAL v1.0</i>`
}
