"""
CLAUDE L-NACIONAL — Motor de Análisis Estadístico v2
=====================================================
Mejoras vs v1:
  - Análisis por POSICIÓN separado (1ra, 2da, 3ra independientes)
  - Ventana deslizante de 30 sorteos recientes (peso 40%)
  - Análisis de RANGOS dominantes (00-24, 25-49, 50-74, 75-99)
  - Anti-repetición: penaliza picks recomendados sin éxito últimos 3 días
  - Análisis de DÍGITOS (decena y unidad)
  - Overdue reducido 10%→5%, Markov aumentado 15%→20%
  - WMA half-life reducido 30→15 (más peso a datos recientes)
"""

import json
import math
import csv
import datetime
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy import stats
from sklearn.metrics import mutual_info_score

# ── Constants ────────────────────────────────────────────────────────────────
ALL_NUMS  = [str(i).zfill(2) for i in range(100)]
NUM_IDX   = {n: i for i, n in enumerate(ALL_NUMS)}
DATA_DIR  = Path(__file__).parent.parent / "data"
HALF_LIFE = 10   # Further reduced: last 2 weeks dominate

# Updated weights
WEIGHTS = {
    "rating":    0.10,  # Rating RD
    "overdue":   0.04,  # Reduced
    "cooccur":   0.08,  # Co-occurrence
    "sum":       0.04,  # Sum analysis
    "chi2":      0.10,  # Chi²
    "mi":        0.12,  # Mutual Information
    "markov":    0.20,  # Highest: best real-time signal
    "bayes":     0.08,  # Bayesian
    "monte":     0.04,  # Monte Carlo
    "position":  0.06,  # Position analysis
    "range":     0.08,  # Increased: ranges matter
    "digit":     0.06,  # Increased: digit patterns matter
}

PRIZE_MULTIPLIERS = {
    "tripleta": 20000,
    "pale":     1000,
    "1ra":      60,
    "2da":      8,
    "3ra":      5,
    "miss":     0,
}


# ── JSON I/O ──────────────────────────────────────────────────────────────────
class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return super().default(obj)

def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, cls=_NumpyEncoder), encoding="utf-8")

def get_draws(lottery: str) -> list[dict]:
    data = load_json(DATA_DIR / "history.json")
    draws = [d for d in data.get("history", []) if d["lottery"] == lottery]
    return sorted(draws, key=lambda x: x["date"])


# ── WMA ───────────────────────────────────────────────────────────────────────
def wma_weight(idx: int, total: int, half_life: float = HALF_LIFE) -> float:
    age = (total - 1) - idx
    return math.exp(-age / half_life)


# ── Recent window (last 30 draws) ─────────────────────────────────────────────
def split_windows(draws: list[dict]) -> tuple[list, list]:
    """Split draws into recent (last 45) and full history."""
    recent = draws[-45:] if len(draws) >= 45 else draws
    return draws, recent


# ── Method 1: Rating RD ───────────────────────────────────────────────────────
def calc_rating_rd(draws: list[dict]) -> dict[str, float]:
    ratings = defaultdict(float)
    n = len(draws)
    for idx, d in enumerate(draws):
        w = wma_weight(idx, n)
        present = {d["p1"], d["p2"], d["p3"]}
        ratings[d["p1"]] += 60 * w
        ratings[d["p2"]] += 8  * w
        ratings[d["p3"]] += 4  * w
        for num in ALL_NUMS:
            if num not in present:
                ratings[num] -= 1 * w
    return dict(ratings)


# ── Method 2: Overdue ─────────────────────────────────────────────────────────
def calc_overdue(draws: list[dict]) -> dict[str, int]:
    last_seen = {}
    for i in range(len(draws) - 1, -1, -1):
        for p in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            if p not in last_seen:
                last_seen[p] = len(draws) - 1 - i
    for num in ALL_NUMS:
        if num not in last_seen:
            last_seen[num] = len(draws)
    return last_seen


