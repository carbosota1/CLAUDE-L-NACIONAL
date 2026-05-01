import { useState } from 'react'
import { PlusCircle, RefreshCw } from 'lucide-react'

const DAYS = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
const LOTTERIES = ['Gana Más', 'Nacional Noche']

function getDayName(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  return DAYS[d.getDay() === 0 ? 6 : d.getDay() - 1]
}

function NumInput({ label, value, onChange }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-mono text-gray-500">{label}</label>
      <input
        type="number" min="0" max="99"
        value={value}
        onChange={e => onChange(String(parseInt(e.target.value || '0')).padStart(2,'0'))}
        placeholder="00"
        className="w-full bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-3 py-3 font-mono text-2xl text-center text-white outline-none transition-colors"
      />
    </div>
  )
}

export default function AddResult({ addResult, settings, history }) {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm]   = useState({ date: today, lottery: settings.lottery, p1: '', p2: '', p3: '' })
  const [submitted, setSubmitted] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = () => {
    if (!form.p1 || !form.p2 || !form.p3) return
    const p1 = String(parseInt(form.p1)).padStart(2,'0')
    const p2 = String(parseInt(form.p2)).padStart(2,'0')
    const p3 = String(parseInt(form.p3)).padStart(2,'0')
    addResult({
      id:      `r_${Date.now()}`,
      date:    form.date,
      dayName: getDayName(form.date),
      lottery: form.lottery,
      p1, p2, p3,
    })
    setForm({ date: today, lottery: form.lottery, p1: '', p2: '', p3: '' })
    setSubmitted(true)
    setTimeout(() => setSubmitted(false), 2000)
  }

  // Recent results for this lottery
  const recent = history
    .filter(h => h.lottery === form.lottery)
    .slice(-10)
    .reverse()

  return (
    <div className="space-y-6 animate-slide-up">
      <h2 className="font-display text-2xl tracking-widest text-white">INGRESAR RESULTADO</h2>

      {/* Form */}
      <div className="bg-dark-800/60 border border-dark-600 rounded-xl p-5 space-y-4">

        {/* Lottery selector */}
        <div>
          <label className="text-xs font-mono text-gray-500 block mb-2">LOTERÍA</label>
          <div className="grid grid-cols-2 gap-2">
            {LOTTERIES.map(l => (
              <button
                key={l}
                onClick={() => set('lottery', l)}
                className={`py-2.5 px-4 rounded-lg font-body text-sm font-medium border transition-all ${
                  form.lottery === l
                    ? 'bg-gold-500/20 border-gold-500/50 text-gold-400'
                    : 'bg-dark-700 border-dark-500 text-gray-400 hover:text-white'
                }`}
              >{l}</button>
            ))}
          </div>
        </div>

        {/* Date */}
        <div>
          <label className="text-xs font-mono text-gray-500 block mb-2">FECHA</label>
          <input
            type="date"
            value={form.date}
            onChange={e => set('date', e.target.value)}
            className="w-full bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-3 py-2.5 font-mono text-white outline-none transition-colors"
          />
        </div>

        {/* Numbers */}
        <div className="grid grid-cols-3 gap-3">
          <NumInput label="1RA POSICIÓN" value={form.p1} onChange={v => set('p1', v)} />
          <NumInput label="2DA POSICIÓN" value={form.p2} onChange={v => set('p2', v)} />
          <NumInput label="3RA POSICIÓN" value={form.p3} onChange={v => set('p3', v)} />
        </div>

        <button
          onClick={handleSubmit}
          disabled={!form.p1 || !form.p2 || !form.p3}
          className={`w-full py-3.5 rounded-xl font-body font-bold text-base flex items-center justify-center gap-2 transition-all ${
            submitted
              ? 'bg-emerald-600 text-white'
              : 'bg-gold-500 hover:bg-gold-400 disabled:opacity-40 text-dark-900'
          }`}
        >
          {submitted
            ? <><RefreshCw size={16} className="animate-spin"/> Sistema actualizado</>
            : <><PlusCircle size={16}/> Guardar y Actualizar Sistema</>
          }
        </button>
      </div>

      {/* Recent results table */}
      <div>
        <h3 className="font-display text-lg tracking-widest text-white mb-3">
          ÚLTIMOS 10 — {form.lottery}
        </h3>
        <div className="space-y-2">
          {recent.length === 0 && (
            <p className="text-gray-600 font-mono text-sm text-center py-4">Sin resultados aún</p>
          )}
          {recent.map((r, i) => (
            <div key={r.id} className={`flex items-center justify-between px-4 py-2.5 rounded-lg border ${
              i === 0 ? 'bg-gold-500/5 border-gold-500/20' : 'bg-dark-800/40 border-dark-600/50'
            }`}>
              <div className="flex items-center gap-3">
                {i === 0 && <span className="text-xs font-mono text-gold-400">ÚLTIMO</span>}
                <span className="text-xs font-mono text-gray-500">{r.date}</span>
                <span className="text-xs font-mono text-gray-600">{r.dayName}</span>
              </div>
              <div className="flex gap-2">
                {[r.p1, r.p2, r.p3].map((n, j) => (
                  <span key={j} className={`font-mono font-bold px-2 py-0.5 rounded text-sm ${
                    j === 0 ? 'text-gold-400 bg-gold-500/10' : 'text-white bg-dark-700'
                  }`}>{n}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
