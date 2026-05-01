import { useState } from 'react'
import { buildPickMessage, sendTelegram } from '../utils/telegram.js'
import { TrendingUp, TrendingDown, Clock, Send, Zap, Activity, ChevronRight } from 'lucide-react'

const MEDAL = ['🥇','🥈','🥉','4️⃣','5️⃣']

function NumBadge({ num, label, score, highlight }) {
  return (
    <div className={`flex flex-col items-center gap-1 p-3 rounded-lg border ${
      highlight
        ? 'bg-gold-500/10 border-gold-500/40'
        : 'bg-dark-700/50 border-dark-600'
    }`}>
      {label && <span className="text-xs font-mono text-gray-500">{label}</span>}
      <span className={`font-mono text-3xl font-bold ${highlight ? 'text-gold-400' : 'text-white'}`}>{num}</span>
      {score !== undefined && (
        <span className="text-xs font-mono text-gray-500">{score}/100</span>
      )}
    </div>
  )
}

function MethodBar({ label, value, color = 'bg-gold-500' }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-mono text-gray-400 w-28 shrink-0">{label}</span>
      <div className="flex-1 bg-dark-600 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${Math.min(value,100)}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-500 w-8 text-right">{value}</span>
    </div>
  )
}

export default function Dashboard({ analysis, perfStats, settings, showToast, addPick, picks }) {
  const [sending, setSending] = useState(false)

  if (!analysis) return (
    <div className="flex items-center justify-center h-64">
      <p className="text-gray-500 font-mono text-sm">Cargando análisis…</p>
    </div>
  )

  const top5   = analysis.picks.slice(0, 5)
  const top3   = top5.slice(0, 3)

  const handleGeneratePick = () => {
    const pick = {
      id:        `p_${Date.now()}`,
      date:      new Date().toISOString().split('T')[0],
      lottery:   settings.lottery,
      p1:        top3[0]?.num ?? '??',
      p2:        top3[1]?.num ?? '??',
      p3:        top3[2]?.num ?? '??',
      amount:    '',
      method:    'Sistema',
      status:    'pending',
      score:     top3[0]?.compositeScore ?? 0,
    }
    addPick(pick)
  }

  const handleSendTelegram = async () => {
    if (!settings.botToken || !settings.chatId) {
      showToast('⚠️ Configura tu Bot Token y Chat ID en Config', 'error')
      return
    }
    setSending(true)
    try {
      const msg = buildPickMessage({
        lottery:     settings.lottery,
        picks:       top3,
        analysis,
        performance: perfStats,
        nextDate:    new Date().toISOString().split('T')[0],
      })
      await sendTelegram(settings.botToken, settings.chatId, msg)
      showToast('✅ Mensaje enviado a Telegram')
    } catch (e) {
      showToast(`❌ Error: ${e.message}`, 'error')
    }
    setSending(false)
  }

  return (
    <div className="space-y-6 animate-slide-up">

      {/* Lottery selector badge */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono bg-gold-500/20 text-gold-400 border border-gold-500/30 px-3 py-1 rounded-full">
          {settings.lottery}
        </span>
        <span className="text-xs font-mono text-gray-600">{analysis.total} sorteos analizados</span>
      </div>

      {/* TOP PICKS */}
      <section>
        <h2 className="font-display text-2xl tracking-widest text-white mb-4">
          PICKS DEL SISTEMA
        </h2>
        <div className="grid grid-cols-3 gap-3 mb-4">
          {top3.map((p, i) => (
            <NumBadge key={p.num} num={p.num} label={MEDAL[i]} score={p.compositeScore} highlight={i === 0} />
          ))}
        </div>

        {/* Extended top 5 */}
        <div className="grid grid-cols-2 gap-2">
          {top5.slice(3).map((p, i) => (
            <div key={p.num} className="flex items-center justify-between bg-dark-700/30 border border-dark-600 rounded-lg px-3 py-2">
              <span className="text-xs text-gray-500 font-mono">{MEDAL[i+3]}</span>
              <span className="font-mono font-bold text-lg text-white">{p.num}</span>
              <span className="text-xs font-mono text-gray-500">{p.compositeScore}/100</span>
            </div>
          ))}
        </div>
      </section>

      {/* PALÉS */}
      <section>
        <h2 className="font-display text-xl tracking-widest text-white mb-3">PALÉS SUGERIDOS</h2>
        <div className="grid grid-cols-3 gap-2">
          {[
            [top3[0]?.num, top3[1]?.num],
            [top3[0]?.num, top3[2]?.num],
            [top3[1]?.num, top3[2]?.num],
          ].map(([a, b], i) => (
            <div key={i} className="bg-dark-700/40 border border-dark-600 rounded-lg p-2 text-center">
              <span className="font-mono text-gold-400 font-bold">{a} — {b}</span>
            </div>
          ))}
        </div>
      </section>

      {/* METHOD SCORES for top pick */}
      <section>
        <h2 className="font-display text-xl tracking-widest text-white mb-3">ANÁLISIS DEL PICK #1</h2>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-4 space-y-2.5">
          <MethodBar label="Rating RD"     value={top3[0]?.ratingScore    ?? 0} />
          <MethodBar label="Overdue"       value={Math.min(top3[0]?.overdueGap*3 ?? 0, 100)} color="bg-blue-500" />
          <MethodBar label="Markov"        value={top3[0]?.markovScore    ?? 0} color="bg-purple-500" />
          <MethodBar label="Bayesiano"     value={Math.round((top3[0]?.bayesProb??0)*10)} color="bg-cyan-500" />
          <MethodBar label="Chi²"          value={Math.min(Math.round(top3[0]?.chiScore??0)*5,100)} color="bg-emerald-500" />
        </div>
      </section>

      {/* SYSTEM INDICATORS */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-3">
          <p className="text-xs font-mono text-gray-500 mb-1">Chi² Válido</p>
          <p className="text-lg font-mono font-bold">{analysis.chiValid ? '✅ Sí' : '⚠️ No'}</p>
        </div>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-3">
          <p className="text-xs font-mono text-gray-500 mb-1">MI Level</p>
          <p className="text-lg font-mono font-bold text-gold-400">{analysis.miLevel}</p>
        </div>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-3">
          <p className="text-xs font-mono text-gray-500 mb-1">Markov %</p>
          <p className="text-lg font-mono font-bold text-purple-400">{analysis.markovConfidence}%</p>
        </div>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-3">
          <p className="text-xs font-mono text-gray-500 mb-1">Overdue Máx</p>
          <p className="text-lg font-mono font-bold text-blue-400">{analysis.overdueMax}</p>
        </div>
      </section>

      {/* HOT / COLD */}
      <div className="grid grid-cols-2 gap-4">
        <section>
          <h2 className="font-display text-lg tracking-widest text-red-400 mb-2 flex items-center gap-2">
            <TrendingUp size={16}/> HOT
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {analysis.hot.map(({ num, count }) => (
              <span key={num} className="font-mono text-sm bg-red-900/30 border border-red-800/40 text-red-300 px-2 py-0.5 rounded">
                {num} <span className="text-xs text-red-600">×{count}</span>
              </span>
            ))}
          </div>
        </section>
        <section>
          <h2 className="font-display text-lg tracking-widest text-blue-400 mb-2 flex items-center gap-2">
            <TrendingDown size={16}/> COLD
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {analysis.cold.map(({ num, count }) => (
              <span key={num} className="font-mono text-sm bg-blue-900/30 border border-blue-800/40 text-blue-300 px-2 py-0.5 rounded">
                {num} <span className="text-xs text-blue-600">×{count}</span>
              </span>
            ))}
          </div>
        </section>
      </div>

      {/* OVERDUE */}
      <section>
        <h2 className="font-display text-lg tracking-widest text-amber-400 mb-2 flex items-center gap-2">
          <Clock size={16}/> OVERDUE (sin aparecer)
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {analysis.overdueTop.map(({ num, gap }) => (
            <span key={num} className="font-mono text-sm bg-amber-900/20 border border-amber-800/30 text-amber-300 px-2 py-0.5 rounded">
              {num} <span className="text-xs text-amber-600">{gap}s</span>
            </span>
          ))}
        </div>
      </section>

      {/* PERFORMANCE QUICK */}
      {perfStats && (
        <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-4">
          <h2 className="font-display text-lg tracking-widest text-white mb-3 flex items-center gap-2">
            <Activity size={16} className="text-gold-400"/> PERFORMANCE
          </h2>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-2xl font-mono font-bold text-gold-400">{perfStats.hitRate}%</p>
              <p className="text-xs font-mono text-gray-500">Hit Rate</p>
            </div>
            <div>
              <p className={`text-2xl font-mono font-bold ${perfStats.streak >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {perfStats.streak > 0 ? '+' : ''}{perfStats.streak}
              </p>
              <p className="text-xs font-mono text-gray-500">Racha</p>
            </div>
            <div>
              <p className={`text-2xl font-mono font-bold ${perfStats.roi >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {perfStats.roi > 0 ? '+' : ''}{perfStats.roi}%
              </p>
              <p className="text-xs font-mono text-gray-500">ROI</p>
            </div>
          </div>
        </section>
      )}

      {/* ACTIONS */}
      <div className="grid grid-cols-2 gap-3 pb-6">
        <button
          onClick={handleGeneratePick}
          className="flex items-center justify-center gap-2 bg-dark-700 hover:bg-dark-600 border border-dark-500 hover:border-gold-500/40 text-white px-4 py-3 rounded-xl font-body font-medium transition-all"
        >
          <Zap size={16} className="text-gold-400"/>
          Guardar Pick
        </button>
        <button
          onClick={handleSendTelegram}
          disabled={sending}
          className="flex items-center justify-center gap-2 bg-gold-500 hover:bg-gold-400 disabled:opacity-50 text-dark-900 px-4 py-3 rounded-xl font-body font-bold transition-all"
        >
          <Send size={16}/>
          {sending ? 'Enviando…' : 'Telegram'}
        </button>
      </div>
    </div>
  )
}
