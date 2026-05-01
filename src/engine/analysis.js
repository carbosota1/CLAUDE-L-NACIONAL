// ─── CLAUDE L-NACIONAL | Analysis Engine ─────────────────────────────────────
// Methods: Rating RD · Overdue · Co-occurrence · Sum Analysis ·
//          Chi² · Mutual Information · Markov Chain · Bayesian · Monte Carlo
//          + WMA (Weighted Moving Average) as cross-cutting layer

const ALL_NUMS = Array.from({ length: 100 }, (_, i) => String(i).padStart(2, '0'))

// ── WMA weights: most recent draws weighted more ──────────────────────────────
function wmaWeight(idx, total, halfLife = 30) {
  const age = total - 1 - idx
  return Math.exp(-age / halfLife)
}

// ── 1. Rating de Rentabilidad (Dominican formula) ────────────────────────────
function calcRatingRD(draws) {
  const ratings = {}
  ALL_NUMS.forEach(n => { ratings[n] = 0 })
  draws.forEach((d, idx) => {
    const w = wmaWeight(idx, draws.length)
    if (d.p1 === ALL_NUMS[parseInt(d.p1)]) ratings[d.p1] = (ratings[d.p1] || 0) + 60 * w
    if (d.p2) ratings[d.p2] = (ratings[d.p2] || 0) + 8 * w
    if (d.p3) ratings[d.p3] = (ratings[d.p3] || 0) + 4 * w
    // penalize all that didn't appear
    ALL_NUMS.forEach(n => {
      if (n !== d.p1 && n !== d.p2 && n !== d.p3) ratings[n] -= 1 * w
    })
  })
  return ratings
}

// ── 2. Overdue / Gap Analysis ─────────────────────────────────────────────────
function calcOverdue(draws) {
  const lastSeen = {}
  for (let i = draws.length - 1; i >= 0; i--) {
    for (const p of [draws[i].p1, draws[i].p2, draws[i].p3]) {
      if (lastSeen[p] === undefined) lastSeen[p] = draws.length - 1 - i
    }
  }
  ALL_NUMS.forEach(n => { if (lastSeen[n] === undefined) lastSeen[n] = draws.length })
  return lastSeen // gap = draws since last seen
}

// ── 3. Co-occurrence (draw N → draw N+1) ─────────────────────────────────────
function calcCoOccurrence(draws) {
  const co = {}
  for (let i = 0; i < draws.length - 1; i++) {
    const cur = [draws[i].p1, draws[i].p2, draws[i].p3]
    const nxt = [draws[i + 1].p1, draws[i + 1].p2, draws[i + 1].p3]
    for (const c of cur) {
      if (!co[c]) co[c] = {}
      for (const n of nxt) co[c][n] = (co[c][n] || 0) + 1
    }
  }
  return co
}

// ── 4. Sum Analysis ───────────────────────────────────────────────────────────
function calcSumProfile(draws) {
  const sums = draws.map(d => parseInt(d.p1) + parseInt(d.p2) + parseInt(d.p3))
  const total = sums.length
  const mean  = sums.reduce((a, b) => a + b, 0) / total
  const std   = Math.sqrt(sums.map(s => (s - mean) ** 2).reduce((a, b) => a + b, 0) / total)
  return { mean, std, min: mean - std, max: mean + std }
}

// ── 5. Chi-Squared Test ───────────────────────────────────────────────────────
function calcChiSquared(draws) {
  const freq = {}
  ALL_NUMS.forEach(n => { freq[n] = 0 })
  draws.forEach(d => {
    freq[d.p1]++; freq[d.p2]++; freq[d.p3]++
  })
  const total      = draws.length * 3
  const expected   = total / 100
  const chiScores  = {}
  ALL_NUMS.forEach(n => {
    const obs = freq[n]
    chiScores[n] = ((obs - expected) ** 2) / expected
  })
  // critical value for p=0.05, df=99 ≈ 123.2
  const chiTotal = Object.values(chiScores).reduce((a, b) => a + b, 0)
  const isSignificant = chiTotal > 123.2
  return { chiScores, chiTotal, isSignificant, freq }
}

