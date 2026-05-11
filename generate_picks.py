"""
CLAUDE L-NACIONAL — Generador de Picks v2
==========================================
Flujo:
  1. Carga historial desde data/history.xlsx
  2. Verifica/actualiza si hay resultados nuevos
  3. Verifica resultado del pick anterior → actualiza performance
  4. Guarda performance actualizado en CSV
  5. Corre los 9 métodos + mejoras
  6. Genera picks para el próximo sorteo
  7. Guarda pick en JSON + CSV
  8. Envía mensaje a Telegram
"""

import sys
import json
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from loader import ensure_updated
from engine import run_full_analysis, calc_performance, save_json, DATA_DIR
from tracker import save_pick_to_csv, save_performance_to_csv, sync_csv_from_json
from telegram_bot import send_picks, build_picks_message

PICKS_FILE = DATA_DIR / "picks_log.json"
PERF_FILE  = DATA_DIR / "performance.json"


# ── Picks I/O ─────────────────────────────────────────────────────────────────
def load_picks() -> list:
    if PICKS_FILE.exists():
        return json.loads(PICKS_FILE.read_text(encoding="utf-8")).get("picks", [])
    return []


def already_picked_today(lottery: str) -> bool:
    """Return True if a pick was already generated today for this lottery."""
    today = datetime.date.today().isoformat()
    for p in load_picks():
        if p.get("lottery") == lottery and p.get("date") == today:
            return True
    return False


def auto_verify_last_pick(lottery: str, draws: list[dict]) -> None:
    """
    Verify the most recent pending pick using the latest real result.
    Checks top 5 picks (p1-p5) against real result in any position.
    """
    picks = load_picks()
    pending = [p for p in picks if p.get("lottery") == lottery and p.get("status") == "pending"]
    if not pending or not draws:
        return

    last_pick = sorted(pending, key=lambda x: x.get("id", ""))[-1]
    last_real = draws[-1]

    # Only verify if real result date >= pick date
    if last_real["date"] < last_pick.get("date", ""):
        return

    real_nums = [last_real["p1"], last_real["p2"], last_real["p3"]]

    # Build full candidate list: p1, p2, p3 + alternates from snapshot
    main_picks  = [last_pick["p1"], last_pick["p2"], last_pick["p3"]]
    top5_snap   = last_pick.get("snapshot", {}).get("top5", [])
    alt_picks   = [n for n in top5_snap if n not in main_picks][:2]  # 4th and 5th
    all_picks   = main_picks + alt_picks  # up to 5 numbers

    # Check main picks first (paid positions)
    any_match = [n for n in main_picks if n in real_nums]
    result = "miss"
    payout = 0.0
    amt    = float(last_pick.get("amount") or 0)

    if len(any_match) == 3:
        result = "tripleta"; payout = amt * 20000
    elif len(any_match) >= 2:
        result = "pale";     payout = amt * 1000
    elif main_picks[0] == real_nums[0]:
        result = "1ra";      payout = amt * 60
    elif main_picks[1] == real_nums[1]:
        result = "2da";      payout = amt * 8
    elif main_picks[2] == real_nums[2]:
        result = "3ra";      payout = amt * 5

    # Check alternates — no payout but register as "alt_hit" for tracking
    alt_hit = False
    alt_hit_num = ""
    if result == "miss" and alt_picks:
        for alt in alt_picks:
            if alt in real_nums:
                alt_hit = True
                alt_hit_num = alt
                result = "alt_hit"
                break

    # Update JSON
    updated = []
    for p in picks:
        if p["id"] == last_pick["id"]:
            p.update({
                "status":     "verified",
                "result":     result,
                "payout":     payout,
                "real_p1":    real_nums[0],
                "real_p2":    real_nums[1],
                "real_p3":    real_nums[2],
                "all_picks":  all_picks,
                "alt_hit":    alt_hit,
                "alt_hit_num": alt_hit_num,
                "verified_at": datetime.datetime.now().isoformat(),
            })
        updated.append(p)
    save_json(PICKS_FILE, {"picks": updated})

    result_label = {
        "miss":     "❌ MISS",
        "1ra":      "🥇 1RA",
        "2da":      "🥈 2DA",
        "3ra":      "🥉 3RA",
        "pale":     "💜 PALÉ",
        "tripleta": "🟢 TRIPLETA",
        "alt_hit":  f"🔵 ALTERNATIVO ({alt_hit_num})",
    }.get(result, result)

    print(f"  🔍 Pick anterior verificado: {result_label}")
    print(f"     Main: {main_picks[0]}-{main_picks[1]}-{main_picks[2]} | Alts: {alt_picks} | Real: {real_nums[0]}-{real_nums[1]}-{real_nums[2]}")


