"""
CLAUDE L-NACIONAL — Loader v4
==============================
Fuente: enloteria.com (funciona en el runner de Gitea)
  Gana Más:       /resultados-gana-mas
  Nacional Noche: /resultados-nacional-noche

BUG FIX: El scraper anterior guardaba la fecha de la página
en vez de la fecha que se pedía. Ahora:
  - Gana Más: scrapes hasta HOY
  - Nacional Noche: scrapes hasta AYER solamente
    (el sorteo es a las 9 PM, si se corre a las 4 PM
     el resultado aún no existe y se guarda el de ayer con fecha de hoy)
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
        try:
            draws.append({
                "date":     date_str,
                "day_name": DAYS_ES[datetime.date.fromisoformat(date_str).weekday()],
                "lottery":  lottery,
                "p1":       str(int(float(p1))).zfill(2),
                "p2":       str(int(float(p2))).zfill(2),
                "p3":       str(int(float(p3))).zfill(2),
            })
        except (ValueError, TypeError):
            continue
    wb.close()
    draws.sort(key=lambda x: x["date"])

    # Filter holiday duplicates
    filtered = []
    for i, d in enumerate(draws):
        if i == 0:
            filtered.append(d)
            continue
        prev = draws[i - 1]
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


def parse_date_enloteria(text: str) -> str | None:
    """
    Parse dates from enloteria.com format:
    'Domingo 12 de julio, 2026' or 'Lunes 13 de julio, 2026'
    Returns ISO date string YYYY-MM-DD or None.
    """
    m = re.search(
        r"(\d{1,2})\s+de\s+(\w+)[,\s]+(\d{4})",
        text, re.IGNORECASE
    )
    if m:
        day   = int(m.group(1))
        month = MONTHS_ES.get(m.group(2).lower().strip(), 0)
        year  = int(m.group(3))
        if month > 0:
            try:
                return datetime.date(year, month, day).isoformat()
            except ValueError:
                pass
    return None


def extract_numbers(text: str) -> list[str]:
    """Extract 1-2 digit numbers from text, return zero-padded."""
    nums = re.findall(r"\b(\d{1,2})\b", text)
    return [str(int(n)).zfill(2) for n in nums if 0 <= int(n) <= 99]


def scrape_recent(lottery: str) -> list[dict]:
    """
    Scrape the main page of enloteria.com for a lottery.
    Returns all results visible on the page with their CORRECT dates
    parsed from the page itself.
    """
    url  = SCRAPE_URLS[lottery]
    soup = fetch_page(url)
    if not soup:
        return []

    results = []
    text    = soup.get_text(separator="\n")
    lines   = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for date pattern like "Domingo 12 de julio, 2026"
        date_found = parse_date_enloteria(line)
        if date_found:
            # Scan next lines for exactly 3 numbers (the result balls)
            nums = []
            j = i + 1
            while j < min(i + 20, len(lines)) and len(nums) < 3:
                candidate = extract_numbers(lines[j])
                # Each ball is on its own line as a 1-2 digit number
                if len(candidate) == 1:
                    nums.append(candidate[0])
                elif len(candidate) == 3 and not nums:
                    # Sometimes all 3 on same line
                    nums = candidate
                    break
                j += 1

            if len(nums) == 3:
                results.append({
                    "date":     date_found,
                    "day_name": DAYS_ES[datetime.date.fromisoformat(date_found).weekday()],
                    "lottery":  lottery,
                    "p1": nums[0], "p2": nums[1], "p3": nums[2],
                })
        i += 1

    # Deduplicate by date (keep first occurrence)
    seen = {}
    for r in results:
        if r["date"] not in seen:
            seen[r["date"]] = r
    return sorted(seen.values(), key=lambda x: x["date"])


def append_to_excel(new_rows: list[dict]) -> int:
    if not new_rows:
        return 0

    wb = openpyxl.load_workbook(HISTORY_FILE)
    ws = wb.active

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
    Update cycle:
    1. Check last date in Excel
    2. Scrape enloteria.com — uses dates FROM THE PAGE (not today's date)
    3. Filter: Nacional Noche only accepts results up to YESTERDAY
       (prevents saving yesterday's result with today's date)
    4. Append new results to Excel
    5. Return full draw list
    """
    last_date = get_last_date(lottery)
    today     = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Max date we accept for each lottery
    max_date = yesterday if lottery == "Nacional Noche" else today

    up_to_date = (last_date == max_date.isoformat())
    if up_to_date:
        print(f"  ✅ {lottery}: historial al día ({last_date})")
        return load_history(lottery)

    print(f"  📥 {lottery}: último={last_date}, scrapeando hasta {max_date}...")

    scraped = scrape_recent(lottery)

    # CRITICAL FIX: only accept results within valid date range
    # and newer than what we already have
    new_rows = [
        r for r in scraped
        if r["date"] > (last_date or "2000-01-01")
        and r["date"] <= max_date.isoformat()
    ]

    if new_rows:
        for r in new_rows:
            print(f"    ✅ {r['date']}: {r['p1']}-{r['p2']}-{r['p3']}")
        append_to_excel(new_rows)
    else:
        print(f"  ⚠️  No se encontraron resultados nuevos")

    return load_history(lottery)