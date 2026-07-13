"""
CLAUDE L-NACIONAL — Loader v3
==============================
Fuente: loterianacional.com.do (HTML estático, sin JS, sin bloqueo)
  Gana Más:       /resultados/gana-mas/?date=DD-MM-YYYY
  Nacional Noche: /resultados/loteria-nacional/?date=DD-MM-YYYY

Estrategia:
  1. Carga historial desde data/history.xlsx
  2. Detecta última fecha registrada
  3. Itera día a día desde esa fecha hasta hoy
  4. Parsea tabla HTML directamente (muy confiable)
  5. Valida que la fecha del resultado coincida con la fecha pedida
  6. Agrega solo resultados confirmados al Excel
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

# URL slugs on loterianacional.com.do
SCRAPE_SLUGS = {
    "Gana Más":       "gana-mas",
    "Nacional Noche": "loteria-nacional",
}

BASE_URL = "https://loterianacional.com.do/resultados"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-DO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MONTHS_ES = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12
}


# ── Load Excel ────────────────────────────────────────────────────────────────
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
            "p1":       str(int(float(p1))).zfill(2),
            "p2":       str(int(float(p2))).zfill(2),
            "p3":       str(int(float(p3))).zfill(2),
        })
    wb.close()
    draws.sort(key=lambda x: x["date"])

    # Filter holiday duplicates
    filtered = []
    for i, d in enumerate(draws):
        if i == 0:
            filtered.append(d)
            continue
        prev = draws[i-1]
        if d["p1"]==prev["p1"] and d["p2"]==prev["p2"] and d["p3"]==prev["p3"]:
            print(f"  ⚠️  Feriado omitido: {d['date']} {lottery} ({d['p1']}-{d['p2']}-{d['p3']})")
            continue
        filtered.append(d)
    return filtered


def get_last_date(lottery: str) -> str | None:
    draws = load_history(lottery)
    return draws[-1]["date"] if draws else None


# ── Scraper ───────────────────────────────────────────────────────────────────
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


def parse_date_from_text(text: str) -> str | None:
    """
    Parse dates like 'lunes 13 de julio de 2026' or 'sábado 4 de julio de 2026'
    Returns ISO date string or None.
    """
    m = re.search(
        r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})",
        text, re.IGNORECASE
    )
    if m:
        day   = int(m.group(1))
        month = MONTHS_ES.get(m.group(2).lower(), 0)
        year  = int(m.group(3))
        if month > 0:
            try:
                return datetime.date(year, month, day).isoformat()
            except ValueError:
                pass
    return None


def scrape_date(lottery: str, target_date: datetime.date) -> dict | None:
    """
    Scrape a specific date from loterianacional.com.do.
    Uses ?date=DD-MM-YYYY format.
    Validates that the returned result matches the requested date.
    """
    slug     = SCRAPE_SLUGS[lottery]
    date_fmt = target_date.strftime("%d-%m-%Y")  # DD-MM-YYYY format the site uses
    url      = f"{BASE_URL}/{slug}/?date={date_fmt}"

    soup = fetch_page(url)
    if not soup:
        return None

    # Parse the results table
    # Table has: Fecha | Hora | Números ganadores
    table = soup.find("table")
    if not table:
        # Try parsing from the "Último resultado" section
        text = soup.get_text()
        date_found = parse_date_from_text(text)
        if date_found == target_date.isoformat():
            nums = re.findall(r"\b(\d{2})\b", text[:500])
            if len(nums) >= 3:
                return {
                    "date":     date_found,
                    "day_name": DAYS_ES[target_date.weekday()],
                    "p1": nums[0], "p2": nums[1], "p3": nums[2],
                }
        return None

    rows = table.find_all("tr")
    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 3:
            continue

        # First column contains the date link/text
        date_cell = cols[0].get_text(strip=True)
        date_found = parse_date_from_text(date_cell)

        if not date_found:
            continue

        # CRITICAL: only accept rows that match our target date exactly
        if date_found != target_date.isoformat():
            continue

        # Third column contains the numbers
        nums_cell = cols[2].get_text(strip=True)
        nums = re.findall(r"\b(\d{1,2})\b", nums_cell)
        nums = [str(int(n)).zfill(2) for n in nums if 0 <= int(n) <= 99]

        if len(nums) >= 3:
            return {
                "date":     date_found,
                "day_name": DAYS_ES[target_date.weekday()],
                "lottery":  lottery,
                "p1": nums[0], "p2": nums[1], "p3": nums[2],
                "source": "loterianacional.com.do",
            }

    return None


def scrape_missing_dates(lottery: str, since_date: str, max_date: datetime.date | None = None) -> list[dict]:
    """
    Iterate day by day from since_date+1 to max_date (default: yesterday for NN, today for GM).
    Only adds results where the site confirms the exact date.
    This prevents saving today's Nacional Noche result before the draw happens.
    """
    start   = datetime.date.fromisoformat(since_date) + datetime.timedelta(days=1)
    end     = max_date if max_date else datetime.date.today()
    results = []

    print(f"  📅 Scrapeando {lottery} desde {start} hasta {end}...")

    current = start
    while current <= end:
        result = scrape_date(lottery, current)
        if result:
            results.append(result)
            print(f"    ✅ {current}: {result['p1']}-{result['p2']}-{result['p3']}")
        else:
            print(f"    ⏭️  {current}: sin resultado (feriado o no disponible aún)")
        current += datetime.timedelta(days=1)
        time.sleep(0.8)  # Be polite to the server

    return results


def append_to_excel(new_rows: list[dict]) -> int:
    """Append new rows to history.xlsx, skipping duplicates."""
    if not new_rows:
        return 0

    wb = openpyxl.load_workbook(HISTORY_FILE)
    ws = wb.active

    # Build existing keys
    existing = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0] or not row[1]: continue
        if isinstance(row[0], (datetime.datetime, datetime.date)):
            fecha = row[0].date().isoformat() if isinstance(row[0], datetime.datetime) else row[0].isoformat()
        else:
            fecha = str(row[0]).strip()
        canonical = LOTTERY_CANONICAL.get(str(row[1]).strip(), str(row[1]).strip())
        existing.add((fecha, canonical))

    EXCEL_NAMES = {
        "Gana Más":       "Loteria Nacional- Gana Más",
        "Nacional Noche": "Loteria Nacional- Noche",
    }

    added = 0
    for r in sorted(new_rows, key=lambda x: x["date"]):
        key = (r["date"], r["lottery"])
        if key in existing:
            print(f"    ⏭️  Ya existe: {r['date']} {r['lottery']}")
            continue
        ws.append([r["date"], EXCEL_NAMES[r["lottery"]], r["p1"], r["p2"], r["p3"]])
        existing.add(key)
        added += 1

    if added > 0:
        wb.save(HISTORY_FILE)
        print(f"  ✅ {added} nuevos resultados guardados en history.xlsx")
    else:
        print(f"  ℹ️  Sin cambios en history.xlsx")

    wb.close()
    return added


def ensure_updated(lottery: str) -> list[dict]:
    """
    Full update cycle:
    1. Find last date in Excel
    2. Scrape missing dates day by day (date-validated)
    3. Append to Excel
    4. Return full draw list

    IMPORTANT: Nacional Noche scrapes up to YESTERDAY only.
    The draw happens at 9 PM so when the system runs at 4 PM
    the result is not available yet. Scraping today would grab
    yesterday's result and save it with today's date — causing
    the date shift bug.
    """
    last_date = get_last_date(lottery)
    today     = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).isoformat()

    # For Nacional Noche: only scrape up to yesterday
    # For Gana Más: scrape up to today (result available by 4 PM)
    if lottery == "Nacional Noche":
        max_date = today - datetime.timedelta(days=1)
        up_to_date = last_date == yesterday
    else:
        max_date = today
        up_to_date = last_date == today.isoformat()

    if up_to_date:
        print(f"  ✅ {lottery}: historial al día ({last_date})")
    else:
        print(f"  📥 {lottery}: último={last_date}, scrapeando hasta {max_date}...")
        new_rows = scrape_missing_dates(lottery, last_date or "2020-12-29", max_date=max_date)
        if new_rows:
            append_to_excel(new_rows)
        else:
            print(f"  ⚠️  No se encontraron resultados nuevos")

    return load_history(lottery)