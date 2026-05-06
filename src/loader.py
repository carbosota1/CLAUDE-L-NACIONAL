"""
CLAUDE L-NACIONAL — Cargador de Historial
==========================================
Lee el archivo data/history.xlsx, normaliza los datos,
detecta días feriados y verifica si el historial está actualizado.

Formato del Excel:
  Columnas: fecha | sorteo | primero | segundo | tercero
  Sorteos:  'Loteria Nacional- Gana Más'
            'Loteria Nacional- Noche'
"""

import datetime
import re
from pathlib import Path
from collections import defaultdict

import openpyxl
import requests
from bs4 import BeautifulSoup

DATA_DIR     = Path(__file__).parent.parent / "data"
HISTORY_FILE = DATA_DIR / "history.xlsx"
DAYS_ES      = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

# Canonical names used internally
LOTTERY_CANONICAL = {
    "Loteria Nacional- Gana Más":  "Gana Más",
    "Loteria Nacional- Noche":     "Nacional Noche",
    "Gana Más":                    "Gana Más",
    "Nacional Noche":              "Nacional Noche",
}

# Scraping sources
SCRAPE_URLS = {
    "Gana Más":       "https://loteriasdominicanas.com/loteria-nacional/gana-mas",
    "Nacional Noche": "https://loteriasdominicanas.com/loteria-nacional/quiniela",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-DO,es;q=0.9",
}


# ── Load Excel ─────────────────────────────────────────────────────────────────
def load_history(lottery: str) -> list[dict]:
    """
    Load and return sorted draws for a specific lottery from history.xlsx.
    Filters out likely holiday duplicates (same numbers as previous day).
    """
    wb = openpyxl.load_workbook(HISTORY_FILE, read_only=True, data_only=True)
    ws = wb.active

    draws = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        fecha, sorteo, p1, p2, p3 = row[0], row[1], row[2], row[3], row[4]

        # Normalize lottery name
        canonical = LOTTERY_CANONICAL.get(str(sorteo).strip())
        if canonical != lottery:
            continue

        # Normalize date
        if isinstance(fecha, datetime.datetime):
            date_str = fecha.date().isoformat()
        elif isinstance(fecha, datetime.date):
            date_str = fecha.isoformat()
        else:
            date_str = str(fecha).strip()

        draws.append({
            "date":     date_str,
            "day_name": DAYS_ES[datetime.date.fromisoformat(date_str).weekday()],
            "lottery":  lottery,
            "p1":       str(p1).zfill(2),
            "p2":       str(p2).zfill(2),
            "p3":       str(p3).zfill(2),
        })

    wb.close()

    # Sort by date
    draws.sort(key=lambda x: x["date"])

    # Filter holiday duplicates:
    # If a draw has identical numbers to the previous draw of same lottery → skip
    filtered = []
    for i, d in enumerate(draws):
        if i == 0:
            filtered.append(d)
            continue
        prev = draws[i - 1]
        if d["p1"] == prev["p1"] and d["p2"] == prev["p2"] and d["p3"] == prev["p3"]:
            print(f"  ⚠️  Feriado detectado y omitido: {d['date']} {lottery} ({d['p1']}-{d['p2']}-{d['p3']})")
            continue
        filtered.append(d)

    return filtered


def get_last_date(lottery: str) -> str | None:
    """Return the most recent date in the Excel for a given lottery."""
    draws = load_history(lottery)
    return draws[-1]["date"] if draws else None


def is_up_to_date(lottery: str) -> tuple[bool, str | None]:
    """
    Check if the history is up to date for today's draw.
    Returns (is_current, last_date_in_file).
    """
    today     = datetime.date.today().isoformat()
    last_date = get_last_date(lottery)
    return (last_date == today), last_date


# ── Scraper for missing recent dates ─────────────────────────────────────────
def scrape_recent(lottery: str, since_date: str) -> list[dict]:
    """
    Scrape results from loteriasdominicanas.com for dates after since_date.
    Returns list of new result dicts.
    """
    url  = SCRAPE_URLS[lottery]
    year = datetime.date.today().year

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ⚠️  No se pudo conectar a {url}: {e}")
        return []

    results = []
    text    = soup.get_text(separator="\n")
    lines   = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        # Match date like "16-04" or "30-04"
        m = re.match(r"^(\d{1,2})[-/](\d{1,2})$", lines[i])
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            try:
                d = datetime.date(year, month, day)
                if d > datetime.date.today():
                    d = datetime.date(year - 1, month, day)
                date_str = d.isoformat()

                # Only grab dates we don't have yet
                if date_str > since_date:
                    # Scan next lines for 3 numbers
                    window = " ".join(lines[i+1:i+12])
                    nums   = re.findall(r"\b(\d{1,2})\b", window)
                    nums   = [n.zfill(2) for n in nums if 0 <= int(n) <= 99]
                    if len(nums) >= 3:
                        results.append({
                            "date":     date_str,
                            "day_name": DAYS_ES[d.weekday()],
                            "lottery":  lottery,
                            "p1":       nums[0],
                            "p2":       nums[1],
                            "p3":       nums[2],
                            "source":   "scraper",
                        })
            except ValueError:
                pass
        i += 1

    # Deduplicate by date
    seen = {}
    for r in results:
        seen[r["date"]] = r
    return sorted(seen.values(), key=lambda x: x["date"])


def append_to_excel(new_rows: list[dict]) -> int:
    """
    Append new rows to history.xlsx.
    Returns number of rows actually added.
    """
    if not new_rows:
        return 0

    wb = openpyxl.load_workbook(HISTORY_FILE)
    ws = wb.active

    # Build set of existing (date, lottery) pairs
    existing = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            fecha = row[0].date().isoformat() if isinstance(row[0], (datetime.datetime, datetime.date)) else str(row[0])
            canonical = LOTTERY_CANONICAL.get(str(row[1]).strip(), str(row[1]).strip())
            existing.add((fecha, canonical))

    # Reverse-map canonical → Excel name
    excel_name = {
        "Gana Más":       "Loteria Nacional- Gana Más",
        "Nacional Noche": "Loteria Nacional- Noche",
    }

    added = 0
    for r in sorted(new_rows, key=lambda x: x["date"]):
        key = (r["date"], r["lottery"])
        if key in existing:
            continue
        ws.append([r["date"], excel_name[r["lottery"]], r["p1"], r["p2"], r["p3"]])
        existing.add(key)
        added += 1

    if added > 0:
        wb.save(HISTORY_FILE)
        print(f"  ✅ {added} filas nuevas agregadas a history.xlsx")

    wb.close()
    return added


def ensure_updated(lottery: str) -> list[dict]:
    """
    Full update cycle:
    1. Check if history.xlsx is current
    2. If not, scrape missing dates and append to Excel
    3. Return the full up-to-date draw list
    """
    current, last_date = is_up_to_date(lottery)

    if current:
        print(f"  ✅ Historial actualizado ({last_date})")
    else:
        print(f"  📥 Historial desactualizado. Último: {last_date}. Scrapeando...")
        new_rows = scrape_recent(lottery, last_date or "2020-01-01")
        if new_rows:
            print(f"  🕷️  {len(new_rows)} resultados nuevos encontrados en web")
            append_to_excel(new_rows)
        else:
            print(f"  ⚠️  No se encontraron resultados nuevos en web")

    return load_history(lottery)