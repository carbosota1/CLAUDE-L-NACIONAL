import { useState } from 'react'
import { CheckCircle, Clock, XCircle, Plus, Send } from 'lucide-react'
import { buildPickMessage, sendTelegram } from '../utils/telegram.js'

const RESULT_STYLES = {
  miss:     'text-red-400   bg-red-900/20   border-red-800/30',
  '1ra':    'text-gold-400  bg-gold-500/10  border-gold-500/30',
  '2da':    'text-blue-400  bg-blue-900/20  border-blue-800/30',
  '3ra':    'text-cyan-400  bg-cyan-900/20  border-cyan-800/30',
  'palé':   'text-purple-400 bg-purple-900/20 border-purple-800/30',
  tripleta: 'text-emerald-400 bg-emerald-900/20 border-emerald-800/30',
}

const LOTTERIES = ['Gana Más', 'Nacional Noche']

export default function PicksLog({ picks, addPick, verifyPick, settings, analysis, perfStats, showToast }) {
  const [showAdd,    setShowAdd]    = useState(false)
  const [verifying,  setVerifying]  = useState(null) // pick id being verified
  const [realResult, setRealResult] = useState({ p1:'', p2:'', p3:'' })
  const [newPick,    setNewPick]    = useState({ lottery: settings.lottery, p1:'', p2:'', p3:'', amount:'' })
  const [sending,    setSending]    = useState(null)

  const handleAddManual = () => {
    if (!newPick.p1 || !newPick.p2 || !newPick.p3) return
    addPick({
      id:      `p_${Date.now()}`,
      date:    new Date().toISOString().split('T')[0],
      lottery: newPick.lottery,
      p1:      newPick.p1.padStart(2,'0'),
      p2:      newPick.p2.padStart(2,'0'),
      p3:      newPick.p3.padStart(2,'0'),
      amount:  newPick.amount,
      method:  'Manual',
      status:  'pending',
    })
    setNewPick({ lottery: settings.lottery, p1:'', p2:'', p3:'', amount:'' })
    setShowAdd(false)
  }

  const handleVerify = () => {
    if (!realResult.p1 || !realResult.p2 || !realResult.p3) return
    verifyPick(verifying, realResult)
    setVerifying(null)
    setRealResult({ p1:'', p2:'', p3:'' })
  }

  const handleResend = async (pick) => {
    if (!settings.botToken || !settings.chatId) {
      showToast('⚠️ Configura Telegram en Config', 'error'); return
    }
    setSending(pick.id)
    try {
      const msg = buildPickMessage({
        lottery:     pick.lottery,
        picks:       [{ num: pick.p1, compositeScore: pick.score || 0 }, { num: pick.p2 }, { num: pick.p3 }],
        analysis:    analysis || {},
        performance: perfStats || {},
        nextDate:    pick.date,
      })
      await sendTelegram(settings.botToken, settings.chatId, msg)
      showToast('✅ Pick re-enviado a Telegram')
    } catch(e) { showToast(`❌ ${e.message}`, 'error') }
    setSending(null)
  }

  const pending  = picks.filter(p => p.status === 'pending')
  const verified = picks.filter(p => p.status === 'verified')

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-2xl tracking-widest text-white">PICKS LOG</h2>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-1.5 bg-gold-500 hover:bg-gold-400 text-dark-900 px-3 py-2 rounded-lg text-sm font-bold transition-all"
        >
          <Plus size={15}/> Manual
        </button>
      </div>

      {/* Manual pick form */}
      {showAdd && (
        <div className="bg-dark-800/60 border border-gold-500/20 rounded-xl p-4 space-y-3 animate-slide-up">
          <h3 className="font-display text-lg tracking-widest text-gold-400">NUEVO PICK MANUAL</h3>
          <div className="grid grid-cols-2 gap-2">
            {LOTTERIES.map(l => (
              <button key={l} onClick={() => setNewPick(p=>({...p,lottery:l}))}
                className={`py-2 rounded-lg text-sm border transition-all ${newPick.lottery===l ? 'border-gold-500/50 text-gold-400 bg-gold-500/10' : 'border-dark-500 text-gray-400 bg-dark-700'}`}
              >{l}</button>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-2">
            {['p1','p2','p3'].map((k,i) => (
              <input key={k} type="number" min="0" max="99" placeholder={`${['1ra','2da','3ra'][i]}`}
                value={newPick[k]}
                onChange={e => setNewPick(p=>({...p,[k]:e.target.value}))}
                className="bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-2 py-2.5 font-mono text-center text-white outline-none text-lg"
              />
            ))}
            <input type="number" placeholder="RD$" value={newPick.amount}
              onChange={e => setNewPick(p=>({...p,amount:e.target.value}))}
              className="bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-2 py-2.5 font-mono text-center text-white outline-none"
            />
          </div>
          <button onClick={handleAddManual} className="w-full bg-gold-500 hover:bg-gold-400 text-dark-900 py-2.5 rounded-lg font-bold text-sm transition-all">
            Guardar Pick
          </button>
        </div>
      )}

      {/* Verify modal */}
      {verifying && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-800 border border-gold-500/30 rounded-2xl p-6 w-full max-w-sm space-y-4 animate-slide-up">
            <h3 className="font-display text-xl tracking-widest text-gold-400">VERIFICAR RESULTADO REAL</h3>
            <p className="text-xs font-mono text-gray-500">Ingresa los números reales del sorteo</p>
            <div className="grid grid-cols-3 gap-3">
              {['p1','p2','p3'].map((k,i) => (
                <input key={k} type="number" min="0" max="99" placeholder={['1ra','2da','3ra'][i]}
                  value={realResult[k]}
                  onChange={e => setRealResult(r=>({...r,[k]:e.target.value}))}
                  className="bg-dark-700 border border-dark-500 focus:border-gold-500 rounded-lg px-2 py-3 font-mono text-2xl text-center text-white outline-none"
                />
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={()=>setVerifying(null)} className="py-2.5 border border-dark-500 text-gray-400 rounded-lg font-body text-sm">Cancelar</button>
              <button onClick={handleVerify} className="py-2.5 bg-gold-500 text-dark-900 rounded-lg font-bold text-sm">Verificar</button>
            </div>
          </div>
        </div>
      )}

      {/* Pending picks */}
      {pending.length > 0 && (
        <section>
          <h3 className="font-display text-lg tracking-widest text-amber-400 mb-3 flex items-center gap-2">
            <Clock size={15}/> PENDIENTES ({pending.length})
          </h3>
          <div className="space-y-2">
            {pending.map(p => (
              <div key={p.id} className="bg-dark-800/50 border border-dark-600 rounded-xl px-4 py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono text-gray-600 shrink-0">{p.date}</span>
                  <span className="text-xs bg-dark-600 text-gray-400 px-2 py-0.5 rounded font-mono shrink-0">{p.lottery === 'Gana Más' ? 'GM' : 'NN'}</span>
                  <div className="flex gap-1.5">
                    {[p.p1,p.p2,p.p3].map((n,i)=>(
                      <span key={i} className={`font-mono font-bold text-base px-1.5 py-0.5 rounded ${i===0?'text-gold-400':'text-white'}`}>{n}</span>
                    ))}
                  </div>
                  {p.amount && <span className="text-xs font-mono text-gray-600">RD${p.amount}</span>}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => handleResend(p)} disabled={sending===p.id}
                    className="p-1.5 text-gray-500 hover:text-gold-400 transition-colors">
                    <Send size={14}/>
                  </button>
                  <button onClick={() => setVerifying(p.id)}
                    className="text-xs bg-emerald-900/40 border border-emerald-800/40 text-emerald-400 px-3 py-1 rounded-lg font-mono hover:bg-emerald-900/60 transition-all">
                    Verificar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Verified picks */}
      {verified.length > 0 && (
        <section>
          <h3 className="font-display text-lg tracking-widest text-gray-400 mb-3">
            HISTORIAL VERIFICADO ({verified.length})
          </h3>
          <div className="space-y-2">
            {[...verified].reverse().map(p => (
              <div key={p.id} className="bg-dark-800/30 border border-dark-700/50 rounded-xl px-4 py-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0 flex-wrap">
                  <span className="text-xs font-mono text-gray-600 shrink-0">{p.date}</span>
                  <span className="text-xs bg-dark-600 text-gray-500 px-1.5 py-0.5 rounded font-mono">{p.lottery === 'Gana Más' ? 'GM' : 'NN'}</span>
                  <div className="flex gap-1">
                    {[p.p1,p.p2,p.p3].map((n,i)=>(
                      <span key={i} className="font-mono text-sm text-gray-400 px-1 rounded bg-dark-700">{n}</span>
                    ))}
                  </div>
                  {p.realP1 && (
                    <>
                      <span className="text-gray-600 text-xs">→</span>
                      <div className="flex gap-1">
                        {[p.realP1,p.realP2,p.realP3].map((n,i)=>(
                          <span key={i} className="font-mono text-sm text-emerald-400 px-1 rounded bg-emerald-900/20">{String(n).padStart(2,'0')}</span>
                        ))}
                      </div>
                    </>
                  )}
                </div>
                <div className="shrink-0">
                  <span className={`text-xs font-mono px-2.5 py-1 rounded-full border uppercase ${RESULT_STYLES[p.result] || ''}`}>
                    {p.result === 'miss' ? 'MISS' : p.result}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {picks.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-600 font-mono text-sm">No hay picks aún.</p>
          <p className="text-gray-700 font-mono text-xs mt-1">Genera uno desde Dashboard o usa el botón Manual.</p>
        </div>
      )}
    </div>
  )
}