def save_pick(analysis: dict) -> dict:
    picks = load_picks()
    top3  = analysis["picks"][:3]
    pick  = {
        "id":      f"p_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "date":    datetime.date.today().isoformat(),
        "lottery": analysis["lottery"],
        "p1":      top3[0]["num"] if len(top3) > 0 else "??",
        "p2":      top3[1]["num"] if len(top3) > 1 else "??",
        "p3":      top3[2]["num"] if len(top3) > 2 else "??",
        "method":  "Sistema",
        "status":  "pending",
        "score":   top3[0]["composite_score"] if top3 else 0,
        "snapshot": {
            "total_draws":       analysis["total_draws"],
            "recent_draws":      analysis.get("recent_draws", 30),
            "chi2_significant":  analysis["chi2_significant"],
            "mi_level":          analysis["mi_level"],
            "markov_confidence": analysis["markov_confidence"],
            "top5":              [p["num"] for p in analysis["picks"][:5]],
        },
    }
    picks.append(pick)
    save_json(PICKS_FILE, {"picks": picks})
    # Save to CSV too
    save_pick_to_csv(pick)
    return pick


def load_performance(lottery: str) -> dict:
    if not PERF_FILE.exists():
        return {"hit_rate": 0, "streak": 0, "roi": 0.0}
    data = json.loads(PERF_FILE.read_text(encoding="utf-8"))
    return data.get("by_lottery", {}).get(lottery, {"hit_rate": 0, "streak": 0, "roi": 0.0})


def update_performance(lottery: str) -> dict:
    """Recalculate and save performance for this lottery."""
    perf = calc_performance(lottery)
    data = json.loads(PERF_FILE.read_text(encoding="utf-8")) if PERF_FILE.exists() else {}
    data.setdefault("by_lottery", {})[lottery] = perf
    data["last_updated"] = datetime.datetime.now().isoformat()
    save_json(PERF_FILE, data)
    # Save snapshot to CSV
    save_performance_to_csv(lottery, perf)
    return perf


def print_summary(analysis: dict, perf: dict) -> None:
    print("\n" + "="*54)
    print(f"  CLAUDE L-NACIONAL v2 — {analysis['lottery']}")
    print("="*54)
    print(f"  Historial:    {analysis['total_draws']} sorteos ({analysis.get('recent_draws',30)} recientes)")
    print(f"  Último:       {analysis['last_draw']['date']} → {analysis['last_draw']['p1']}-{analysis['last_draw']['p2']}-{analysis['last_draw']['p3']}")
    print(f"  Chi²:         p={analysis['chi2_pvalue']:.4f} {'✅' if analysis['chi2_significant'] else '⚠️'}")
    print(f"  MI:           {analysis['mi_level']}")
    print(f"  Markov:       {analysis['markov_confidence']}% lift")
    print()
    print("  TOP 5 PICKS:")
    for p in analysis["picks"][:5]:
        bar = "█" * int(p["composite_score"] / 5)
        pen = f" [-{p['penalty']}pen]" if p.get("penalty", 0) > 0 else ""
        print(f"    #{p['rank']} → {p['num']}  [{bar:<20}] {p['composite_score']}/100{pen}")
    print()
    print(f"  PERFORMANCE:  Hit rate {perf.get('hit_rate',0)}% | Racha {perf.get('streak',0)} | ROI {perf.get('roi',0)}%")
    print("="*54 + "\n")


