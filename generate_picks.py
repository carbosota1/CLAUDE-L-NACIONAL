"""
CLAUDE L-NACIONAL — Generador de Picks
=======================================
Corre el análisis completo, guarda los picks en picks_log.json
y envía el mensaje a Telegram.

Uso:
  python generate_picks.py --lottery "Gana Más"
  python generate_picks.py --lottery "Nacional Noche"
"""

import sys
import json
import argparse
import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine import run_full_analysis, calc_performance, load_json, save_json, DATA_DIR
from telegram_bot import send_picks

PICKS_FILE = DATA_DIR / "picks_log.json"


def save_pick(analysis: dict) -> dict:
    """Save generated picks to picks_log.json."""
    data  = load_json(PICKS_FILE)
    picks = data.get("picks", [])

    top3  = analysis["picks"][:3]
    today = datetime.date.today().isoformat()

    pick = {
        "id":       f"p_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "date":     today,
        "lottery":  analysis["lottery"],
        "p1":       top3[0]["num"] if len(top3) > 0 else "??",
        "p2":       top3[1]["num"] if len(top3) > 1 else "??",
        "p3":       top3[2]["num"] if len(top3) > 2 else "??",
        "method":   "Sistema",
        "status":   "pending",
        "score":    top3[0]["composite_score"] if top3 else 0,
        "amount":   "",
        "analysis_snapshot": {
            "total_draws":      analysis["total_draws"],
            "chi2_significant": analysis["chi2_significant"],
            "mi_level":         analysis["mi_level"],
            "markov_confidence": analysis["markov_confidence"],
            "top5":             [p["num"] for p in analysis["picks"][:5]],
        }
    }

    picks.append(pick)
    data["picks"] = picks
    save_json(PICKS_FILE, data)
    print(f"✅ Pick guardado: {pick['p1']} — {pick['p2']} — {pick['p3']}")
    return pick


def print_analysis_summary(analysis: dict) -> None:
    """Print a readable summary to GitHub Actions logs."""
    print("\n" + "="*50)
    print(f"  CLAUDE L-NACIONAL — {analysis['lottery']}")
    print("="*50)
    print(f"  Sorteos analizados: {analysis['total_draws']}")
    print(f"  Chi² significativo: {analysis['chi2_significant']} (p={analysis['chi2_pvalue']:.4f})")
    print(f"  MI correlación:     {analysis['mi_level']}")
    print(f"  Markov confidence:  {analysis['markov_confidence']}%")
    print()
    print("  TOP 5 PICKS:")
    for p in analysis["picks"][:5]:
        print(f"    #{p['rank']} → {p['num']}  (score: {p['composite_score']}/100  |  overdue: {p['overdue_gap']})")
    print()
    print("  HOT:", [h["num"] for h in analysis["hot"][:5]])
    print("  COLD:", [c["num"] for c in analysis["cold"][:5]])
    print("  OVERDUE:", [o["num"] for o in analysis["overdue_top"][:5]])
    print("="*50 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CLAUDE L-NACIONAL — Generador de Picks")
    parser.add_argument("--lottery", required=True, choices=["Gana Más", "Nacional Noche"],
                        help="Lotería a analizar")
    parser.add_argument("--no-telegram", action="store_true",
                        help="Omitir envío de Telegram")
    args = parser.parse_args()

    print(f"\n🚀 CLAUDE L-NACIONAL — Iniciando análisis para: {args.lottery}")

    # Run full analysis
    analysis = run_full_analysis(args.lottery)
    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        sys.exit(1)

    # Print summary to logs
    print_analysis_summary(analysis)

    # Save pick
    save_pick(analysis)

    # Get performance stats
    performance = calc_performance(args.lottery)
    print(f"  Hit rate: {performance['hit_rate']}%  |  Racha: {performance['streak']}  |  ROI: {performance['roi']}%")

    # Send to Telegram
    if not args.no_telegram:
        send_picks(analysis, performance)
    else:
        print("⏭️  Telegram omitido (--no-telegram)")

    print("\n✅ CLAUDE L-NACIONAL — Análisis completado\n")


if __name__ == "__main__":
    main()
