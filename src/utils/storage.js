// ─── CLAUDE L-NACIONAL | Storage Utils ──────────────────────────────────────

export const KEYS = {
  HISTORY:     'cln_history',
  PICKS:       'cln_picks',
  PERFORMANCE: 'cln_performance',
  SETTINGS:    'cln_settings',
}

export function load(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch { return fallback }
}

export function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch {}
}

export function exportAllData() {
  const data = {
    version: '1.0',
    exportedAt: new Date().toISOString(),
    history:     load(KEYS.HISTORY, []),
    picks:       load(KEYS.PICKS, []),
    performance: load(KEYS.PERFORMANCE, []),
    settings:    load(KEYS.SETTINGS, {}),
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `claude-l-nacional-backup-${new Date().toISOString().split('T')[0]}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export function importAllData(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)
        if (data.history)     save(KEYS.HISTORY,     data.history)
        if (data.picks)       save(KEYS.PICKS,        data.picks)
        if (data.performance) save(KEYS.PERFORMANCE,  data.performance)
        if (data.settings)    save(KEYS.SETTINGS,     data.settings)
        resolve(data)
      } catch (err) { reject(err) }
    }
    reader.readAsText(file)
  })
}
