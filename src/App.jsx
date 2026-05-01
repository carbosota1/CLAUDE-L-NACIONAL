import { useState, useEffect, useCallback } from 'react'
import { load, save, KEYS } from './utils/storage.js'
import { runFullAnalysis, calcPerformance } from './engine/analysis.js'
import Dashboard from './components/Dashboard.jsx'
import AddResult from './components/AddResult.jsx'
import PicksLog from './components/PicksLog.jsx'
import Performance from './components/Performance.jsx'
import Settings from './components/Settings.jsx'
import { LayoutDashboard, PlusCircle, ListChecks, BarChart3, Settings2 } from 'lucide-react'
import './index.css'

const TABS = [
  { id: 'dashboard',   label: 'Dashboard',    Icon: LayoutDashboard },
  { id: 'add',         label: 'Resultado',    Icon: PlusCircle },
  { id: 'picks',       label: 'Picks Log',    Icon: ListChecks },
  { id: 'performance', label: 'Performance',  Icon: BarChart3 },
  { id: 'settings',    label: 'Config',       Icon: Settings2 },
]

const SEED_DRAWS = (() => {
  const days = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
  const lots  = ['Gana Más', 'Nacional Noche']
  const arr   = []
  const now   = new Date()
  const rng   = (seed) => { let x = Math.sin(seed + 42) * 10000; return Math.abs(x - Math.floor(x)) }
  for (let i = 89; i >= 0; i--) {
    const d = new Date(now); d.setDate(d.getDate() - i)
    const dayName = days[d.getDay() === 0 ? 6 : d.getDay() - 1]
    for (const lot of lots) {
      const s = i * 7 + (lot === 'Gana Más' ? 1 : 3)
      arr.push({
        id: `seed_${i}_${lot.replace(' ','')}`,
        date: d.toISOString().split('T')[0],
        dayName,
        lottery: lot,
        p1: String(Math.floor(rng(s) * 100)).padStart(2,'0'),
        p2: String(Math.floor(rng(s+1) * 100)).padStart(2,'0'),
        p3: String(Math.floor(rng(s+2) * 100)).padStart(2,'0'),
      })
    }
  }
  return arr
})()

export default function App() {
  const [tab,         setTab]         = useState('dashboard')
  const [history,     setHistory]     = useState(() => load(KEYS.HISTORY) ?? SEED_DRAWS)
  const [picks,       setPicks]       = useState(() => load(KEYS.PICKS)   ?? [])
  const [settings,    setSettings]    = useState(() => load(KEYS.SETTINGS) ?? { botToken: '', chatId: '', lottery: 'Gana Más' })
  const [analysis,    setAnalysis]    = useState(null)
  const [perfStats,   setPerfStats]   = useState(null)
  const [toast,       setToast]       = useState(null)

  // Persist state
  useEffect(() => { save(KEYS.HISTORY, history) },  [history])
  useEffect(() => { save(KEYS.PICKS,   picks)   },  [picks])
  useEffect(() => { save(KEYS.SETTINGS,settings) }, [settings])

  // Re-run analysis whenever history or selected lottery changes
  useEffect(() => {
    const filtered = history.filter(h => h.lottery === settings.lottery)
    const result   = runFullAnalysis(filtered)
    setAnalysis(result)
  }, [history, settings.lottery])

  // Re-calc performance whenever picks change
  useEffect(() => {
    const lotteryPicks = picks.filter(p => p.lottery === settings.lottery)
    setPerfStats(calcPerformance(lotteryPicks))
  }, [picks, settings.lottery])

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }, [])

  const addResult = useCallback((entry) => {
    setHistory(prev => [...prev, entry])
    showToast(`✅ Resultado guardado — ${entry.lottery}`)
  }, [showToast])

  const addPick = useCallback((pick) => {
    setPicks(prev => [pick, ...prev])
    showToast(`🎯 Pick registrado`)
  }, [showToast])

  const verifyPick = useCallback((pickId, realResult) => {
    setPicks(prev => prev.map(p => {
      if (p.id !== pickId) return p
      const pickNums  = [p.p1, p.p2, p.p3]
      const realNums  = [realResult.p1.padStart(2,'0'), realResult.p2.padStart(2,'0'), realResult.p3.padStart(2,'0')]
      const anyMatch  = pickNums.filter(n => realNums.includes(n))
      const posMatch  = pickNums.filter((n,i) => n === realNums[i])
      let result = 'miss', payout = 0
      const amt = parseFloat(p.amount) || 0
      if      (anyMatch.length === 3)       { result = 'tripleta'; payout = amt * 20000 }
      else if (anyMatch.length >= 2)        { result = 'palé';     payout = amt * 1000  }
      else if (pickNums[0] === realNums[0]) { result = '1ra';      payout = amt * 60    }
      else if (pickNums[1] === realNums[1]) { result = '2da';      payout = amt * 8     }
      else if (pickNums[2] === realNums[2]) { result = '3ra';      payout = amt * 5     }
      return { ...p, status: 'verified', result, payout, realP1: realResult.p1, realP2: realResult.p2, realP3: realResult.p3 }
    }))
    showToast('✅ Pick verificado')
  }, [showToast])

  const props = { history, picks, settings, setSettings, analysis, perfStats, addResult, addPick, verifyPick, showToast }

  return (
    <div className="min-h-screen bg-dark-900 text-white font-body">
      {/* Header */}
      <header className="border-b border-dark-600 bg-dark-800/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-gold-400 to-gold-600 rounded-sm flex items-center justify-center animate-glow">
              <span className="font-display text-dark-900 text-sm">CL</span>
            </div>
            <div>
              <h1 className="font-display text-xl tracking-widest text-gold-400 leading-none">
                CLAUDE L-NACIONAL
              </h1>
              <p className="text-xs text-dark-500 font-mono tracking-wider mt-0.5">
                {settings.lottery} · SISTEMA DE ANÁLISIS
              </p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-1">
            {analysis && (
              <span className="text-xs font-mono text-dark-500 bg-dark-700 px-2 py-1 rounded">
                {analysis.total} sorteos
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Nav */}
      <nav className="border-b border-dark-700 bg-dark-800/50">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex overflow-x-auto scrollbar-hide">
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm font-body whitespace-nowrap border-b-2 transition-all ${
                  tab === id
                    ? 'border-gold-400 text-gold-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-6 animate-fade-in">
        {tab === 'dashboard'   && <Dashboard   {...props} />}
        {tab === 'add'         && <AddResult   {...props} />}
        {tab === 'picks'       && <PicksLog    {...props} />}
        {tab === 'performance' && <Performance {...props} />}
        {tab === 'settings'    && <Settings    {...props} />}
      </main>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-lg text-sm font-body font-medium shadow-2xl animate-slide-up flex items-center gap-2 ${
          toast.type === 'error'
            ? 'bg-red-900/90 border border-red-700 text-red-200'
            : 'bg-dark-700/95 border border-gold-500/40 text-gold-300'
        }`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
