"""
CLAUDE L-NACIONAL — Generador de Picks v2.3
==========================================
Flujo:
  1. Carga historial desde data/history.xlsx
  2. Verifica/actualiza si hay resultados nuevos
  3. Verifica TODOS los picks pendientes atrasados → actualiza performance
     → envía mensaje de Telegram por cada uno que se verifica
  4. Guarda performance actualizado en CSV
  5. Corre los 12 métodos + mejoras (engine.py v2.1)
  6. Genera picks para el próximo sorteo
  7. Guarda pick en JSON + CSV
  8. Envía mensaje a Telegram

CHANGELOG v2.1:
  - auto_verify_last_pick() renombrada a auto_verify_pending_picks().
    ANTES: solo tomaba el pick pendiente MÁS RECIENTE y lo verificaba
    contra el sorteo más reciente. AHORA: recorre TODOS los pendientes,
    cada uno verificado contra el sorteo real de SU PROPIA fecha.

CHANGELOG v2.2:
  - Eliminada run_full_analysis_from_draws() (parche de get_draws).
    engine.py v2.1 lee directo de history.xlsx vía loader.load_history().

CHANGELOG v2.3:
  - auto_verify_pending_picks() ahora envía send_verification_message()
    a Telegram por CADA pick que se verifica en el run. ANTES: la
    verificación solo se imprimía en el log del workflow — nunca se
    notificaba, ni en aciertos ni en misses. Respeta --no-telegram.
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
from telegram_bot import send_picks, build_picks_message, send_verification_message

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


def _verify_one(pick: dict, real_draw: dict) -> tuple:
    """Compute verification fields for a single pick against its real draw. Returns the updated pick dict (does not mutate input)."""
    real_nums = [real_draw["p1"], real_draw["p2"], real_draw["p3"]]

    main_picks = [pick["p1"], pick["p2"], pick["p3"]]
    top5_snap  = pick.get("snapshot", {}).get("top5", [])
    alt_picks  = [n for n in top5_snap if n not in main_picks][:2]  # 4th and 5th
    all_picks  = main_picks + alt_picks

    any_match = [n for n in main_picks if n in real_nums]
    result = "miss"
    payout = 0.0
    amt    = float(pick.get("amount") or 0)

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

    alt_hit = False
    alt_hit_num = ""
    alt_hit_rank = None  # 4 or 5, which alternate slot hit (for position tracking)
    if result == "miss" and alt_picks:
        for i, alt in enumerate(alt_picks):
            if alt in real_nums:
                alt_hit = True
                alt_hit_num = alt
                alt_hit_rank = 4 + i  # alt_picks[0] is rank 4, alt_picks[1] is rank 5
                result = "alt_hit"
                break

    updated = dict(pick)
    updated.update({
        "status":       "verified",
        "result":       result,
        "payout":       payout,
        "real_p1":      real_nums[0],
        "real_p2":      real_nums[1],
        "real_p3":      real_nums[2],
        "all_picks":    all_picks,
        "alt_hit":      alt_hit,
        "alt_hit_num":  alt_hit_num,
        "alt_hit_rank": alt_hit_rank,
        "verified_at":  datetime.datetime.now().isoformat(),
    })
    return updated, result, main_picks, alt_picks, real_nums


def auto_verify_pending_picks(lottery: str, draws: list[dict], no_telegram: bool = False) -> None:
    """
    Verify ALL pending picks for this lottery, each against the real draw
    matching ITS OWN date. Picks whose date has no matching draw yet are
    left pending (e.g. a day with no sorteo — see position_report.py notes).

    v2.3: sends a Telegram verification message for each pick verified in
    this run (using a fresh performance snapshot), unless no_telegram.
    """
    picks = load_picks()
    pending = [p for p in picks if p.get("lottery") == lottery and p.get("status") == "pending"]
    if not pending or not draws:
        return

    draws_by_date = {d["date"]: d for d in draws}
    picks_by_id   = {p["id"]: p for p in picks}
    newly_verified = []

    for pend in sorted(pending, key=lambda x: x.get("date", "")):
        real_draw = draws_by_date.get(pend.get("date", ""))
        if real_draw is None:
            continue

        updated, result, main_picks, alt_picks, real_nums = _verify_one(pend, real_draw)
        picks_by_id[updated["id"]] = updated
        newly_verified.append(updated)

        result_label = {
            "miss":     "❌ MISS",
            "1ra":      "🥇 1RA",
            "2da":      "🥈 2DA",
            "3ra":      "🥉 3RA",
            "pale":     "💜 PALÉ",
            "tripleta": "🟢 TRIPLETA",
            "alt_hit":  f"🔵 ALTERNATIVO ({updated['alt_hit_num']})",
        }.get(result, result)

        print(f"  🔍 {pend['date']} verificado: {result_label}")
        print(f"     Main: {main_picks[0]}-{main_picks[1]}-{main_picks[2]} | Alts: {alt_picks} | Real: {real_nums[0]}-{real_nums[1]}-{real_nums[2]}")

    if not newly_verified:
        print("  ℹ️  Sin picks pendientes con sorteo real disponible aún.")
        return

    save_json(PICKS_FILE, {"picks": list(picks_by_id.values())})
    print(f"  ✅ {len(newly_verified)} pick(s) verificado(s) en este run.")

    if not no_telegram:
        # Fresh performance snapshot so the verification messages reflect
        # the just-updated results, not stale numbers from before this run.
        fresh_perf = calc_performance(lottery)
        for updated in newly_verified:
            sent = send_verification_message(updated, fresh_perf)
            if sent:
                print(f"  📤 Telegram: verificación de {updated['date']} enviada")
            else:
                print(f"  ⚠️  Telegram: no se pudo enviar verificación de {updated['date']}")


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lottery", required=True, choices=["Gana Más", "Nacional Noche"])
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--force", action="store_true", help="Forzar pick aunque ya exista uno hoy")
    parser.add_argument("--reset-today", action="store_true", help="Borra el pick de hoy y regenera desde cero")
    args = parser.parse_args()

    print(f"\n🚀 CLAUDE L-NACIONAL v2 — {args.lottery}")
    print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ── 1. Sync CSV from JSON (in case of discrepancies) ─────────────────────
    synced = sync_csv_from_json()
    print(f"  📋 CSV sincronizado: {synced} picks\n")

    # ── 2. Reset today's pick if requested ───────────────────────────────────
    if args.reset_today:
        picks  = load_picks()
        today  = datetime.date.today().isoformat()
        before = len(picks)
        picks  = [p for p in picks if not (p.get("lottery") == args.lottery and p.get("date") == today)]
        if len(picks) < before:
            save_json(PICKS_FILE, {"picks": picks})
            print(f"  🗑️  Pick de hoy eliminado ({before - len(picks)} registros). Regenerando...")
        else:
            print(f"  ℹ️  No había pick de hoy para eliminar.")

    # ── 3. Check if already picked today ─────────────────────────────────────
    if already_picked_today(args.lottery):
        if args.force:
            print(f"  📤 Pick de hoy ya existe. Reenviando a Telegram...")
            picks   = load_picks()
            today   = datetime.date.today().isoformat()
            existing = [p for p in picks if p.get("lottery") == args.lottery and p.get("date") == today]
            if existing:
                pick = sorted(existing, key=lambda x: x.get("id",""))[-1]
                perf = load_performance(args.lottery)
                if not args.no_telegram:
                    ensure_updated(args.lottery)
                    analysis = run_full_analysis(args.lottery)
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

    # ── 4. Ensure history is up to date ──────────────────────────────────────
    print("📂 Verificando historial...")
    draws = ensure_updated(args.lottery)
    if len(draws) < 5:
        print(f"❌ Datos insuficientes: {len(draws)} sorteos")
        sys.exit(1)

    # ── 5. Auto-verify ALL pending picks with matching real results ──────────
    print("🔍 Verificando picks pendientes...")
    auto_verify_pending_picks(args.lottery, draws, no_telegram=args.no_telegram)

    # ── 6. Update performance BEFORE generating new pick ──────────────────────
    print("📊 Actualizando performance...")
    perf = update_performance(args.lottery)
    print(f"   Hit rate: {perf['hit_rate']}% | Racha: {perf['streak']} | ROI: {perf['roi']}%\n")

    # ── 7. Run analysis ────────────────────────────────────────────────────────
    print("🧠 Ejecutando análisis...")
    analysis = run_full_analysis(args.lottery)
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        sys.exit(1)

    print_summary(analysis, perf)

    # ── 8. Save pick ────────────────────────────────────────────────────────────
    pick = save_pick(analysis)
    print(f"💾 Pick guardado (JSON + CSV): {pick['p1']} — {pick['p2']} — {pick['p3']}\n")

    # ── 9. Send Telegram ────────────────────────────────────────────────────────
    if not args.no_telegram:
        send_picks(analysis, perf)
    else:
        print("⏭️  Telegram omitido")
        print(build_picks_message(analysis, perf))

    print("✅ CLAUDE L-NACIONAL v2 — Completado\n")


if __name__ == "__main__":
    main()