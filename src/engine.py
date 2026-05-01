"""
CLAUDE L-NACIONAL — Motor de Análisis Estadístico
==================================================
Métodos implementados:
  1. Rating de Rentabilidad (fórmula dominicana)
  2. Overdue / Gap Analysis
  3. Co-ocurrencia
  4. Sum Analysis
  5. Chi² (scipy.stats)
  6. Mutual Information (sklearn)
  7. Markov Chain (numpy matrices)
  8. Inferencia Bayesiana (Dirichlet-Multinomial)
  9. Monte Carlo Simulation
  +  WMA — Weighted Moving Average (capa transversal)
"""

import json
import math
import random
import datetime
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy import stats
from sklearn.metrics import mutual_info_score

# ── Constants ────────────────────────────────────────────────────────────────
ALL_NUMS   = [str(i).zfill(2) for i in range(100)]
NUM_IDX    = {n: i for i, n in enumerate(ALL_NUMS)}
DATA_DIR   = Path(__file__).parent.parent / "data"
HALF_LIFE  = 30   # WMA decay parameter (in draws)

# Method weights — must sum to 1.0
WEIGHTS = {
    "rating":   0.15,
    "overdue":  0.10,
    "cooccur":  0.10,
    "sum":      0.05,
    "chi2":     0.15,
    "mi":       0.15,
    "markov":   0.15,
    "bayes":    0.10,
    "monte":    0.05,
}

PRIZE_MULTIPLIERS = {
    "tripleta": 20000,
    "pale":     1000,
    "1ra":      60,
    "2da":      8,
    "3ra":      5,
    "miss":     0,
}


# ── Data I/O ──────────────────────────────────────────────────────────────────
def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


