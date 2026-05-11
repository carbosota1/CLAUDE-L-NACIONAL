"""
CLAUDE L-NACIONAL — Telegram Messenger
"""

import os
import requests
import datetime

DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
LOTTERY_TIMES = {"Gana Más": "2:30 PM", "Nacional Noche": "9:00 PM"}


def send_message(token: str, chat_id: str, text: str) -> dict:
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def build_picks_message(analysis: dict, performance: dict, next_date: str | None = None) -> str:
    lottery = analysis["lottery"]
    d       = datetime.date.fromisoformat(next_date) if next_date else datetime.date.today()
    weekday = d.weekday()  # 0=Monday
    day_name = DAYS_ES[weekday]
    date_str = d.strftime("%d %b %Y").upper()
    time_str = LOTTERY_TIMES.get(lottery, "")

    picks   = analysis["picks"][:3]
    p1 = picks[0]["num"] if len(picks) > 0 else "??"
    p2 = picks[1]["num"] if len(picks) > 1 else "??"
    p3 = picks[2]["num"] if len(picks) > 2 else "??"

    score         = picks[0]["composite_score"] if picks else 0
    markov_confidence = analysis.get("markov_confidence", 0)
    markov_max_prob   = analysis.get("markov_max_prob", analysis.get("max_prob", 0))
    # Show max transition probability % and lift vs baseline
    markov_pct    = markov_confidence
    mi_level      = analysis.get("mi_level", "N/A")
    chi_valid     = "✅" if analysis.get("chi2_significant") else "⚠️"
    overdue_max   = analysis.get("overdue_top", [{}])[0].get("gap", 0) if analysis.get("overdue_top") else 0
    total_draws   = analysis.get("total_draws", 0)
    chi2_pval     = round(analysis.get("chi2_pvalue", 1.0), 4)

    hit_rate      = performance.get("hit_rate", 0)
    main_hit_rate = performance.get("main_hit_rate", hit_rate)
    alt_hit_rate  = performance.get("alt_hit_rate", 0)
    streak        = performance.get("streak", 0)
    roi           = performance.get("roi", 0)
    streak_emoji  = "🔥" if streak > 0 else "❄️" if streak < 0 else "➖"
    roi_sign      = "+" if roi > 0 else ""

    pales = [f"{p1}-{p2}", f"{p1}-{p3}", f"{p2}-{p3}"]

    # Extended picks (4th and 5th)
    ext_picks = ""
    if len(analysis["picks"]) >= 5:
        p4 = analysis["picks"][3]["num"]
        p5 = analysis["picks"][4]["num"]
        ext_picks = f"\n4️⃣ Alternativo   →  <code>{p4}</code>  |  5️⃣ Alternativo   →  <code>{p5}</code>"

    msg = f"""🎯 <b>CLAUDE L-NACIONAL</b>
━━━━━━━━━━━━━━━━━━━━━
🎰 <b>{lottery.upper()}</b>
📅 {day_name} {date_str} • {time_str}
━━━━━━━━━━━━━━━━━━━━━
🔢 <b>PICKS PRINCIPALES</b>
━━━━━━━━━━━━━━━━━━━━━
🥇 1ra posición  →  <code>{p1}</code>
🥈 2da posición  →  <code>{p2}</code>
🥉 3ra posición  →  <code>{p3}</code>{ext_picks}
━━━━━━━━━━━━━━━━━━━━━
📊 <b>ANÁLISIS DEL SISTEMA</b>
━━━━━━━━━━━━━━━━━━━━━
🔥 Score compuesto:  <b>{score}/100</b>
⏳ Overdue máx:      <b>{overdue_max} sorteos</b>
🔗 Markov match:     <b>{markov_pct}%</b>
🧪 Chi² (p-value):   {chi_valid} <b>{chi2_pval}</b>
📈 MI correlación:   <b>{mi_level}</b>
📂 Historial:        <b>{total_draws} sorteos</b>
━━━━━━━━━━━━━━━━━━━━━
💰 <b>PALÉS SUGERIDOS</b>
━━━━━━━━━━━━━━━━━━━━━
• {pales[0]}   • {pales[1]}   • {pales[2]}
━━━━━━━━━━━━━━━━━━━━━
📉 <b>PERFORMANCE DEL SISTEMA</b>
━━━━━━━━━━━━━━━━━━━━━
Hit rate:      <b>{hit_rate}%</b> (últimos 30)
🎯 Main hits:   <b>{main_hit_rate}%</b>  |  🔵 Alts: <b>{alt_hit_rate}%</b>
Racha actual:  <b>{"+"+str(streak) if streak > 0 else str(streak)}</b> {streak_emoji}
ROI estimado:  <b>{roi_sign}{roi}%</b>
━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Solo para análisis estadístico</i>
🤖 <i>CLAUDE L-NACIONAL v1.0</i>"""

    return msg


def send_picks(analysis: dict, performance: dict, next_date: str | None = None) -> bool:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("⚠️  TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados")
        return False
    msg = build_picks_message(analysis, performance, next_date)
    result = send_message(token, chat_id, msg)
    if result.get("ok"):
        print("✅ Mensaje enviado a Telegram")
        return True
    print(f"❌ Error Telegram: {result}")
    return False


def send_verification_message(pick: dict, performance: dict) -> bool:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False

    result     = pick.get("result", "miss")
    result_map = {
        "miss":     ("❌ MISS",     "Sin acierto"),
        "1ra":      ("🥇 PRIMERA",  "Premio 1ra posición"),
        "2da":      ("🥈 SEGUNDA",  "Premio 2da posición"),
        "3ra":      ("🥉 TERCERA",  "Premio 3ra posición"),
        "pale":     ("💜 PALÉ",     "¡Palé ganador!"),
        "tripleta": ("🟢 TRIPLETA", "¡TRIPLETA! Premio máximo"),
    }
    emoji_label, description = result_map.get(result, ("❓ DESCONOCIDO", ""))

    msg = f"""📋 <b>CLAUDE L-NACIONAL — VERIFICACIÓN</b>
━━━━━━━━━━━━━━━━━━━━━
🎰 {pick.get('lottery', '')} · {pick.get('date', '')}
━━━━━━━━━━━━━━━━━━━━━
🎯 Picks jugados:    <code>{pick.get('p1')} — {pick.get('p2')} — {pick.get('p3')}</code>
🎲 Resultado real:   <code>{pick.get('real_p1','??')} — {pick.get('real_p2','??')} — {pick.get('real_p3','??')}</code>
━━━━━━━━━━━━━━━━━━━━━
{emoji_label}  <b>{description}</b>
━━━━━━━━━━━━━━━━━━━━━
📉 <b>PERFORMANCE ACTUALIZADO</b>
Hit rate:  <b>{performance.get('hit_rate', 0)}%</b>
Racha:     <b>{performance.get('streak', 0)}</b>
ROI:       <b>{performance.get('roi', 0)}%</b>
━━━━━━━━━━━━━━━━━━━━━
🤖 <i>CLAUDE L-NACIONAL v1.0</i>"""

    result_api = send_message(token, chat_id, msg)
    return result_api.get("ok", False)