def run_full_analysis_from_draws(draws, lottery):
    import engine as eng
    original   = eng.get_draws
    eng.get_draws = lambda lot: draws
    result     = eng.run_full_analysis(lottery)
    eng.get_draws = original
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lottery", required=True, choices=["Gana Más", "Nacional Noche"])
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--force", action="store_true", help="Forzar generación aunque ya exista pick de hoy")
    args = parser.parse_args()

    print(f"\n🚀 CLAUDE L-NACIONAL v2 — {args.lottery}")
    print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ── 1. Sync CSV from JSON (in case of discrepancies) ─────────────────────
    synced = sync_csv_from_json()
    print(f"  📋 CSV sincronizado: {synced} picks\n")

    # ── 2. Check if already picked today ─────────────────────────────────────
    if already_picked_today(args.lottery):
        if args.force:
            # --force: resend existing pick to Telegram, do NOT regenerate
            print(f"  📤 Pick de hoy ya existe. Reenviando a Telegram...")
            picks   = load_picks()
            today   = datetime.date.today().isoformat()
            existing = [p for p in picks if p.get("lottery") == args.lottery and p.get("date") == today]
            if existing:
                pick = sorted(existing, key=lambda x: x.get("id",""))[-1]
                perf = load_performance(args.lottery)
                if not args.no_telegram:
                    # Rebuild analysis shell just for the message
                    draws   = ensure_updated(args.lottery)
                    analysis = run_full_analysis_from_draws(draws, args.lottery)
                    # Override picks with today's existing pick
                    analysis["picks"][0]["num"] = pick["p1"]
                    analysis["picks"][1]["num"] = pick["p2"]
                    analysis["picks"][2]["num"] = pick["p3"]
                    send_picks(analysis, perf)
                    print(f"  ✅ Pick reenviado: {pick['p1']} — {pick['p2']} — {pick['p3']}")
                else:
                    print(f"  ℹ️  Pick de hoy: {pick['p1']} — {pick['p2']} — {pick['p3']}")
            sys.exit(0)
        else:
            print(f"  ⏭️  Ya existe un pick para hoy ({args.lottery}). Usa --force para reenviar a Telegram.")
            sys.exit(0)

    # ── 3. Ensure history is up to date ──────────────────────────────────────
    print("📂 Verificando historial...")
    draws = ensure_updated(args.lottery)
    if len(draws) < 5:
        print(f"❌ Datos insuficientes: {len(draws)} sorteos")
        sys.exit(1)

    # ── 4. Auto-verify last pick with latest real result ─────────────────────
    print("🔍 Verificando pick anterior...")
    auto_verify_last_pick(args.lottery, draws)

    # ── 5. Update performance BEFORE generating new pick ─────────────────────
    print("📊 Actualizando performance...")
    perf = update_performance(args.lottery)
    print(f"   Hit rate: {perf['hit_rate']}% | Racha: {perf['streak']} | ROI: {perf['roi']}%\n")

    # ── 6. Run analysis ───────────────────────────────────────────────────────
    print("🧠 Ejecutando análisis...")
    analysis = run_full_analysis_from_draws(draws, args.lottery)
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        sys.exit(1)

    print_summary(analysis, perf)

    # ── 7. Save pick ──────────────────────────────────────────────────────────
    pick = save_pick(analysis)
    print(f"💾 Pick guardado (JSON + CSV): {pick['p1']} — {pick['p2']} — {pick['p3']}\n")

    # ── 8. Send Telegram ──────────────────────────────────────────────────────
    if not args.no_telegram:
        send_picks(analysis, perf)
    else:
        print("⏭️  Telegram omitido")
        print(build_picks_message(analysis, perf))

    print("✅ CLAUDE L-NACIONAL v2 — Completado\n")


if __name__ == "__main__":
    main()
