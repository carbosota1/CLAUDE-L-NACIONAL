"""
CLAUDE L-NACIONAL — Loader v2
==============================
Fuente principal: enloteria.com (HTML estático, sin JS)
  Gana Más:       /resultados-gana-mas
  Nacional Noche: /resultados-nacional-noche

Estrategia:
  - Página principal: últimos 3 resultados
  - Paginación por fecha: /resultados-gana-mas?date=YYYY-MM-DD
  - Itera desde la última fecha en el Excel hasta hoy
"""

import datetime
import re
import time
from pathlib import Path

import openpyxl
import requests
from bs4 import BeautifulSoup

DATA_DIR     = Path(__file__).parent.parent / "data"
HISTORY_FILE = DATA_DIR / "history.xlsx"
DAYS_ES      = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

LOTTERY_CANONICAL = {
    "Loteria Nacional- Gana Más":  "Gana Más",
    "Loteria Nacional- Noche":     "Nacional Noche",
    "Gana Más":                    "Gana Más",
    "Nacional Noche":              "Nacional Noche",
}

SCRAPE_URLS = {
    "Gana Más":       "https://enloteria.com/resultados-gana-mas",
    "Nacional Noche": "https://enloteria.com/resultados-nacional-noche",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-DO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── Load Excel ─────────────────────────────────────────────────────────────────
def load_history(lottery: str) -> list[dict]:
    wb = openpyxl.load_workbook(HISTORY_FILE, read_only=True, data_only=True)
    ws = wb.active
    draws = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]: continue
        fecha, sorteo, p1, p2, p3 = row[0], row[1], row[2], row[3], row[4]
        canonical = LOTTERY_CANONICAL.get(str(sorteo).strip())
        if canonical != lottery: continue
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
            "p1":       str(int(p1)).zfill(2),
            "p2":       str(int(p2)).zfill(2),
            "p3":       str(int(p3)).zfill(2),
        })
    wb.close()
    draws.sort(key=lambda x: x["date"])

    # Filter holiday duplicates
    filtered = []
    for i, d in enumerate(draws):
        if i == 0: filtered.append(d); continue
        prev = draws[i-1]
        if d["p1"]==prev["p1"] and d["p2"]==prev["p2"] and d["p3"]==prev["p3"]:
            print(f"  ⚠️  Feriado omitido: {d['date']} {lottery} ({d['p1']}-{d['p2']}-{d['p3']})")
            continue
        filtered.append(d)
    return filtered


def get_last_date(lottery: str) -> str | None:
    draws = load_history(lottery)
    return draws[-1]["date"] if draws else None


# ── Scraper using enloteria.com ────────────────────────────────────────────────
def fetch_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"    ⚠️  Intento {attempt+1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
    return None


def extract_results_from_soup(soup: BeautifulSoup) -> list[dict]:
    """
    Parse enloteria.com page and extract date + 3 numbers.
    The site renders: date string + 3 number balls per result block.
    """
    results = []
    today_year = datetime.date.today().year

    # Month name mapping
    MONTHS = {
        "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12
    }

    # Find all result blocks — each has a date and 3 numbers
    # Pattern: "Martes 30 de junio, 2026" followed by 3 numbers
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        # Match date like "Martes 30 de junio, 2026" or "Martes 30 de junio"
        dm = re.match(
            r"(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+(\d{1,2})\s+de\s+(\w+)(?:,?\s+(\d{4}))?",
            line, re.IGNORECASE
        )
        if dm:
            day   = int(dm.group(1))
            month = MONTHS.get(dm.group(2).lower(), 0)
            year  = int(dm.group(3)) if dm.group(3) else today_year
            if month > 0:
                try:
                    date_obj = datetime.date(year, month, day)
                    # Scan ahead for 3 numbers
                    nums = []
                    j = i + 1
                    while j < min(i + 20, len(lines)) and len(nums) < 3:
                        n = lines[j].strip()
                        if re.match(r"^\d{1,2}$", n) and 0 <= int(n) <= 99:
                            nums.append(str(int(n)).zfill(2))
                        j += 1
                    if len(nums) == 3:
                        results.append({
                            "date":     date_obj.isoformat(),
                            "day_name": DAYS_ES[date_obj.weekday()],
                            "p1": nums[0], "p2": nums[1], "p3": nums[2],
                        })
                except ValueError:
                    pass
        i += 1
    return results


def scrape_date(lottery: str, date: datetime.date) -> dict | None:
    """Scrape a specific date from enloteria.com using ?date= parameter."""
    base_url = SCRAPE_URLS[lottery]
    url = f"{base_url}?date={date.isoformat()}"
    soup = fetch_page(url)
    if not soup:
        return None
    results = extract_results_from_soup(soup)
    # Find the result matching our date
    for r in results:
        if r["date"] == date.isoformat():
            return r
    # Sometimes the page returns the closest available result
    if results:
        return results[0]
    return None


def scrape_missing_dates(lottery: str, since_date: str) -> list[dict]:
    """
    Iterate day by day from since_date+1 to today,
    scraping each date that's missing from the Excel.
    """
    start = datetime.date.fromisoformat(since_date) + datetime.timedelta(days=1)
    end   = datetime.date.today()
    new_results = []

    print(f"  📅 Scrapeando desde {start} hasta {end}...")

    current = start
    while current <= end:
        result = scrape_date(lottery, current)
        if result and result["date"] == current.isoformat():
            result["lottery"] = lottery
            new_results.append(result)
            print(f"    ✅ {current}: {result['p1']}-{result['p2']}-{result['p3']}")
        else:
            print(f"    ⏭️  {current}: sin resultado (feriado o no disponible)")
        current += datetime.timedelta(days=1)
        time.sleep(0.5)  # Be polite

    return new_results


def append_to_excel(new_rows: list[dict]) -> int:
    """Append new rows to history.xlsx, skipping duplicates."""
    if not new_rows:
        return 0
    wb = openpyxl.load_workbook(HISTORY_FILE)
    ws = wb.active

    existing = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            if isinstance(row[0], (datetime.datetime, datetime.date)):
                fecha = row[0].date().isoformat() if isinstance(row[0], datetime.datetime) else row[0].isoformat()
            else:
                fecha = str(row[0])
            canonical = LOTTERY_CANONICAL.get(str(row[1]).strip(), str(row[1]).strip())
            existing.add((fecha, canonical))

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
        print(f"  ✅ {added} filas nuevas guardadas en history.xlsx")
    wb.close()
    return added


def ensure_updated(lottery: str) -> list[dict]:
    """
    Full update cycle:
    1. Check last date in Excel
    2. Scrape all missing dates day by day
    3. Append to Excel
    4. Return full draw list
    """
    last_date = get_last_date(lottery)
    today     = datetime.date.today().isoformat()

    if last_date == today:
        print(f"  ✅ Historial actualizado hasta hoy ({today})")
    else:
        print(f"  📥 Último en Excel: {last_date} → scrapeando hasta {today}")
        new_rows = scrape_missing_dates(lottery, last_date or "2026-06-10")
        if new_rows:
            append_to_excel(new_rows)
        else:
            print(f"  ⚠️  No se encontraron resultados nuevos")

    return load_history(lottery)