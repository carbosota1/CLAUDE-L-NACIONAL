"""
CLAUDE L-NACIONAL — Ingresar Resultado Real
============================================
Agrega el resultado real al historial, verifica el pick pendiente,
actualiza performance y envía mensaje de verificación a Telegram.

Uso (manual desde GitHub Actions):
  python add_result.py --lottery "Gana Más" --p1 47 --p2 23 --p3 08
  python add_result.py --lottery "Nacional Noche" --p1 12 --p2 55 --p3 99
"""

import sys
import json
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine import load_json, save_json, calc_performance, DATA_DIR
from telegram_bot import send_verification_message

HISTORY_FILE = DATA_DIR / "history.json"
PICKS_FILE   = DATA_DIR / "picks_log.json"
PERF_FILE    = DATA_DIR / "performance.json"

DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def add_to_history(lottery: str, p1: str, p2: str, p3: str, date: str) -> dict:
    """Append a new result to history.json."""
    data    = load_json(HISTORY_FILE)
    history = data.get("history", [])

    d = datetime.date.fromisoformat(date)
    entry = {
        "id":       f"r_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "date":     date,
        "day_name": DAYS_ES[d.weekday()],
        "lottery":  lottery,
        "p1":       p1.zfill(2),
        "p2":       p2.zfill(2),
        "p3":       p3.zfill(2),
    }

    # Avoid duplicate for same date+lottery
    existing = [(h["date"], h["lottery"]) for h in history]
    if (date, lottery) in existing:
        print(f"⚠️  Ya existe un resultado para {lottery} en {date}. Actualizando...")
        history = [h for h in history if not (h["date"] == date and h["lottery"] == lottery)]

    history.append(entry)
    data["history"]      = history
    data["last_updated"] = datetime.datetime.now().isoformat()
    save_json(HISTORY_FILE, data)
    print(f"✅ Historial actualizado: {lottery} {date} → {p1} — {p2} — {p3}")
    return entry


def verify_pending_pick(lottery: str, real_p1: str, real_p2: str, real_p3: str, date: str) -> dict | None:
    """
    Find the most recent pending pick for this lottery+date and verify it.
    Returns the updated pick.
    """
    data  = load_json(PICKS_FILE)
    picks = data.get("picks", [])

    # Find most recent pending pick for this lottery
    pending = [
        p for p in picks
        if p.get("lottery") == lottery and p.get("status") == "pending"
    ]
    if not pending:
        print("ℹ️  No hay picks pendientes para verificar.")
        return None

    # Take the most recent
    target = sorted(pending, key=lambda x: x.get("id", ""))[-1]

    pick_nums = [target["p1"], target["p2"], target["p3"]]
    real_nums = [real_p1.zfill(2), real_p2.zfill(2), real_p3.zfill(2)]

    # Determine result
    any_match  = [n for n in pick_nums if n in real_nums]
    pos_match  = [pick_nums[i] for i in range(3) if pick_nums[i] == real_nums[i]]

    result = "miss"
    payout = 0.0
    amt    = float(target.get("amount", 0) or 0)

    if len(any_match) == 3:
        result = "tripleta"; payout = amt * 20000
    elif len(any_match) >= 2:
        result = "pale";     payout = amt * 1000
    elif pick_nums[0] == real_nums[0]:
        result = "1ra";      payout = amt * 60
    elif pick_nums[1] == real_nums[1]:
        result = "2da";      payout = amt * 8
    elif pick_nums[2] == real_nums[2]:
        result = "3ra";      payout = amt * 5

    target.update({
        "status":    "verified",
        "result":    result,
        "payout":    payout,
        "real_p1":   real_nums[0],
        "real_p2":   real_nums[1],
        "real_p3":   real_nums[2],
        "verified_at": datetime.datetime.now().isoformat(),
    })

    # Save updated picks
    updated_picks = [p if p["id"] != target["id"] else target for p in picks]
    data["picks"]  = updated_picks
    save_json(PICKS_FILE, data)

    result_label = {
        "miss": "❌ MISS", "1ra": "🥇 1RA", "2da": "🥈 2DA",
        "3ra": "🥉 3RA", "pale": "💜 PALÉ", "tripleta": "🟢 TRIPLETA"
    }.get(result, result)
    print(f"✅ Pick verificado: {result_label} | Pago: RD${payout:,.0f}")
    return target


def update_performance_file(lottery: str) -> dict:
    """Recalculate and save performance stats."""
    perf = calc_performance(lottery)
    data = load_json(PERF_FILE)
    data["summary"]             = perf
    data["by_lottery"]          = data.get("by_lottery", {})
    data["by_lottery"][lottery] = perf
    data["last_updated"]        = datetime.datetime.now().isoformat()
    save_json(PERF_FILE, data)
    return perf


def main():
    parser = argparse.ArgumentParser(description="CLAUDE L-NACIONAL — Ingresar Resultado")
    parser.add_argument("--lottery", required=True, choices=["Gana Más", "Nacional Noche"])
    parser.add_argument("--p1", required=True, help="Número 1ra posición (00-99)")
    parser.add_argument("--p2", required=True, help="Número 2da posición (00-99)")
    parser.add_argument("--p3", required=True, help="Número 3ra posición (00-99)")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="Fecha del sorteo (YYYY-MM-DD, default: hoy)")
    parser.add_argument("--no-telegram", action="store_true")
    args = parser.parse_args()

    # Validate numbers
    for val, name in [(args.p1, "p1"), (args.p2, "p2"), (args.p3, "p3")]:
        if not val.isdigit() or not (0 <= int(val) <= 99):
            print(f"❌ Error: {name}={val} debe ser un número entre 00 y 99")
            sys.exit(1)

    print(f"\n📥 CLAUDE L-NACIONAL — Ingresando resultado")
    print(f"   Lotería: {args.lottery}")
    print(f"   Fecha:   {args.date}")
    print(f"   Números: {args.p1} — {args.p2} — {args.p3}\n")

    # 1. Add to history
    add_to_history(args.lottery, args.p1, args.p2, args.p3, args.date)

    # 2. Verify pending pick
    pick = verify_pending_pick(args.lottery, args.p1, args.p2, args.p3, args.date)

    # 3. Update performance
    perf = update_performance_file(args.lottery)
    print(f"\n📊 Performance actualizado:")
    print(f"   Hit rate: {perf['hit_rate']}%  |  Racha: {perf['streak']}  |  ROI: {perf['roi']}%")

    # 4. Send Telegram verification message
    if not args.no_telegram and pick:
        send_verification_message(pick, perf)

    print("\n✅ CLAUDE L-NACIONAL — Resultado procesado\n")


if __name__ == "__main__":
    main()