class _NumpyEncoder(json.JSONEncoder):
    """Converts numpy types to native Python types before JSON serialization."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, cls=_NumpyEncoder), encoding="utf-8")


def get_draws(lottery: str) -> list[dict]:
    """Return sorted draws for a specific lottery."""
    data = load_json(DATA_DIR / "history.json")
    draws = [d for d in data.get("history", []) if d["lottery"] == lottery]
    return sorted(draws, key=lambda x: x["date"])


# ── WMA weight ────────────────────────────────────────────────────────────────
def wma_weight(idx: int, total: int, half_life: float = HALF_LIFE) -> float:
    """Exponential decay: most recent draw (idx=total-1) has weight≈1."""
    age = (total - 1) - idx
    return math.exp(-age / half_life)


# ── Method 1: Rating de Rentabilidad ─────────────────────────────────────────
def calc_rating_rd(draws: list[dict]) -> dict[str, float]:
    """
    Dominican formula:
      1ra position → +60 pts
      2da position → +8 pts
      3ra position → +4 pts
      absent       → -1 pt
    WMA-weighted so recent draws matter more.
    """
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


# ── Method 2: Overdue / Gap Analysis ─────────────────────────────────────────
def calc_overdue(draws: list[dict]) -> dict[str, int]:
    """Number of draws since each number last appeared."""
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
def calc_cooccurrence(draws: list[dict]) -> dict[str, dict[str, float]]:
    """
    Transition probability: given numbers in draw N,
    what numbers tend to appear in draw N+1?
    Returns normalized probability table.
    """
    co: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i in range(len(draws) - 1):
        cur = [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]
        nxt = [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]]
        for c in cur:
            for n in nxt:
                co[c][n] += 1
    # Normalize
    result = {}
    for src, targets in co.items():
        total = sum(targets.values())
        result[src] = {tgt: cnt/total for tgt, cnt in targets.items()}
    return result


def cooccur_scores_for_last(draws: list[dict], co: dict) -> dict[str, float]:
    """Score each number based on co-occurrence with last draw."""
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
    """Analyze historical sum distributions (p1+p2+p3)."""
    sums = [int(d["p1"]) + int(d["p2"]) + int(d["p3"]) for d in draws]
    if not sums:
        return {"mean": 99, "std": 30, "low": 69, "high": 129}
    mean = float(np.mean(sums))
    std  = float(np.std(sums))
    return {
        "mean": mean,
        "std":  std,
        "low":  mean - std,
        "high": mean + std,
        "p10":  float(np.percentile(sums, 10)),
        "p90":  float(np.percentile(sums, 90)),
    }


def sum_score(num: str, candidates: list[str], profile: dict) -> float:
    """1.0 if num keeps trio sum in historical range, 0.2 otherwise."""
    base = sum(int(c) for c in candidates[:2]) if len(candidates) >= 2 else 99
    total = base + int(num)
    in_range = profile["low"] <= total <= profile["high"]
    return 1.0 if in_range else 0.2


# ── Method 5: Chi-Squared ─────────────────────────────────────────────────────
def calc_chi2(draws: list[dict]) -> dict:
    """
    scipy.stats.chisquare: tests whether observed frequencies differ
    significantly from uniform (expected = total/100).
    """
    freq = defaultdict(int)
    for d in draws:
        freq[d["p1"]] += 1
        freq[d["p2"]] += 1
        freq[d["p3"]] += 1

    observed  = np.array([freq.get(n, 0) for n in ALL_NUMS], dtype=float)
    total_obs = observed.sum()
    expected  = np.full(100, total_obs / 100)

    chi2_stat, p_value = stats.chisquare(observed, f_exp=expected)
    # Per-number chi² contribution
    per_num_chi2 = ((observed - expected) ** 2) / expected

    return {
        "freq":         {n: int(freq.get(n, 0)) for n in ALL_NUMS},
        "chi2_scores":  {n: float(per_num_chi2[i]) for i, n in enumerate(ALL_NUMS)},
        "chi2_stat":    float(chi2_stat),
        "p_value":      float(p_value),
        "significant":  p_value < 0.05,
    }


# ── Method 6: Mutual Information ─────────────────────────────────────────────
def calc_mutual_info(draws: list[dict]) -> dict:
    """
    sklearn mutual_info_score: measures statistical dependence between
    consecutive draw numbers (draw N → draw N+1).
    """
    if len(draws) < 10:
        return {"mi_scores": {n: 0.0 for n in ALL_NUMS}, "mi_level": "Insuficiente", "avg_mi": 0.0}

    # Build label arrays for consecutive pairs
    cur_labels, nxt_labels = [], []
    for i in range(len(draws) - 1):
        for c in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            for n in [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]]:
                cur_labels.append(NUM_IDX[c])
                nxt_labels.append(NUM_IDX[n])

    mi_global = mutual_info_score(cur_labels, nxt_labels)

    # Per-target MI: how much knowing last draw tells us about each number
    mi_scores = {}
    last = draws[-1]
    last_nums = [last["p1"], last["p2"], last["p3"]]

    for tgt in ALL_NUMS:
        score = 0.0
        for src in last_nums:
            # Build binary arrays: did src appear → did tgt appear next?
            y_src, y_tgt = [], []
            for i in range(len(draws) - 1):
                appeared_src = int(src in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]])
                appeared_tgt = int(tgt in [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]])
                y_src.append(appeared_src)
                y_tgt.append(appeared_tgt)
            if len(set(y_src)) > 1 and len(set(y_tgt)) > 1:
                score += mutual_info_score(y_src, y_tgt)
        mi_scores[tgt] = score / len(last_nums)

    avg_mi = float(np.mean(list(mi_scores.values())))
    mi_level = "Alta" if avg_mi > 0.05 else "Media" if avg_mi > 0.02 else "Baja"

    return {"mi_scores": mi_scores, "mi_level": mi_level, "avg_mi": avg_mi, "mi_global": float(mi_global)}


# ── Method 7: Markov Chain ────────────────────────────────────────────────────
def calc_markov(draws: list[dict]) -> dict:
    """
    Build 1-step and 2-step transition matrices using numpy.
    Superpose both for better signal.
    """
    n = 100
    T1 = np.zeros((n, n))  # 1-step
    T2 = np.zeros((n, n))  # 2-step

    for i in range(len(draws) - 1):
        for src in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            for tgt in [draws[i+1]["p1"], draws[i+1]["p2"], draws[i+1]["p3"]]:
                T1[NUM_IDX[src], NUM_IDX[tgt]] += 1

    for i in range(len(draws) - 2):
        for src in [draws[i]["p1"], draws[i]["p2"], draws[i]["p3"]]:
            for tgt in [draws[i+2]["p1"], draws[i+2]["p2"], draws[i+2]["p3"]]:
                T2[NUM_IDX[src], NUM_IDX[tgt]] += 1

    # Row-normalize (avoid div by zero)
    def row_norm(M):
        row_sums = M.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        return M / row_sums

    P1 = row_norm(T1)
    P2 = row_norm(T2)
    P  = (P1 + P2) / 2  # Superposition

    # Score each target using last draw as source state
    if not draws:
        return {"markov_scores": {n: 0.0 for n in ALL_NUMS}, "confidence": 0}

    last = draws[-1]
    last_idx = [NUM_IDX[last["p1"]], NUM_IDX[last["p2"]], NUM_IDX[last["p3"]]]
    combined = P[last_idx, :].mean(axis=0)  # average over 3 source states

    markov_scores = {ALL_NUMS[i]: float(combined[i]) for i in range(100)}
    max_score = max(markov_scores.values()) if markov_scores else 1
    confidence = min(int(max_score * 1000), 99)

    return {"markov_scores": markov_scores, "confidence": confidence}


# ── Method 8: Bayesian Inference (Dirichlet-Multinomial) ──────────────────────
def calc_bayesian(draws: list[dict]) -> dict[str, float]:
    """
    Dirichlet-Multinomial: uniform prior α=1 updated with WMA-weighted observations.
    Returns posterior mean probability for each number.
    """
    alpha = {n: 1.0 for n in ALL_NUMS}  # uniform Dirichlet prior
    n = len(draws)
    for idx, d in enumerate(draws):
        w = wma_weight(idx, n)
        alpha[d["p1"]] += w
        alpha[d["p2"]] += w
        alpha[d["p3"]] += w

    total_alpha = sum(alpha.values())
    return {num: alpha[num] / total_alpha for num in ALL_NUMS}


# ── Method 9: Monte Carlo Simulation ──────────────────────────────────────────
def calc_monte_carlo(draws: list[dict], iterations: int = 10_000) -> dict[str, float]:
    """
    Sample 10k virtual draws using WMA-weighted empirical distribution.
    Returns frequency of each number across all simulations.
    """
    if len(draws) < 5:
        return {n: 1/100 for n in ALL_NUMS}

    # Build weighted frequency table
    freq = defaultdict(float)
    for n in ALL_NUMS:
        freq[n] = 1.0  # Laplace smoothing

    total_w = len(draws)
    for idx, d in enumerate(draws):
        w = wma_weight(idx, total_w)
        freq[d["p1"]] += w
        freq[d["p2"]] += w
        freq[d["p3"]] += w

    nums  = ALL_NUMS
    probs = np.array([freq[n] for n in nums], dtype=float)
    probs /= probs.sum()

    # Monte Carlo sampling
    sim_count = defaultdict(int)
    rng = np.random.default_rng(seed=42)
    samples = rng.choice(nums, size=iterations * 3, p=probs)
    for s in samples:
        sim_count[s] += 1

    total_sim = iterations * 3
    return {n: sim_count[n] / total_sim for n in ALL_NUMS}


# ── Normalize helper ───────────────────────────────────────────────────────────
def normalize(scores: dict[str, float]) -> dict[str, float]:
    vals = list(scores.values())
    mn, mx = min(vals), max(vals)
    rng = mx - mn or 1e-9
    return {k: (v - mn) / rng for k, v in scores.items()}


# ── Full Analysis Pipeline ────────────────────────────────────────────────────
def run_full_analysis(lottery: str) -> dict:
    """
    Run all 9 methods + WMA on the historical data for a given lottery.
    Returns ranked picks with composite scores and full diagnostics.
    """
    draws = get_draws(lottery)
    if len(draws) < 5:
        return {"error": f"Insuficientes datos: {len(draws)} sorteos (mínimo 5)"}

    print(f"  Analizando {len(draws)} sorteos de {lottery}...")

    # ── Run methods ──────────────────────────────────────────────────────────
    print("  [1/9] Rating de Rentabilidad...")
    rating     = calc_rating_rd(draws)

    print("  [2/9] Overdue / Gap Analysis...")
    overdue    = calc_overdue(draws)

    print("  [3/9] Co-ocurrencia...")
    co         = calc_cooccurrence(draws)
    co_scores  = cooccur_scores_for_last(draws, co)

    print("  [4/9] Sum Analysis...")
    sum_prof   = calc_sum_profile(draws)

    print("  [5/9] Chi² (scipy)...")
    chi2       = calc_chi2(draws)

    print("  [6/9] Mutual Information (sklearn)...")
    mi         = calc_mutual_info(draws)

    print("  [7/9] Markov Chain (numpy)...")
    markov     = calc_markov(draws)

    print("  [8/9] Inferencia Bayesiana...")
    bayes      = calc_bayesian(draws)

    print("  [9/9] Monte Carlo (10k iteraciones)...")
    monte      = calc_monte_carlo(draws)

    # ── Normalize all scores ─────────────────────────────────────────────────
    n_rating  = normalize(rating)
    n_overdue = normalize(overdue)
    n_co      = normalize(co_scores)
    n_chi2    = normalize(chi2["chi2_scores"])
    n_mi      = normalize(mi["mi_scores"])
    n_markov  = normalize(markov["markov_scores"])
    n_bayes   = normalize(bayes)
    n_monte   = normalize(monte)

    # Sum scores: need top-2 markov candidates as context
    top2_markov = sorted(markov["markov_scores"], key=lambda x: markov["markov_scores"][x], reverse=True)[:2]
    n_sum = {num: sum_score(num, top2_markov, sum_prof) for num in ALL_NUMS}
    n_sum = normalize(n_sum)

    # ── Composite score ───────────────────────────────────────────────────────
    composite = {}
    for num in ALL_NUMS:
        composite[num] = (
            WEIGHTS["rating"]  * n_rating.get(num, 0)  +
            WEIGHTS["overdue"] * n_overdue.get(num, 0) +
            WEIGHTS["cooccur"] * n_co.get(num, 0)      +
            WEIGHTS["sum"]     * n_sum.get(num, 0)     +
            WEIGHTS["chi2"]    * n_chi2.get(num, 0)    +
            WEIGHTS["mi"]      * n_mi.get(num, 0)      +
            WEIGHTS["markov"]  * n_markov.get(num, 0)  +
            WEIGHTS["bayes"]   * n_bayes.get(num, 0)   +
            WEIGHTS["monte"]   * n_monte.get(num, 0)
        )

    # ── Rank ──────────────────────────────────────────────────────────────────
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
        })

    # Hot / Cold / Overdue
    freq_sorted = sorted(chi2["freq"].items(), key=lambda x: x[1], reverse=True)
    hot         = [{"num": n, "count": c} for n, c in freq_sorted[:10]]
    cold        = [{"num": n, "count": c} for n, c in freq_sorted[-10:]]
    overdue_top = sorted(overdue.items(), key=lambda x: x[1], reverse=True)[:10]
    overdue_top = [{"num": n, "gap": g} for n, g in overdue_top]

    return {
        "lottery":          lottery,
        "analyzed_at":      datetime.datetime.now().isoformat(),
        "total_draws":      len(draws),
        "picks":            picks,
        "hot":              hot,
        "cold":             cold,
        "overdue_top":      overdue_top,
        "sum_profile":      sum_prof,
        "chi2_stat":        chi2["chi2_stat"],
        "chi2_pvalue":      chi2["p_value"],
        "chi2_significant": chi2["significant"],
        "mi_level":         mi["mi_level"],
        "mi_avg":           mi["avg_mi"],
        "markov_confidence": markov["confidence"],
        "last_draw":        draws[-1] if draws else None,
    }


# ── Performance Calculator ─────────────────────────────────────────────────────
def calc_performance(lottery: str | None = None) -> dict:
    data  = load_json(DATA_DIR / "picks_log.json")
    picks = data.get("picks", [])
    if lottery:
        picks = [p for p in picks if p.get("lottery") == lottery]

    verified = [p for p in picks if p.get("status") == "verified"]
    if not verified:
        return {
            "total_picks": 0, "verified_picks": 0, "hits": 0,
            "hit_rate": 0.0, "streak": 0, "roi": 0.0,
            "total_invested": 0.0, "total_won": 0.0
        }

    recent30  = verified[-30:]
    hits      = sum(1 for p in recent30 if p.get("result") != "miss")
    hit_rate  = round(hits / len(recent30) * 100, 1) if recent30 else 0.0

    # Streak
    streak = 0
    first_win = verified[-1].get("result") != "miss" if verified else False
    for p in reversed(verified):
        is_win = p.get("result") != "miss"
        if is_win == first_win:
            streak += 1 if first_win else -1
        else:
            break

    total_invested = sum(float(p.get("amount", 0)) for p in verified)
    total_won      = sum(float(p.get("payout", 0)) for p in verified)
    roi = round((total_won - total_invested) / total_invested * 100, 1) if total_invested > 0 else 0.0

    return {
        "total_picks":    len(picks),
        "verified_picks": len(verified),
        "hits":           hits,
        "hit_rate":       hit_rate,
        "streak":         streak,
        "roi":            roi,
        "total_invested": total_invested,
        "total_won":      total_won,
    }