// ── 6. Mutual Information ─────────────────────────────────────────────────────
function calcMutualInfo(draws) {
  if (draws.length < 10) return { mi: {}, miLevel: 'Insuficiente' }
  const pairCounts = {}
  const numCounts  = {}
  const N = draws.length - 1

  for (let i = 0; i < N; i++) {
    const cur = [draws[i].p1, draws[i].p2, draws[i].p3]
    const nxt = [draws[i + 1].p1, draws[i + 1].p2, draws[i + 1].p3]
    for (const c of cur) {
      numCounts[c] = (numCounts[c] || 0) + 1
      for (const n of nxt) {
        const key = `${c}|${n}`
        pairCounts[key] = (pairCounts[key] || 0) + 1
      }
    }
    for (const n of nxt) numCounts[n] = (numCounts[n] || 0) + 1
  }

  const mi = {}
  Object.entries(pairCounts).forEach(([key, count]) => {
    const [a, b] = key.split('|')
    const pAB = count / (N * 9)
    const pA  = (numCounts[a] || 1) / (N * 3)
    const pB  = (numCounts[b] || 1) / (N * 3)
    if (pAB > 0) mi[key] = pAB * Math.log2(pAB / (pA * pB))
  })

  const topMI  = Object.entries(mi).sort((a, b) => b[1] - a[1]).slice(0, 20)
  const avgMI  = topMI.reduce((s, [, v]) => s + v, 0) / (topMI.length || 1)
  const miLevel = avgMI > 0.5 ? 'Alta' : avgMI > 0.2 ? 'Media' : 'Baja'
  return { mi, topMI, miLevel, avgMI }
}

// ── 7. Markov Chain (1-step + 2-step superposition) ──────────────────────────
function calcMarkov(draws) {
  const trans1 = {} // 1-step
  const trans2 = {} // 2-step

  for (let i = 0; i < draws.length - 1; i++) {
    const cur = [draws[i].p1, draws[i].p2, draws[i].p3]
    const nxt = [draws[i + 1].p1, draws[i + 1].p2, draws[i + 1].p3]
    for (const c of cur) {
      if (!trans1[c]) trans1[c] = {}
      for (const n of nxt) trans1[c][n] = (trans1[c][n] || 0) + 1
    }
  }
  for (let i = 0; i < draws.length - 2; i++) {
    const cur = [draws[i].p1, draws[i].p2, draws[i].p3]
    const nxt = [draws[i + 2].p1, draws[i + 2].p2, draws[i + 2].p3]
    for (const c of cur) {
      if (!trans2[c]) trans2[c] = {}
      for (const n of nxt) trans2[c][n] = (trans2[c][n] || 0) + 1
    }
  }

  // Normalize rows to probabilities
  const normalize = (matrix) => {
    const norm = {}
    Object.entries(matrix).forEach(([from, tos]) => {
      const total = Object.values(tos).reduce((a, b) => a + b, 0)
      norm[from] = {}
      Object.entries(tos).forEach(([to, cnt]) => { norm[from][to] = cnt / total })
    })
    return norm
  }

  const p1 = normalize(trans1)
  const p2 = normalize(trans2)

  // Superpose: combined = p1 + p2 for each transition
  const lastDraw = draws[draws.length - 1]
  const lastNums = lastDraw ? [lastDraw.p1, lastDraw.p2, lastDraw.p3] : []
  const markovScores = {}
  ALL_NUMS.forEach(n => { markovScores[n] = 0 })

  lastNums.forEach(src => {
    ALL_NUMS.forEach(n => {
      const s1 = p1[src]?.[n] || 0
      const s2 = p2[src]?.[n] || 0
      markovScores[n] += (s1 + s2) / lastNums.length
    })
  })

  const maxScore = Math.max(...Object.values(markovScores)) || 1
  const confidence = Math.round(maxScore * 100)
  return { markovScores, p1, p2, confidence: Math.min(confidence, 99) }
}

