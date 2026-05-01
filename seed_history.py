"""
CLAUDE L-NACIONAL — Inicializador de Historial
================================================
Corre esto UNA SOLA VEZ para poblar el historial con datos de ejemplo.
Después reemplaza los datos con resultados reales usando add_result.py
"""

import sys
import json
import random
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from engine import save_json, DATA_DIR

HISTORY_FILE = DATA_DIR / "history.json"
DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

def generate_seed(days_back: int = 90) -> list[dict]:
    entries = []
    today   = datetime.date.today()
    rng     = random.Random(2024)  # Fixed seed for reproducibility

    for i in range(days_back, 0, -1):
        d       = today - datetime.timedelta(days=i)
        day_name = DAYS_ES[d.weekday()]

        for lottery in ["Gana Más", "Nacional Noche"]:
            entries.append({
                "id":       f"seed_{i}_{lottery.replace(' ','')}",
                "date":     d.isoformat(),
                "day_name": day_name,
                "lottery":  lottery,
                "p1":       str(rng.randint(0, 99)).zfill(2),
                "p2":       str(rng.randint(0, 99)).zfill(2),
                "p3":       str(rng.randint(0, 99)).zfill(2),
            })

    return entries


if __name__ == "__main__":
    print("🌱 CLAUDE L-NACIONAL — Generando historial inicial...")
    entries = generate_seed(90)
    data = {
        "version":      "1.0",
        "lotteries":    ["Gana Más", "Nacional Noche"],
        "history":      entries,
        "last_updated": datetime.datetime.now().isoformat(),
    }
    save_json(HISTORY_FILE, data)
    print(f"✅ {len(entries)} entradas generadas en data/history.json")
    print("⚠️  Recuerda reemplazar estos datos con resultados REALES usando add_result.py")