# ── Method 3: Co-occurrence ───────────────────────────────────────────────────
def calc_cooccurrence(draws: list[dict]) -> dict:
    co = defaultdict(lambda: defaultdict(int))
    for i in range(len(draws) - 1):
        cur = [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]
        nxt = [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]]
        for c in cur:
            for n in nxt:
                co[c][n] += 1
    result = {}
    for src, targets in co.items():
        total = sum(targets.values())
        result[src] = {tgt: cnt/total for tgt, cnt in targets.items()}
    return result

def cooccur_scores_for_last(draws: list[dict], co: dict) -> dict[str, float]:
    if not draws:
        return {n: 0.0 for n in ALL_NUMS}
    last = draws[-1]
    last_nums = [last["p1"], last["p2"], last["p3"]]
    scores = defaultdict(float)
    for src in last_nums:
        if src in co:
            for tgt, prob in co[src].items():
                scores[tgt] += prob / len(last_nums)
    return {n: scores.get(n, 0.0) for n in ALL_NUMS}


# ── Method 4: Sum Analysis ────────────────────────────────────────────────────
def calc_sum_profile(draws: list[dict]) -> dict:
    sums = [int(d["p1"]) + int(d["p2"]) + int(d["p3"]) for d in draws]
    if not sums:
        return {"mean": 99, "std": 30, "low": 69, "high": 129}
    mean = float(np.mean(sums))
    std  = float(np.std(sums))
    return {"mean": mean, "std": std, "low": mean - std, "high": mean + std,
            "p10": float(np.percentile(sums, 10)), "p90": float(np.percentile(sums, 90))}

def sum_score(num: str, candidates: list[str], profile: dict) -> float:
    base  = sum(int(c) for c in candidates[:2]) if len(candidates) >= 2 else 99
    total = base + int(num)
    return 1.0 if profile["low"] <= total <= profile["high"] else 0.2


# ── Method 5: Chi² ───────────────────────────────────────────────────────────
def calc_chi2(draws: list[dict]) -> dict:
    freq = defaultdict(int)
    for d in draws:
        freq[d["p1"]] += 1
        freq[d["p2"]] += 1
        freq[d["p3"]] += 1
    observed  = np.array([freq.get(n, 0) for n in ALL_NUMS], dtype=float)
    total_obs = observed.sum()
    expected  = np.full(100, total_obs / 100)
    chi2_stat, p_value = stats.chisquare(observed, f_exp=expected)
    per_num = ((observed - expected) ** 2) / expected
    return {
        "freq":         {n: int(freq.get(n, 0)) for n in ALL_NUMS},
        "chi2_scores":  {n: float(per_num[i]) for i, n in enumerate(ALL_NUMS)},
        "chi2_stat":    float(chi2_stat),
        "p_value":      float(p_value),
        "significant":  p_value < 0.05,
    }


# ── Method 6: Mutual Information ─────────────────────────────────────────────
def calc_mutual_info(draws: list[dict]) -> dict:
    if len(draws) < 10:
        return {"mi_scores": {n: 0.0 for n in ALL_NUMS}, "mi_level": "Insuficiente", "avg_mi": 0.0}
    cur_labels, nxt_labels = [], []
    for i in range(len(draws) - 1):
        for c in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            for n in [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]]:
                cur_labels.append(NUM_IDX[c])
                nxt_labels.append(NUM_IDX[n])
    mi_global = mutual_info_score(cur_labels, nxt_labels)
    last = draws[-1]
    last_nums = [last["p1"], last["p2"], last["p3"]]
    mi_scores = {}
    for tgt in ALL_NUMS:
        score = 0.0
        for src in last_nums:
            y_src = [int(src in [d["p1"],d["p2"],d["p3"]]) for d in draws[:-1]]
            y_tgt = [int(tgt in [d["p1"],d["p2"],d["p3"]]) for d in draws[1:]]
            if len(set(y_src)) > 1 and len(set(y_tgt)) > 1:
                score += mutual_info_score(y_src, y_tgt)
        mi_scores[tgt] = score / len(last_nums)
    avg_mi   = float(np.mean(list(mi_scores.values())))
    mi_level = "Alta" if avg_mi > 0.01 else "Media" if avg_mi > 0.003 else "Baja"
    return {"mi_scores": mi_scores, "mi_level": mi_level, "avg_mi": avg_mi, "mi_global": float(mi_global)}


