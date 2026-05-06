"""
CLAUDE L-NACIONAL — CSV Tracker
=================================
Guarda picks y performance en archivos CSV para
control exacto y análisis en Excel/Sheets.

Archivos generados:
  data/picks_log.csv      — Un registro por pick generado
  data/performance.csv    — Un registro de performance por día/lotería
"""

import csv
import json
import datetime
from pathlib import Path

DATA_DIR        = Path(__file__).parent.parent / "data"
PICKS_CSV       = DATA_DIR / "picks_log.csv"
PERFORMANCE_CSV = DATA_DIR / "performance.csv"
PICKS_JSON      = DATA_DIR / "picks_log.json"

PICKS_HEADERS = [
    "id", "fecha", "loteria", "p1", "p2", "p3",
    "score", "metodo", "status", "resultado",
    "real_p1", "real_p2", "real_p3", "pago",
    "total_sorteos", "chi2_significativo", "mi_nivel",
    "markov_confidence", "top5",
    "generado_en"
]

PERF_HEADERS = [
    "fecha", "loteria", "total_picks", "picks_verificados",
    "aciertos", "hit_rate_pct", "racha", "roi_pct",
    "total_invertido", "total_ganado", "actualizado_en"
]


def _ensure_csv(path: Path, headers: list[str]) -> None:
    """Create CSV with headers if it doesn't exist."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)


def save_pick_to_csv(pick: dict) -> None:
    """Append a new pick to picks_log.csv."""
    _ensure_csv(PICKS_CSV, PICKS_HEADERS)
    snapshot = pick.get("snapshot") or pick.get("analysis_snapshot") or {}
    row = [
        pick.get("id", ""),
        pick.get("date", ""),
        pick.get("lottery", ""),
        pick.get("p1", ""),
        pick.get("p2", ""),
        pick.get("p3", ""),
        pick.get("score", ""),
        pick.get("method", "Sistema"),
        pick.get("status", "pending"),
        pick.get("result", ""),
        pick.get("real_p1", ""),
        pick.get("real_p2", ""),
        pick.get("real_p3", ""),
        pick.get("payout", ""),
        snapshot.get("total_draws", ""),
        snapshot.get("chi2_significant", ""),
        snapshot.get("mi_level", ""),
        snapshot.get("markov_confidence", ""),
        ",".join(snapshot.get("top5", [])),
        datetime.datetime.now().isoformat(),
    ]
    with open(PICKS_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


def update_pick_result_in_csv(pick_id: str, result: str,
                               real_p1: str, real_p2: str, real_p3: str,
                               payout: float) -> None:
    """Update the result of an existing pick in the CSV."""
    if not PICKS_CSV.exists():
        return
    rows = []
    with open(PICKS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or PICKS_HEADERS
        for row in reader:
            if row.get("id") == pick_id:
                row["status"]   = "verified"
                row["resultado"] = result
                row["real_p1"]  = real_p1
                row["real_p2"]  = real_p2
                row["real_p3"]  = real_p3
                row["pago"]     = str(payout)
            rows.append(row)
    with open(PICKS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def save_performance_to_csv(lottery: str, perf: dict) -> None:
    """Append current performance snapshot to performance.csv."""
    _ensure_csv(PERFORMANCE_CSV, PERF_HEADERS)
    row = [
        datetime.date.today().isoformat(),
        lottery,
        perf.get("total_picks", 0),
        perf.get("verified_picks", 0),
        perf.get("hits", 0),
        perf.get("hit_rate", 0.0),
        perf.get("streak", 0),
        perf.get("roi", 0.0),
        perf.get("total_invested", 0.0),
        perf.get("total_won", 0.0),
        datetime.datetime.now().isoformat(),
    ]
    with open(PERFORMANCE_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


def sync_csv_from_json() -> int:
    """
    Full sync: rebuild picks_log.csv from picks_log.json.
    Useful when the CSV gets out of sync.
    Returns number of rows written.
    """
    if not PICKS_JSON.exists():
        return 0
    data  = json.loads(PICKS_JSON.read_text(encoding="utf-8"))
    picks = data.get("picks", [])

    # Rewrite entire CSV
    _ensure_csv(PICKS_CSV, PICKS_HEADERS)
    with open(PICKS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(PICKS_HEADERS)
        for pick in picks:
            snapshot = pick.get("snapshot") or pick.get("analysis_snapshot") or {}
            writer.writerow([
                pick.get("id", ""),
                pick.get("date", ""),
                pick.get("lottery", ""),
                pick.get("p1", ""),
                pick.get("p2", ""),
                pick.get("p3", ""),
                pick.get("score", ""),
                pick.get("method", "Sistema"),
                pick.get("status", "pending"),
                pick.get("result", ""),
                pick.get("real_p1", ""),
                pick.get("real_p2", ""),
                pick.get("real_p3", ""),
                pick.get("payout", ""),
                snapshot.get("total_draws", ""),
                snapshot.get("chi2_significant", ""),
                snapshot.get("mi_level", ""),
                snapshot.get("markov_confidence", ""),
                ",".join(snapshot.get("top5", [])),
                pick.get("id", "")[:15],  # use id prefix as timestamp
            ])
    return len(picks)