// ── 8. Bayesian Inference (Dirichlet-Multinomial, simplified) ─────────────────
function calcBayesian(draws) {
  // Prior: uniform Dirichlet α=1 for all 100 numbers
  const alpha0 = 1
  const counts = {}
  ALL_NUMS.forEach(n => { counts[n] = alpha0 })

  draws.forEach((d, idx) => {
    const w = wmaWeight(idx, draws.length)
    counts[d.p1] += w
    counts[d.p2] += w
    counts[d.p3] += w
  })

  const totalAlpha = Object.values(counts).reduce((a, b) => a + b, 0)
  const posterior  = {}
  ALL_NUMS.forEach(n => { posterior[n] = counts[n] / totalAlpha })
  return posterior
}

// ── 9. Monte Carlo Simulation ─────────────────────────────────────────────────
function runMonteCarlo(draws, iterations = 5000) {
  if (draws.length < 5) return {}
  // Build probability table from frequency
  const freq = {}
  ALL_NUMS.forEach(n => { freq[n] = 1 }) // laplace smoothing
  draws.forEach((d, idx) => {
    const w = wmaWeight(idx, draws.length)
    freq[d.p1] += w; freq[d.p2] += w; freq[d.p3] += w
  })
  const total  = Object.values(freq).reduce((a, b) => a + b, 0)
  const probs  = ALL_NUMS.map(n => freq[n] / total)
  const cumulative = []
  probs.reduce((acc, p, i) => { cumulative[i] = acc + p; return acc + p }, 0)

  const sampleNum = () => {
    const r = Math.random()
    for (let i = 0; i < cumulative.length; i++) if (r <= cumulative[i]) return ALL_NUMS[i]
    return ALL_NUMS[99]
  }

  const simCount = {}
  ALL_NUMS.forEach(n => { simCount[n] = 0 })
  for (let i = 0; i < iterations; i++) {
    simCount[sampleNum()]++
    simCount[sampleNum()]++
    simCount[sampleNum()]++
  }
  const simProb = {}
  const totalSim = iterations * 3
  ALL_NUMS.forEach(n => { simProb[n] = simCount[n] / totalSim })
  return simProb
}

// ── COMPOSITE SCORER ──────────────────────────────────────────────────────────
// Weights per method
const W = {
  rating:   0.15,
  overdue:  0.10,
  coOccur:  0.10,
  sum:      0.05,
  chi:      0.15,
  mi:       0.15,
  markov:   0.15,
  bayes:    0.10,
  monte:    0.05,
}