# ── Method 7: Markov Chain ────────────────────────────────────────────────────
def calc_markov(draws: list[dict]) -> dict:
    T1 = np.zeros((100, 100))
    T2 = np.zeros((100, 100))
    for i in range(len(draws) - 1):
        for c in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            for n in [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]]:
                T1[NUM_IDX[c], NUM_IDX[n]] += 1
    for i in range(len(draws) - 2):
        for c in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            for n in [draws[i+2]["p1"], draws[i+2]["p2"], draws[i+2]["p3"]]:
                T2[NUM_IDX[c], NUM_IDX[n]] += 1
    def row_norm(M):
        rs = M.sum(axis=1, keepdims=True); rs[rs==0] = 1; return M / rs
    P = (row_norm(T1) + row_norm(T2)) / 2
    last     = draws[-1]
    last_idx = [NUM_IDX[last["p1"]], NUM_IDX[last["p2"]], NUM_IDX[last["p3"]]]
    combined = P[last_idx, :].mean(axis=0)
    markov_scores    = {ALL_NUMS[i]: float(combined[i]) for i in range(100)}
    expected_baseline = 1.0 / 100
    max_score = max(markov_scores.values()) if markov_scores else expected_baseline
    lift      = (max_score - expected_baseline) / expected_baseline
    confidence = min(int(lift * 100), 99)
    return {"markov_scores": markov_scores, "confidence": confidence, "max_prob": round(max_score * 100, 2)}


# ── Method 8: Bayesian ────────────────────────────────────────────────────────
def calc_bayesian(draws: list[dict]) -> dict[str, float]:
    alpha = {n: 1.0 for n in ALL_NUMS}
    n = len(draws)
    for idx, d in enumerate(draws):
        w = wma_weight(idx, n)
        alpha[d["p1"]] += w
        alpha[d["p2"]] += w
        alpha[d["p3"]] += w
    total = sum(alpha.values())
    return {num: alpha[num] / total for num in ALL_NUMS}


# ── Method 9: Monte Carlo ─────────────────────────────────────────────────────
def calc_monte_carlo(draws: list[dict], iterations: int = 10_000) -> dict[str, float]:
    if len(draws) < 5:
        return {n: 1/100 for n in ALL_NUMS}
    freq = defaultdict(float)
    for n in ALL_NUMS: freq[n] = 1.0
    for idx, d in enumerate(draws):
        w = wma_weight(idx, len(draws))
        freq[d["p1"]] += w; freq[d["p2"]] += w; freq[d["p3"]] += w
    probs = np.array([freq[n] for n in ALL_NUMS], dtype=float)
    probs /= probs.sum()
    rng      = np.random.default_rng(seed=42)
    samples  = rng.choice(ALL_NUMS, size=iterations * 3, p=probs)
    sim_count = defaultdict(int)
    for s in samples: sim_count[s] += 1
    return {n: sim_count[n] / (iterations * 3) for n in ALL_NUMS}


# ── NEW Method 10: Position Analysis ─────────────────────────────────────────
def calc_position_scores(draws: list[dict], recent: list[dict]) -> dict[str, dict[str, float]]:
    """
    Analyze frequency of each number per position (1ra, 2da, 3ra) separately.
    Uses recent window (last 30) with 60% weight + full history 40%.
    """
    positions = ["p1", "p2", "p3"]
    result = {}
    for pos in positions:
        freq_full   = defaultdict(float)
        freq_recent = defaultdict(float)
        for d in draws:   freq_full[d[pos]]   += 1
        for d in recent:  freq_recent[d[pos]] += 1
        # Blend: 40% full history + 60% recent
        scores = {}
        total_full   = sum(freq_full.values())   or 1
        total_recent = sum(freq_recent.values()) or 1
        for n in ALL_NUMS:
            scores[n] = (
                0.40 * (freq_full.get(n, 0)   / total_full) +
                0.60 * (freq_recent.get(n, 0) / total_recent)
            )
        result[pos] = scores
    return result


