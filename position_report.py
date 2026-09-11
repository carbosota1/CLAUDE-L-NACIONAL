"""
CLAUDE L-NACIONAL — Reporte de Aciertos por Posición
======================================================
Responde: "¿en qué posición del pick está acertando más el sistema?"

El sistema genera 5 números ordenados por score (1ra, 2da, 3ra = los que
pagan; 4to y 5to = alternativos, no pagan pero indican si el modelo
"casi" acierta). Este reporte cuenta, sobre los picks YA VERIFICADOS,
cuántas veces el acierto vino de cada posición.

Uso:
    python position_report.py [--lottery "Gana Más"|"Nacional Noche"]
    (sin --lottery, reporta ambas loterías por separado + combinado)

Lee data/picks_log.csv directamente — no requiere red ni el resto del
pipeline.
"""

import argparse
import csv
from pathlib import Path
from collections import defaultdict

DATA_DIR   = Path(__file__).parent / "data"
PICKS_CSV  = DATA_DIR / "picks_log.csv"

# Qué campo/columna del CSV corresponde a "acierto en esta posición"
POSITION_LABELS = {
    "1ra":  "1ra posición (p1)",
    "2da":  "2da posición (p2)",
    "3ra":  "3ra posición (p3)",
    "pale": "Palé (2 de 3 posiciones)",
    "tripleta": "Tripleta (3 de 3 posiciones)",
}


def load_verified(lottery: str | None) -> list[dict]:
    if not PICKS_CSV.exists():
        raise SystemExit(f"No encontré {PICKS_CSV}. Corre este script desde la raíz del repo.")
    rows = []
    with open(PICKS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") != "verified":
                continue
            if lottery and row.get("loteria") != lottery:
                continue
            rows.append(row)
    return rows


def report_for(lottery_label: str, rows: list[dict]) -> None:
    total = len(rows)
    print(f"\n{'='*56}")
    print(f"  {lottery_label}  —  {total} picks verificados")
    print(f"{'='*56}")
    if total == 0:
        print("  (sin datos)")
        return

    result_counts = defaultdict(int)
    for r in rows:
        result_counts[r.get("resultado", "miss")] += 1

    misses = result_counts.get("miss", 0)
    hits   = total - misses

    print(f"\n  Aciertos totales: {hits}/{total} ({hits/total*100:.1f}%)")
    print(f"  Misses:           {misses}/{total} ({misses/total*100:.1f}%)\n")

    print("  Desglose por tipo de acierto (dónde está acertando el sistema):")
    print(f"  {'Tipo':<28} {'Cantidad':>9} {'% del total':>12} {'% de aciertos':>15}")
    print(f"  {'-'*28} {'-'*9} {'-'*12} {'-'*15}")

    # Orden fijo: main positions primero (las que pagan), luego alternos
    ordered_keys = ["1ra", "2da", "3ra", "pale", "tripleta", "alt_hit"]
    for key in ordered_keys:
        count = result_counts.get(key, 0)
        if count == 0 and key not in ("1ra", "2da", "3ra"):
            continue
        label = POSITION_LABELS.get(key, "Alternativo (4to/5to, no paga)")
        pct_total = count / total * 100
        pct_hits  = (count / hits * 100) if hits else 0
        print(f"  {label:<28} {count:>9} {pct_total:>11.1f}% {pct_hits:>14.1f}%")

    # Cuál posición paga más (solo entre 1ra/2da/3ra, que son single-position hits)
    single_pos = {k: result_counts.get(k, 0) for k in ("1ra", "2da", "3ra")}
    if any(single_pos.values()):
        best = max(single_pos, key=single_pos.get)
        print(f"\n  🎯 La posición que MÁS acierta (de las que pagan): {POSITION_LABELS[best]} "
              f"({single_pos[best]} de {sum(single_pos.values())} aciertos de una sola posición)")

    # Alt hit: ¿4to o 5to acierta más?
    alt4 = sum(1 for r in rows if r.get("resultado") == "alt_hit" and str(r.get("all_picks","")).strip())
    # Nota: el CSV histórico puede no traer alt_hit_rank; si no está disponible, lo indicamos.
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lottery", choices=["Gana Más", "Nacional Noche"], default=None)
    args = parser.parse_args()

    if args.lottery:
        rows = load_verified(args.lottery)
        report_for(args.lottery, rows)
    else:
        for lot in ["Gana Más", "Nacional Noche"]:
            rows = load_verified(lot)
            report_for(lot, rows)
        combined = load_verified(None)
        report_for("COMBINADO (ambas loterías)", combined)


if __name__ == "__main__":
    main()
