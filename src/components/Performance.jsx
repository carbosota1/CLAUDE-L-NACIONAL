import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, CartesianGrid } from 'recharts'

const RESULT_COLORS = {
  tripleta: '#10b981',
  palé:     '#a855f7',
  '1ra':    '#f59e0b',
  '2da':    '#3b82f6',
  '3ra':    '#06b6d4',
  miss:     '#374151',
}

export default function Performance({ picks, perfStats }) {
  const verified = picks.filter(p => p.status === 'verified')

  if (verified.length === 0) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <p className="text-gray-500 font-mono text-sm text-center">Aún no hay picks verificados.</p>
      <p className="text-gray-700 font-mono text-xs text-center">Verifica tus picks en Picks Log para ver el performance.</p>
    </div>
  )

  // Result distribution
  const dist = {}
  verified.forEach(p => { dist[p.result] = (dist[p.result] || 0) + 1 })
  const distData = Object.entries(dist).map(([name, value]) => ({ name: name.toUpperCase(), value, color: RESULT_COLORS[name] }))

  // ROI over time (running)
  const roiData = []
  let cumInvested = 0, cumWon = 0
  verified.forEach((p, i) => {
    cumInvested += parseFloat(p.amount) || 0
    cumWon      += parseFloat(p.payout) || 0
    if ((i + 1) % 3 === 0 || i === verified.length - 1) {
      roiData.push({
        sorteo: i + 1,
        roi: cumInvested > 0 ? Math.round(((cumWon - cumInvested) / cumInvested) * 100) : 0,
      })
    }
  })

  // Hit rate by method
  const byMethod = {}
  verified.forEach(p => {
    if (!byMethod[p.method]) byMethod[p.method] = { hits: 0, total: 0 }
    byMethod[p.method].total++
    if (p.result !== 'miss') byMethod[p.method].hits++
  })
  const methodData = Object.entries(byMethod).map(([name, s]) => ({
    name,
    hitRate: Math.round((s.hits / s.total) * 100),
    total: s.total,
  }))

  // Last 20 results timeline
  const timeline = verified.slice(-20).map((p, i) => ({
    idx: i + 1,
    result: p.result,
    color: RESULT_COLORS[p.result] || '#374151',
    win: p.result !== 'miss' ? 1 : 0,
  }))

  return (
    <div className="space-y-6 animate-slide-up">
      <h2 className="font-display text-2xl tracking-widest text-white">PERFORMANCE</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-4 text-center">
          <p className="text-3xl font-mono font-bold text-gold-400">{perfStats?.hitRate ?? 0}%</p>
          <p className="text-xs font-mono text-gray-500 mt-1">Hit Rate</p>
          <p className="text-xs font-mono text-gray-700">últimos 30</p>
        </div>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-4 text-center">
          <p className={`text-3xl font-mono font-bold ${(perfStats?.streak ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {(perfStats?.streak ?? 0) > 0 ? '+' : ''}{perfStats?.streak ?? 0}
          </p>
          <p className="text-xs font-mono text-gray-500 mt-1">Racha</p>
          <p className="text-xs font-mono text-gray-700">{(perfStats?.streak ?? 0) >= 0 ? '🔥' : '❄️'}</p>
        </div>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-4 text-center">
          <p className={`text-3xl font-mono font-bold ${(perfStats?.roi ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {(perfStats?.roi ?? 0) > 0 ? '+' : ''}{perfStats?.roi ?? 0}%
          </p>
          <p className="text-xs font-mono text-gray-500 mt-1">ROI</p>
          <p className="text-xs font-mono text-gray-700">acumulado</p>
        </div>
        <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-4 text-center">
          <p className="text-3xl font-mono font-bold text-white">{verified.length}</p>
          <p className="text-xs font-mono text-gray-500 mt-1">Total</p>
          <p className="text-xs font-mono text-gray-700">picks jugados</p>
        </div>
      </div>

      {/* ROI Chart */}
      {roiData.length > 1 && (
        <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-4">
          <h3 className="font-display text-lg tracking-widest text-white mb-4">ROI ACUMULADO</h3>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={roiData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2a40" />
              <XAxis dataKey="sorteo" stroke="#374151" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <YAxis stroke="#374151" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }}
                tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ background: '#0e1420', border: '1px solid #243350', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }}
                formatter={v => [`${v}%`, 'ROI']}
              />
              <Line type="monotone" dataKey="roi" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Result Distribution */}
      {distData.length > 0 && (
        <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-4">
          <h3 className="font-display text-lg tracking-widest text-white mb-4">DISTRIBUCIÓN DE RESULTADOS</h3>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={distData}>
              <XAxis dataKey="name" stroke="#374151" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <YAxis stroke="#374151" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <Tooltip
                contentStyle={{ background: '#0e1420', border: '1px solid #243350', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }}
              />
              <Bar dataKey="value" radius={[4,4,0,0]}>
                {distData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* By Method */}
      {methodData.length > 0 && (
        <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-4">
          <h3 className="font-display text-lg tracking-widest text-white mb-3">HIT RATE POR MÉTODO</h3>
          <div className="space-y-3">
            {methodData.map(m => (
              <div key={m.name} className="flex items-center gap-3">
                <span className="text-xs font-mono text-gray-400 w-16 shrink-0">{m.name}</span>
                <div className="flex-1 bg-dark-600 rounded-full h-2">
                  <div className="bg-gold-500 h-2 rounded-full transition-all" style={{ width: `${m.hitRate}%` }} />
                </div>
                <span className="text-xs font-mono text-gray-400 w-16 text-right">{m.hitRate}% ({m.total})</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Timeline dots */}
      <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-4">
        <h3 className="font-display text-lg tracking-widest text-white mb-3">ÚLTIMOS 20 PICKS</h3>
        <div className="flex flex-wrap gap-2">
          {timeline.map((t, i) => (
            <div key={i} className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono font-bold"
              style={{ background: t.color + '30', border: `1px solid ${t.color}60`, color: t.color }}>
              {t.result === 'miss' ? '✗' : t.result === 'tripleta' ? 'T' : t.result === 'palé' ? 'P' : t.result}
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-3 mt-3">
          {Object.entries(RESULT_COLORS).map(([r, c]) => (
            <span key={r} className="flex items-center gap-1 text-xs font-mono text-gray-500">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: c }}/>
              {r}
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}