# ── NEW Method 11: Range Dominance ────────────────────────────────────────────
def calc_range_scores(recent: list[dict]) -> dict[str, float]:
    """
    Detect which range is hot using last 14 draws.
    Uses exponential decay so very recent draws matter more.
    Amplifies scores for hot ranges above baseline (25%).
    """
    last14 = recent[-14:] if len(recent) >= 14 else recent
    ranges = {"00-24": 0.0, "25-49": 0.0, "50-74": 0.0, "75-99": 0.0}
    n = len(last14)
    for idx, d in enumerate(last14):
        w = math.exp(-(n - 1 - idx) / 7)  # half-life=7 draws
        for p in [d["p1"], d["p2"], d["p3"]]:
            v = int(p)
            if   v <= 24: ranges["00-24"] += w
            elif v <= 49: ranges["25-49"] += w
            elif v <= 74: ranges["50-74"] += w
            else:         ranges["75-99"] += w
    total = sum(ranges.values()) or 1
    baseline = 0.25  # uniform baseline per range
    # Amplify: ranges above baseline get boosted, below get penalized
    range_scores = {}
    for rng, cnt in ranges.items():
        prob = cnt / total
        # Score = how much above/below baseline, amplified
        range_scores[rng] = max(0.1, prob / baseline)
    scores = {}
    for num in ALL_NUMS:
        v = int(num)
        if   v <= 24: rng = "00-24"
        elif v <= 49: rng = "25-49"
        elif v <= 74: rng = "50-74"
        else:         rng = "75-99"
        scores[num] = range_scores[rng]
    return scores