export function runFullAnalysis(draws) {
  if (!draws || draws.length < 5) return null

  const n = draws.length

  // Run all methods
  const rating   = calcRatingRD(draws)
  const overdue  = calcOverdue(draws)
  const coOccur  = calcCoOccurrence(draws)
  const sumProf  = calcSumProfile(draws)
  const chi      = calcChiSquared(draws)
  const mi       = calcMutualInfo(draws)
  const markov   = calcMarkov(draws)
  const bayes    = calcBayesian(draws)
  const monte    = runMonteCarlo(draws)

  // Last draw numbers for co-occurrence lookup
  const lastDraw = draws[n - 1]
  const lastNums = lastDraw ? [lastDraw.p1, lastDraw.p2, lastDraw.p3] : []

  // Normalize helper
  const normalize = (obj) => {
    const vals = Object.values(obj)
    const min = Math.min(...vals), max = Math.max(...vals)
    const range = max - min || 1
    const norm = {}
    Object.keys(obj).forEach(k => { norm[k] = (obj[k] - min) / range })
    return norm
  }

  // Normalize each method's scores
  const nRating  = normalize(rating)
  const nOverdue = normalize(overdue) // higher overdue = higher score
  const nChi     = normalize(chi.chiScores)
  const nBayes   = normalize(bayes)
  const nMonte   = normalize(monte)
  const nMarkov  = normalize(markov.markovScores)

  // MI: score from topMI pairs given last draw
  const miScores = {}
  ALL_NUMS.forEach(n => { miScores[n] = 0 })
  if (mi.mi) {
    lastNums.forEach(src => {
      ALL_NUMS.forEach(tgt => {
        const key = `${src}|${tgt}`
        miScores[tgt] += mi.mi[key] || 0
      })
    })
  }
  const nMI = normalize(miScores)

  // Co-occurrence scores from last draw
  const coScores = {}
  ALL_NUMS.forEach(n => { coScores[n] = 0 })
  lastNums.forEach(src => {
    if (coOccur[src]) {
      const total = Object.values(coOccur[src]).reduce((a, b) => a + b, 0) || 1
      ALL_NUMS.forEach(n => { coScores[n] += (coOccur[src][n] || 0) / total })
    }
  })
  const nCo = normalize(coScores)

  // Sum filter: score numbers whose sum w/ top2 falls in historical range
  const sumScores = {}
  const top2Candidates = Object.entries(nMarkov).sort((a, b) => b[1] - a[1]).slice(0, 2).map(e => e[0])
  ALL_NUMS.forEach(n => {
    const candidate = parseInt(n)
    const base = top2Candidates.reduce((s, c) => s + parseInt(c), 0)
    const total = base + candidate
    const inRange = total >= sumProf.min && total <= sumProf.max
    sumScores[n] = inRange ? 1 : 0.2
  })

  // Composite score per number
  const composite = {}
  ALL_NUMS.forEach(n => {
    composite[n] = (
      W.rating  * (nRating[n]  || 0) +
      W.overdue * (nOverdue[n] || 0) +
      W.coOccur * (nCo[n]      || 0) +
      W.sum     * (sumScores[n]|| 0) +
      W.chi     * (nChi[n]     || 0) +
      W.mi      * (nMI[n]      || 0) +
      W.markov  * (nMarkov[n]  || 0) +
      W.bayes   * (nBayes[n]   || 0) +
      W.monte   * (nMonte[n]   || 0)
    )
  })

  // Rank all numbers
  const ranked = Object.entries(composite)
    .sort((a, b) => b[1] - a[1])
    .map(([num, score], rank) => ({
      num,
      rank: rank + 1,
      compositeScore: Math.round(score * 100),
      ratingScore:   Math.round((nRating[num]  || 0) * 100),
      overdueGap:    overdue[num] || 0,
      markovScore:   Math.round((nMarkov[num]  || 0) * 100),
      bayesProb:     +(bayes[num] * 100).toFixed(3),
      chiScore:      +(chi.chiScores[num] || 0).toFixed(2),
      miScore:       +(miScores[num] || 0).toFixed(4),
    }))

  // Hot & Cold
  const freqSorted = Object.entries(chi.freq).sort((a, b) => b[1] - a[1])
  const hot  = freqSorted.slice(0, 10).map(([n, c]) => ({ num: n, count: c }))
  const cold = freqSorted.slice(-10).reverse().map(([n, c]) => ({ num: n, count: c }))
  const overdueTop = Object.entries(overdue).sort((a, b) => b[1] - a[1]).slice(0, 10)
    .map(([n, g]) => ({ num: n, gap: g }))

  return {
    picks: ranked,           // top = best picks
    hot, cold, overdueTop,
    sumProfile: sumProf,
    chiValid:   chi.isSignificant,
    miLevel:    mi.miLevel,
    markovConfidence: markov.confidence,
    overdueMax: overdueTop[0]?.gap || 0,
    total: n,
    lastDraw,
  }
}

// ── Performance Calculator ─────────────────────────────────────────────────────
export function calcPerformance(picks) {
  const verified = picks.filter(p => p.status === 'verified')
  if (!verified.length) return { hitRate: 0, streak: 0, roi: 0, totalPlayed: 0, totalWon: 0 }

  const recent30 = verified.slice(-30)
  const hits     = recent30.filter(p => p.result !== 'miss')
  const hitRate  = Math.round((hits.length / recent30.length) * 100)

  // Streak: count consecutive wins/losses from most recent
  let streak = 0
  const rev  = [...verified].reverse()
  if (rev.length > 0) {
    const firstWin = rev[0].result !== 'miss'
    for (const p of rev) {
      if ((p.result !== 'miss') === firstWin) streak += firstWin ? 1 : -1
      else break
    }
  }

  const totalAmountPlayed = verified.reduce((s, p) => s + (parseFloat(p.amount) || 0), 0)
  const totalWon          = verified.reduce((s, p) => s + (parseFloat(p.payout) || 0), 0)
  const roi = totalAmountPlayed > 0
    ? Math.round(((totalWon - totalAmountPlayed) / totalAmountPlayed) * 100)
    : 0

  return { hitRate, streak, roi, totalPlayed: verified.length, totalWon, totalAmountPlayed }
}
