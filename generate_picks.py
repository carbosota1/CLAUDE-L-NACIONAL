"""
CLAUDE L-NACIONAL — Generador de Picks
=======================================
Script principal. Hace todo en orden:

  1. Carga el historial desde data/history.xlsx
  2. Verifica si está actualizado (última fecha vs hoy)
  3. Si no está actualizado → scrapes resultados faltantes → los agrega al Excel
  4. Corre los 9 métodos de análisis + WMA
  5. Genera los picks para el próximo sorteo
  6. Guarda el pick en data/picks_log.json
  7. Envía el mensaje a Telegram

Uso:
  python generate_picks.py --lottery "Gana Más"
  python generate_picks.py --lottery "Nacional Noche"
  python generate_picks.py --lottery "Gana Más" --no-telegram
"""

import sys
import json
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from loader import ensure_updated, load_history
from engine import run_full_analysis, calc_performance, save_json, DATA_DIR
from telegram_bot import send_picks, build_picks_message

PICKS_FILE = DATA_DIR / "picks_log.json"
PERF_FILE  = DATA_DIR / "performance.json"


def load_picks() -> list:
    if PICKS_FILE.exists():
        return json.loads(PICKS_FILE.read_text(encoding="utf-8")).get("picks", [])
    return []


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
            "chi2_significant":  analysis["chi2_significant"],
            "mi_level":          analysis["mi_level"],
            "markov_confidence": analysis["markov_confidence"],
            "top5":              [p["num"] for p in analysis["picks"][:5]],
        },
    }
    picks.append(pick)
    save_json(PICKS_FILE, {"picks": picks})
    return pick


def load_performance(lottery: str) -> dict:
    if not PERF_FILE.exists():
        return {"hit_rate": 0, "streak": 0, "roi": 0.0}
    data = json.loads(PERF_FILE.read_text(encoding="utf-8"))
    return data.get("by_lottery", {}).get(lottery, {"hit_rate": 0, "streak": 0, "roi": 0.0})


def print_summary(analysis: dict) -> None:
    print("\n" + "="*52)
    print(f"  CLAUDE L-NACIONAL — {analysis['lottery']}")
    print("="*52)
    print(f"  Sorteos analizados:  {analysis['total_draws']}")
    print(f"  Último sorteo:       {analysis['last_draw']['date']} "
          f"→ {analysis['last_draw']['p1']}-{analysis['last_draw']['p2']}-{analysis['last_draw']['p3']}")
    print(f"  Chi² significativo:  {analysis['chi2_significant']} (p={analysis['chi2_pvalue']:.4f})")
    print(f"  MI correlación:      {analysis['mi_level']}")
    print(f"  Markov confidence:   {analysis['markov_confidence']}%")
    print()
    print("  TOP 5 PICKS:")
    for p in analysis["picks"][:5]:
        bar = "█" * int(p["composite_score"] / 5)
        print(f"    #{p['rank']} → {p['num']}  [{bar:<20}] {p['composite_score']}/100  overdue:{p['overdue_gap']}")
    print()
    print(f"  🔥 HOT:     {[h['num'] for h in analysis['hot'][:5]]}")
    print(f"  ❄️  COLD:    {[c['num'] for c in analysis['cold'][:5]]}")
    print(f"  ⏳ OVERDUE: {[o['num'] for o in analysis['overdue_top'][:5]]}")
    print("="*52 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CLAUDE L-NACIONAL — Generador de Picks")
    parser.add_argument("--lottery", required=True,
                        choices=["Gana Más", "Nacional Noche"],
                        help="Lotería a analizar")
    parser.add_argument("--no-telegram", action="store_true",
                        help="Omitir envío a Telegram")
    args = parser.parse_args()

    print(f"\n🚀 CLAUDE L-NACIONAL — {args.lottery}")
    print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # ── Step 1: Ensure history is up to date ─────────────────────────────────
    print("📂 Verificando historial...")
    draws = ensure_updated(args.lottery)

    if len(draws) < 5:
        print(f"❌ Datos insuficientes: {len(draws)} sorteos")
        sys.exit(1)

    print(f"   {len(draws)} sorteos disponibles\n")

    # ── Step 2: Run full analysis ─────────────────────────────────────────────
    print("🧠 Ejecutando análisis (9 métodos + WMA)...")
    analysis = run_full_analysis_from_draws(draws, args.lottery)

    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        sys.exit(1)

    print_summary(analysis)

    # ── Step 3: Save pick ─────────────────────────────────────────────────────
    pick = save_pick(analysis)
    print(f"💾 Pick guardado: {pick['p1']} — {pick['p2']} — {pick['p3']}\n")

    # ── Step 4: Load performance ──────────────────────────────────────────────
    perf = load_performance(args.lottery)

    # ── Step 5: Send Telegram ─────────────────────────────────────────────────
    if not args.no_telegram:
        send_picks(analysis, perf)
    else:
        print("⏭️  Telegram omitido")
        msg = build_picks_message(analysis, perf)
        print("\n--- MENSAJE QUE SE ENVIARÍA ---")
        print(msg)
        print("--- FIN DEL MENSAJE ---\n")

    print("✅ CLAUDE L-NACIONAL — Completado\n")


# ── Bridge: adapt draw list to engine's run_full_analysis ────────────────────
def run_full_analysis_from_draws(draws: list[dict], lottery: str) -> dict:
    """
    run_full_analysis expects draws from get_draws() which reads JSON.
    This function passes the draws list directly.
    Temporarily patches the engine's get_draws function.
    """
    import engine as eng

    # Monkey-patch get_draws to return our pre-loaded draws
    original = eng.get_draws
    eng.get_draws = lambda lot: draws
    result = eng.run_full_analysis(lottery)
    eng.get_draws = original
    return result


if __name__ == "__main__":
    main()
