"""
CLAUDE L-NACIONAL — Carga Masiva de Historial
===============================================
Carga múltiples resultados históricos desde un archivo CSV.

Formato del CSV (sin encabezado):
  fecha,loteria,p1,p2,p3
  2026-04-01,Gana Más,47,23,08
  2026-04-01,Nacional Noche,12,55,99
  2026-04-02,Gana Más,33,71,05

Uso:
  python bulk_history.py --file historico.csv
  python bulk_history.py --file historico.csv --no-telegram
"""

import sys
import csv
import json
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine import load_json, save_json, calc_performance, DATA_DIR
from telegram_bot import send_message
import os

HISTORY_FILE = DATA_DIR / "history.json"
PICKS_FILE   = DATA_DIR / "picks_log.json"
PERF_FILE    = DATA_DIR / "performance.json"
DAYS_ES      = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
VALID_LOTS   = {"Gana Más", "Nacional Noche"}


def validate_row(row: dict, line_num: int) -> tuple[bool, str]:
    """Validate a single CSV row. Returns (ok, error_message)."""
    required = ["fecha", "loteria", "p1", "p2", "p3"]
    for f in required:
        if f not in row or not row[f].strip():
            return False, f"Línea {line_num}: falta campo '{f}'"

    # Date
    try:
        datetime.date.fromisoformat(row["fecha"].strip())
    except ValueError:
        return False, f"Línea {line_num}: fecha inválida '{row['fecha']}' (usar YYYY-MM-DD)"

    # Lottery
    if row["loteria"].strip() not in VALID_LOTS:
        return False, f"Línea {line_num}: lotería inválida '{row['loteria']}' (usar 'Gana Más' o 'Nacional Noche')"

    # Numbers
    for field in ["p1","p2","p3"]:
        val = row[field].strip()
        if not val.isdigit() or not (0 <= int(val) <= 99):
            return False, f"Línea {line_num}: {field}='{val}' debe ser 00-99"

    return True, ""


def load_csv(filepath: Path) -> tuple[list[dict], list[str]]:
    """Load and validate CSV. Returns (valid_rows, errors)."""
    rows, errors = [], []

    with open(filepath, newline="", encoding="utf-8") as f:
        # Auto-detect if file has header
        sample = f.read(512)
        f.seek(0)
        has_header = "fecha" in sample.lower() or "loteria" in sample.lower()

        if has_header:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 2):
                # Normalize key names
                normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
                ok, err = validate_row(normalized, i)
                if ok:
                    rows.append(normalized)
                else:
                    errors.append(err)
        else:
            reader = csv.reader(f)
            for i, row in enumerate(reader, 1):
                if len(row) < 5:
                    errors.append(f"Línea {i}: se esperan 5 columnas (fecha,loteria,p1,p2,p3)")
                    continue
                normalized = {
                    "fecha":   row[0].strip(),
                    "loteria": row[1].strip(),
                    "p1":      row[2].strip(),
                    "p2":      row[3].strip(),
                    "p3":      row[4].strip(),
                }
                ok, err = validate_row(normalized, i)
                if ok:
                    rows.append(normalized)
                else:
                    errors.append(err)

    return rows, errors


def build_history_entry(row: dict) -> dict:
    d = datetime.date.fromisoformat(row["fecha"])
    return {
        "id":       f"r_bulk_{row['fecha']}_{row['loteria'].replace(' ','')}",
        "date":     row["fecha"],
        "day_name": DAYS_ES[d.weekday()],
        "lottery":  row["loteria"],
        "p1":       row["p1"].zfill(2),
        "p2":       row["p2"].zfill(2),
        "p3":       row["p3"].zfill(2),
    }


def merge_into_history(new_entries: list[dict]) -> tuple[int, int]:
    """Merge new entries into history, skipping duplicates. Returns (added, skipped)."""
    data    = load_json(HISTORY_FILE)
    history = data.get("history", [])

    # Build set of existing (date, lottery) pairs
    existing = {(h["date"], h["lottery"]) for h in history}

    added, skipped = 0, 0
    for entry in new_entries:
        key = (entry["date"], entry["lottery"])
        if key in existing:
            skipped += 1
        else:
            history.append(entry)
            existing.add(key)
            added += 1

    # Sort by date
    history.sort(key=lambda x: x["date"])
    data["history"]      = history
    data["last_updated"] = datetime.datetime.now().isoformat()
    save_json(HISTORY_FILE, data)
    return added, skipped


def send_summary_telegram(added: int, skipped: int, errors: int, total_history: int) -> None:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN","")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID","")
    if not token or not chat_id:
        return
    msg = f"""📦 <b>CLAUDE L-NACIONAL — Carga Masiva</b>
━━━━━━━━━━━━━━━━━━━━━
✅ Entradas agregadas:  <b>{added}</b>
⏭️ Duplicados omitidos: <b>{skipped}</b>
❌ Errores en CSV:      <b>{errors}</b>
📂 Total en historial:  <b>{total_history}</b>
━━━━━━━━━━━━━━━━━━━━━
🤖 <i>CLAUDE L-NACIONAL v1.0</i>"""
    try:
        send_message(token, chat_id, msg)
    except Exception as e:
        print(f"⚠️  Telegram: {e}")


def main():
    parser = argparse.ArgumentParser(description="CLAUDE L-NACIONAL — Carga Masiva de Historial")
    parser.add_argument("--file", required=True, help="Ruta al archivo CSV")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validar sin guardar nada")
    args = parser.parse_args()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"❌ Archivo no encontrado: {args.file}")
        sys.exit(1)

    print(f"\n📦 CLAUDE L-NACIONAL — Carga masiva desde: {args.file}\n")

    # Load and validate
    rows, errors = load_csv(filepath)

    print(f"  Filas válidas:   {len(rows)}")
    print(f"  Filas con error: {len(errors)}")

    if errors:
        print("\n⚠️  Errores encontrados:")
        for e in errors:
            print(f"    {e}")

    if not rows:
        print("❌ No hay filas válidas para procesar.")
        sys.exit(1)

    if args.dry_run:
        print("\n✅ DRY RUN — Nada fue guardado. Filas que se agregarían:")
        for r in rows[:10]:
            print(f"    {r['fecha']} | {r['loteria']} | {r['p1']}-{r['p2']}-{r['p3']}")
        if len(rows) > 10:
            print(f"    ... y {len(rows)-10} más")
        return

    # Merge
    entries = [build_history_entry(r) for r in rows]
    added, skipped = merge_into_history(entries)

    # Get updated total
    data         = load_json(HISTORY_FILE)
    total_history = len(data.get("history", []))

    print(f"\n  ✅ Agregadas:  {added}")
    print(f"  ⏭️  Omitidas:   {skipped} (duplicados)")
    print(f"  📂 Total:      {total_history} sorteos en historial")

    # Update performance for both lotteries
    for lot in ["Gana Más", "Nacional Noche"]:
        perf = calc_performance(lot)
        perf_data = load_json(PERF_FILE)
        perf_data.setdefault("by_lottery", {})[lot] = perf
        perf_data["last_updated"] = datetime.datetime.now().isoformat()
        save_json(PERF_FILE, perf_data)

    if not args.no_telegram:
        send_summary_telegram(added, skipped, len(errors), total_history)

    print("\n✅ Carga masiva completada.\n")


if __name__ == "__main__":
    main()
