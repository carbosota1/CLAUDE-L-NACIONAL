import { useState, useRef } from 'react'
import { Send, Download, Upload, Trash2, Eye, EyeOff, CheckCircle } from 'lucide-react'
import { exportAllData, importAllData } from '../utils/storage.js'
import { sendTelegram, buildPickMessage } from '../utils/telegram.js'

const LOTTERIES = ['Gana Más', 'Nacional Noche']

export default function Settings({ settings, setSettings, showToast, history, picks, analysis, perfStats }) {
  const [showToken, setShowToken] = useState(false)
  const [testing,   setTesting]   = useState(false)
  const fileRef = useRef()

  const set = (k, v) => setSettings(s => ({ ...s, [k]: v }))

  const handleTest = async () => {
    if (!settings.botToken || !settings.chatId) {
      showToast('⚠️ Completa Bot Token y Chat ID', 'error'); return
    }
    setTesting(true)
    try {
      const top3 = analysis?.picks?.slice(0,3) ?? []
      const msg  = buildPickMessage({
        lottery:     settings.lottery,
        picks:       top3,
        analysis:    analysis   || {},
        performance: perfStats  || {},
        nextDate:    new Date().toISOString().split('T')[0],
      })
      await sendTelegram(settings.botToken, settings.chatId, msg)
      showToast('✅ Mensaje de prueba enviado')
    } catch(e) { showToast(`❌ ${e.message}`, 'error') }
    setTesting(false)
  }

  const handleImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await importAllData(file)
      showToast('✅ Datos importados — recarga la página')
      setTimeout(() => window.location.reload(), 1500)
    } catch { showToast('❌ Archivo inválido', 'error') }
  }

  const handleClear = () => {
    if (!window.confirm('¿Borrar TODO el historial y picks? Esta acción no se puede deshacer.')) return
    Object.values({ h:'cln_history', p:'cln_picks', perf:'cln_performance' })
      .forEach(k => localStorage.removeItem(k))
    showToast('🗑️ Datos borrados — recargando…')
    setTimeout(() => window.location.reload(), 1500)
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <h2 className="font-display text-2xl tracking-widest text-white">CONFIGURACIÓN</h2>

      {/* Lottery selector */}
      <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-5 space-y-4">
        <h3 className="font-display text-lg tracking-widest text-gold-400">LOTERÍA ACTIVA</h3>
        <div className="grid grid-cols-2 gap-2">
          {LOTTERIES.map(l => (
            <button key={l} onClick={() => set('lottery', l)}
              className={`py-3 px-4 rounded-lg font-body text-sm font-medium border transition-all ${
                settings.lottery === l
                  ? 'bg-gold-500/20 border-gold-500/50 text-gold-400'
                  : 'bg-dark-700 border-dark-500 text-gray-400 hover:text-white'
              }`}
            >{l}</button>
          ))}
        </div>
        <p className="text-xs font-mono text-gray-600">
          El análisis y los picks se generan para la lotería seleccionada.
        </p>
      </section>

      {/* Telegram config */}
      <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-5 space-y-4">
        <h3 className="font-display text-lg tracking-widest text-gold-400">TELEGRAM</h3>

        <div className="bg-dark-700/50 border border-dark-500 rounded-lg p-3 space-y-1">
          <p className="text-xs font-mono text-gray-400 font-bold">¿Cómo obtener el Bot Token?</p>
          <ol className="text-xs font-mono text-gray-500 space-y-0.5 list-decimal list-inside">
            <li>Abre Telegram y busca <span className="text-gold-400">@BotFather</span></li>
            <li>Envía <span className="text-gold-400">/newbot</span> y sigue las instrucciones</li>
            <li>Copia el token que te da y pégalo abajo</li>
            <li>Para el Chat ID, busca <span className="text-gold-400">@userinfobot</span> y envíale /start</li>
          </ol>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs font-mono text-gray-500 block mb-1.5">BOT TOKEN</label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={settings.botToken}
                onChange={e => set('botToken', e.target.value)}
                placeholder="123456789:ABCdef..."
                className="w-full bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-3 py-2.5 font-mono text-sm text-white outline-none pr-10 transition-colors"
              />
              <button onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                {showToken ? <EyeOff size={15}/> : <Eye size={15}/>}
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs font-mono text-gray-500 block mb-1.5">CHAT ID</label>
            <input
              type="text"
              value={settings.chatId}
              onChange={e => set('chatId', e.target.value)}
              placeholder="-100123456789 o tu user ID"
              className="w-full bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-3 py-2.5 font-mono text-sm text-white outline-none transition-colors"
            />
          </div>

          <button
            onClick={handleTest}
            disabled={testing || !settings.botToken || !settings.chatId}
            className="w-full flex items-center justify-center gap-2 bg-dark-700 hover:bg-dark-600 disabled:opacity-40 border border-dark-500 hover:border-gold-500/40 text-white py-2.5 rounded-lg font-body text-sm font-medium transition-all"
          >
            <Send size={14} className="text-gold-400"/>
            {testing ? 'Enviando prueba…' : 'Enviar mensaje de prueba'}
          </button>
        </div>
      </section>

      {/* Data management */}
      <section className="bg-dark-800/60 border border-dark-600 rounded-xl p-5 space-y-3">
        <h3 className="font-display text-lg tracking-widest text-gold-400">DATOS</h3>

        <div className="grid grid-cols-2 gap-2 text-center text-xs font-mono text-gray-500 bg-dark-700/40 rounded-lg p-3">
          <div>
            <p className="text-2xl font-bold text-white font-mono">{history.length}</p>
            <p>sorteos en historial</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-white font-mono">{picks.length}</p>
            <p>picks registrados</p>
          </div>
        </div>

        <button
          onClick={exportAllData}
          className="w-full flex items-center justify-center gap-2 bg-dark-700 hover:bg-dark-600 border border-dark-500 text-white py-2.5 rounded-lg font-body text-sm font-medium transition-all"
        >
          <Download size={14} className="text-gold-400"/>
          Exportar backup (JSON)
        </button>

        <button
          onClick={() => fileRef.current?.click()}
          className="w-full flex items-center justify-center gap-2 bg-dark-700 hover:bg-dark-600 border border-dark-500 text-white py-2.5 rounded-lg font-body text-sm font-medium transition-all"
        >
          <Upload size={14} className="text-blue-400"/>
          Importar backup (JSON)
        </button>
        <input ref={fileRef} type="file" accept=".json" onChange={handleImport} className="hidden"/>

        <button
          onClick={handleClear}
          className="w-full flex items-center justify-center gap-2 bg-red-900/20 hover:bg-red-900/40 border border-red-800/40 text-red-400 py-2.5 rounded-lg font-body text-sm font-medium transition-all"
        >
          <Trash2 size={14}/>
          Borrar todos los datos
        </button>
      </section>

      {/* Version */}
      <div className="text-center py-4 space-y-1">
        <p className="font-display text-2xl tracking-widest text-gold-400/30">CLAUDE L-NACIONAL</p>
        <p className="text-xs font-mono text-gray-700">v1.0.0 · 9 métodos estadísticos · WMA transversal</p>
        <p className="text-xs font-mono text-gray-800">Solo para análisis estadístico. Juega responsablemente.</p>
      </div>
    </div>
  )
}
