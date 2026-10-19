"""
CLAUDE L-NACIONAL — Sync History v1
=====================================
Script liviano para los runs "solo sincronizar" (10:30 PM y 3:30 PM).

A diferencia de generate_picks.py, este script SOLO hace:
  1. Scrapea/actualiza data/history.xlsx para la lotería indicada
  2. Imprime qué se guardó

NO hace: verificar pick anterior, actualizar performance, correr análisis,
generar pick nuevo, ni tocar Telegram. Es intencional — el objetivo es que
cuando corra el job de generate_picks.py más tarde (12 PM o 4 PM), el
historial YA esté al día y no dependa de que el scrape ocurra en ese
mismo run.

Uso:
    python sync_history.py --lottery "Gana Más"
    python sync_history.py --lottery "Nacional Noche"
"""

import sys
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from loader import ensure_updated, get_last_date


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lottery", required=True, choices=["Gana Más", "Nacional Noche"])
    args = parser.parse_args()

    print(f"\n🔄 SYNC HISTORY — {args.lottery}")
    print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    before = get_last_date(args.lottery)
    draws  = ensure_updated(args.lottery)
    after  = draws[-1]["date"] if draws else None

    if before == after:
        print(f"\nℹ️  Sin cambios. Último sorteo guardado sigue siendo {after}.")
    else:
        last = draws[-1]
        print(f"\n✅ Historial actualizado: {before or '(vacío)'} → {after}")
        print(f"   Último sorteo: {last['date']} [{args.lottery}] {last['p1']}-{last['p2']}-{last['p3']}")

    print(f"\n📊 Total sorteos en historial ({args.lottery}): {len(draws)}\n")


if __name__ == "__main__":
    main()