# ── NEW Method 12: Digit Analysis ────────────────────────────────────────────
def calc_digit_scores(recent: list[dict]) -> dict[str, float]:
    """
    Analyze hot decenas and unidades in last 21 draws with decay.
    Amplifies numbers whose tens AND units are both hot.
    """
    last21 = recent[-21:] if len(recent) >= 21 else recent
    n = len(last21)
    tens_freq  = defaultdict(float)
    units_freq = defaultdict(float)
    for idx, d in enumerate(last21):
        w = math.exp(-(n - 1 - idx) / 10)
        for p in [d["p1"], d["p2"], d["p3"]]:
            tens_freq[int(p) // 10]  += w
            units_freq[int(p) % 10]  += w
    total_t = sum(tens_freq.values())  or 1
    total_u = sum(units_freq.values()) or 1
    base_t = 1/10  # 10 possible tens
    base_u = 1/10  # 10 possible units
    scores = {}
    for num in ALL_NUMS:
        v = int(num)
        t_prob = tens_freq.get(v // 10, 0) / total_t
        u_prob = units_freq.get(v % 10, 0)  / total_u
        # Lift over baseline for both digits, multiply for amplification
        t_lift = t_prob / base_t
        u_lift = u_prob / base_u
        scores[num] = (t_lift * u_lift) ** 0.5  # geometric mean
    return scores


# ── NEW: Anti-repetition Penalty ─────────────────────────────────────────────
def calc_anti_repeat_penalty(lottery: str) -> dict[str, float]:
    """
    Load the last 3 picks for this lottery from picks_log.json.
    Numbers that have been recommended and missed get a penalty.
    """
    penalty = {n: 0.0 for n in ALL_NUMS}
    picks_file = DATA_DIR / "picks_log.json"
    if not picks_file.exists():
        return penalty
    data  = load_json(picks_file)
    picks = [p for p in data.get("picks", []) if p.get("lottery") == lottery]
    # Last 3 picks that were misses
    recent_picks = picks[-3:]
    for p in recent_picks:
        if p.get("result") == "miss" or p.get("status") == "pending":
            for num in [p.get("p1",""), p.get("p2",""), p.get("p3","")]:
                if num in penalty:
                    penalty[num] += 0.33  # accumulate penalty
    return penalty


# ── Normalize ─────────────────────────────────────────────────────────────────
def normalize(scores: dict[str, float]) -> dict[str, float]:
    vals = list(scores.values())
    mn, mx = min(vals), max(vals)
    rng = mx - mn or 1e-9
    return {k: (v - mn) / rng for k, v in scores.items()}


# ── Full Analysis Pipeline ────────────────────────────────────────────────────
def run_full_analysis(lottery: str) -> dict:
    draws = get_draws(lottery)
    if len(draws) < 5:
        return {"error": f"Insuficientes datos: {len(draws)} sorteos (mínimo 5)"}

    full, recent = split_windows(draws)
    print(f"  Analizando {len(draws)} sorteos ({len(recent)} recientes) de {lottery}...")

    print("  [1/9] Rating de Rentabilidad...")
    rating    = calc_rating_rd(draws)
    print("  [2/9] Overdue...")
    overdue   = calc_overdue(draws)
    print("  [3/9] Co-ocurrencia...")
    co        = calc_cooccurrence(draws)
    co_scores = cooccur_scores_for_last(draws, co)
    print("  [4/9] Sum Analysis...")
    sum_prof  = calc_sum_profile(draws)
    print("  [5/9] Chi²...")
    chi2      = calc_chi2(draws)
    print("  [6/9] Mutual Information...")
    mi        = calc_mutual_info(draws)
    print("  [7/9] Markov Chain...")
    markov    = calc_markov(draws)
    print("  [8/9] Bayesiano...")
    bayes     = calc_bayesian(draws)
    print("  [9/9] Monte Carlo...")
    monte     = calc_monte_carlo(draws)
    print("  [+] Análisis por Posición...")
    pos_scores = calc_position_scores(draws, recent)
    print("  [+] Rangos Dominantes...")
    range_sc  = calc_range_scores(recent)
    print("  [+] Análisis de Dígitos...")
    digit_sc  = calc_digit_scores(recent)
    print("  [+] Anti-repetición...")
    penalty   = calc_anti_repeat_penalty(lottery)

    # Normalize
    n_rating  = normalize(rating)
    n_overdue = normalize(overdue)
    n_co      = normalize(co_scores)
    n_chi2    = normalize(chi2["chi2_scores"])
    n_mi      = normalize(mi["mi_scores"])
    n_markov  = normalize(markov["markov_scores"])
    n_bayes   = normalize(bayes)
    n_monte   = normalize(monte)
    n_range   = normalize(range_sc)
    n_digit   = normalize(digit_sc)

    # Position: average of p1, p2, p3 scores per number
    pos_avg = {}
    for n in ALL_NUMS:
        pos_avg[n] = (pos_scores["p1"][n] + pos_scores["p2"][n] + pos_scores["p3"][n]) / 3
    n_position = normalize(pos_avg)

    top2_markov = sorted(markov["markov_scores"], key=lambda x: markov["markov_scores"][x], reverse=True)[:2]
    n_sum = normalize({num: sum_score(num, top2_markov, sum_prof) for num in ALL_NUMS})

    # Composite
    composite = {}
    for num in ALL_NUMS:
        raw = (
            WEIGHTS["rating"]   * n_rating.get(num, 0)    +
            WEIGHTS["overdue"]  * n_overdue.get(num, 0)   +
            WEIGHTS["cooccur"]  * n_co.get(num, 0)        +
            WEIGHTS["sum"]      * n_sum.get(num, 0)       +
            WEIGHTS["chi2"]     * n_chi2.get(num, 0)      +
            WEIGHTS["mi"]       * n_mi.get(num, 0)        +
            WEIGHTS["markov"]   * n_markov.get(num, 0)    +
            WEIGHTS["bayes"]    * n_bayes.get(num, 0)     +
            WEIGHTS["monte"]    * n_monte.get(num, 0)     +
            WEIGHTS["position"] * n_position.get(num, 0)  +
            WEIGHTS["range"]    * n_range.get(num, 0)     +
            WEIGHTS["digit"]    * n_digit.get(num, 0)
        )
        # Apply anti-repetition penalty
        raw *= max(0.5, 1.0 - penalty.get(num, 0))
        composite[num] = raw

    ranked = sorted(ALL_NUMS, key=lambda x: composite[x], reverse=True)

    picks = []
    for rank, num in enumerate(ranked[:20], 1):
        picks.append({
            "rank":            rank,
            "num":             num,
            "composite_score": round(composite[num] * 100, 2),
            "rating_score":    round(n_rating.get(num, 0) * 100, 2),
            "overdue_gap":     overdue.get(num, 0),
            "markov_score":    round(n_markov.get(num, 0) * 100, 2),
            "bayes_prob":      round(bayes.get(num, 0) * 100, 4),
            "chi2_score":      round(chi2["chi2_scores"].get(num, 0), 4),
            "mi_score":        round(mi["mi_scores"].get(num, 0), 6),
            "monte_prob":      round(monte.get(num, 0) * 100, 4),
            "pos_score":       round(n_position.get(num, 0) * 100, 2),
            "range_score":     round(n_range.get(num, 0) * 100, 2),
            "digit_score":     round(n_digit.get(num, 0) * 100, 2),
            "penalty":         round(penalty.get(num, 0), 2),
        })

    freq_sorted = sorted(chi2["freq"].items(), key=lambda x: x[1], reverse=True)
    hot         = [{"num": n, "count": c} for n, c in freq_sorted[:10]]
    cold        = [{"num": n, "count": c} for n, c in freq_sorted[-10:]]
    overdue_top = sorted(overdue.items(), key=lambda x: x[1], reverse=True)[:10]
    overdue_top = [{"num": n, "gap": g} for n, g in overdue_top]

    return {
        "lottery":           lottery,
        "analyzed_at":       datetime.datetime.now().isoformat(),
        "total_draws":       len(draws),
        "recent_draws":      len(recent),
        "picks":             picks,
        "hot":               hot,
        "cold":              cold,
        "overdue_top":       overdue_top,
        "sum_profile":       sum_prof,
        "chi2_stat":         chi2["chi2_stat"],
        "chi2_pvalue":       chi2["p_value"],
        "chi2_significant":  chi2["significant"],
        "mi_level":          mi["mi_level"],
        "mi_avg":            mi["avg_mi"],
        "markov_confidence": markov["confidence"],
        "markov_max_prob":   markov.get("max_prob", 0),
        "last_draw":         draws[-1] if draws else None,
    }


# ── Performance Calculator ────────────────────────────────────────────────────
def calc_performance(lottery: str | None = None) -> dict:
    data  = load_json(DATA_DIR / "picks_log.json")
    picks = data.get("picks", [])
    if lottery:
        picks = [p for p in picks if p.get("lottery") == lottery]
    verified = [p for p in picks if p.get("status") == "verified"]
    if not verified:
        return {"total_picks": 0, "verified_picks": 0, "hits": 0,
                "hit_rate": 0.0, "streak": 0, "roi": 0.0,
                "total_invested": 0.0, "total_won": 0.0}
    recent30  = verified[-30:]
    # Count main hits (paid) and alt hits separately
    main_hits = sum(1 for p in recent30 if p.get("result") not in ("miss", "alt_hit", None, ""))
    alt_hits  = sum(1 for p in recent30 if p.get("result") == "alt_hit")
    total_hits = main_hits + alt_hits
    hit_rate  = round(total_hits / len(recent30) * 100, 1) if recent30 else 0.0
    main_hit_rate = round(main_hits / len(recent30) * 100, 1) if recent30 else 0.0
    alt_hit_rate  = round(alt_hits  / len(recent30) * 100, 1) if recent30 else 0.0

    # Streak: only counts main hits (paid results)
    streak    = 0
    first_win = verified[-1].get("result") not in ("miss", "alt_hit", None, "")
    for p in reversed(verified):
        is_win = p.get("result") not in ("miss", "alt_hit", None, "")
        if is_win == first_win: streak += 1 if first_win else -1
        else: break

    total_invested = sum(float(p.get("amount", 0) or 0) for p in verified)
    total_won      = sum(float(p.get("payout", 0) or 0) for p in verified)
    roi = round((total_won - total_invested) / total_invested * 100, 1) if total_invested > 0 else 0.0

    return {
        "total_picks":    len(picks),
        "verified_picks": len(verified),
        "hits":           main_hits,
        "alt_hits":       alt_hits,
        "total_hits":     total_hits,
        "hit_rate":       hit_rate,
        "main_hit_rate":  main_hit_rate,
        "alt_hit_rate":   alt_hit_rate,
        "streak":         streak,
        "roi":            roi,
        "total_invested": total_invested,
        "total_won":      total_won,
    }
