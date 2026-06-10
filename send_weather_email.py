import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pytz
import os

# ── 이메일 설정 ──────────────────────────────────────────
SENDER_EMAIL    = os.environ['SENDER_EMAIL']
SENDER_PASSWORD = os.environ['SENDER_PASSWORD']
RECEIVER_EMAIL  = os.environ['RECEIVER_EMAIL']

# ── 지점 설정 ────────────────────────────────────────────
LOCATIONS = [
    {
        "name":  "경기도 용인시 처인구 양지면",
        "label": "🎣 낚시터 (양지면)",
        "lat":   37.2567,
        "lon":   127.2894,
    },
    {
        "name":  "경기도 화성시 우정읍",
        "label": "🏢 직장 (우정읍)",
        "lat":   37.1289466,
        "lon":   126.8007403,
    },
]

KST = pytz.timezone('Asia/Seoul')

# ── WMO 날씨 코드 변환 ────────────────────────────────────
def wmo_to_description(code):
    mapping = {
        0: ("맑음", "☀️"), 1: ("대체로 맑음", "🌤️"), 2: ("부분 흐림", "⛅"),
        3: ("흐림", "☁️"), 45: ("안개", "🌫️"), 48: ("안개", "🌫️"),
        51: ("이슬비", "🌦️"), 53: ("이슬비", "🌦️"), 55: ("이슬비", "🌦️"),
        61: ("비", "🌧️"), 63: ("비", "🌧️"), 65: ("강한 비", "🌧️"),
        71: ("눈", "❄️"), 73: ("눈", "❄️"), 75: ("강한 눈", "❄️"),
        77: ("싸락눈", "🌨️"), 80: ("소나기", "🌦️"), 81: ("소나기", "🌦️"),
        82: ("강한 소나기", "⛈️"), 85: ("눈소나기", "🌨️"), 86: ("눈소나기", "🌨️"),
        95: ("뇌우", "⛈️"), 96: ("뇌우+우박", "⛈️"), 99: ("뇌우+우박", "⛈️"),
    }
    return mapping.get(code, ("알 수 없음", "❓"))

# ── Open-Meteo API 호출 ───────────────────────────────────
def fetch_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":  lat,
        "longitude": lon,
        "daily": [
            "weathercode", "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max", "windspeed_10m_max",
        ],
        "current_weather": True,
        "timezone": "Asia/Seoul",
        "forecast_days": 3,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# ── 지점별 HTML 카드 생성 ─────────────────────────────────
def build_location_card(loc):
    data    = fetch_weather(loc["lat"], loc["lon"])
    daily   = data["daily"]
    current = data["current_weather"]

    cur_desc, cur_icon = wmo_to_description(current["weathercode"])

    # 날짜별 카드
    day_cards = ""
    today = datetime.now(KST).date()
    day_labels = ["오늘", "내일", "모레"]

    for i in range(3):
        date_str = daily["time"][i]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        label    = day_labels[i]
        weekday  = ["월","화","수","목","금","토","일"][date_obj.weekday()]
        desc, icon = wmo_to_description(daily["weathercode"][i])
        t_max  = daily["temperature_2m_max"][i]
        t_min  = daily["temperature_2m_min"][i]
        precip = daily["precipitation_probability_max"][i]
        wind   = daily["windspeed_10m_max"][i]

        bg = "#e8f4fd" if i == 0 else "#f9f9f9"
        border = "2px solid #3498db" if i == 0 else "1px solid #e0e0e0"

        day_cards += f"""
        <div style="background:{bg};border:{border};border-radius:12px;
                    padding:16px;text-align:center;min-width:140px;">
          <div style="font-weight:700;color:#2c3e50;font-size:14px;">
            {label} ({date_str[5:]} {weekday})
          </div>
          <div style="font-size:36px;margin:8px 0;">{icon}</div>
          <div style="color:#555;font-size:13px;margin-bottom:8px;">{desc}</div>
          <div style="font-size:15px;font-weight:700;color:#e74c3c;">
            {t_max:.1f}°C
          </div>
          <div style="font-size:13px;color:#3498db;">{t_min:.1f}°C</div>
          <div style="margin-top:8px;font-size:12px;color:#666;">
            💧 {precip}% &nbsp; 💨 {wind:.1f}㎞/h
          </div>
        </div>"""

    return f"""
    <div style="background:#fff;border-radius:16px;padding:24px;margin-bottom:28px;
                box-shadow:0 2px 12px rgba(0,0,0,0.08);">
      <h2 style="margin:0 0 6px;color:#2c3e50;font-size:18px;">{loc['label']}</h2>
      <div style="color:#888;font-size:13px;margin-bottom:14px;">{loc['name']}</div>

      <!-- 현재 날씨 -->
      <div style="background:#eaf6ff;border-radius:10px;padding:12px 16px;
                  margin-bottom:16px;display:flex;align-items:center;gap:12px;">
        <span style="font-size:28px;">{cur_icon}</span>
        <div>
          <div style="font-size:22px;font-weight:700;color:#2c3e50;">
            {current['temperature']:.1f}°C
          </div>
          <div style="font-size:13px;color:#555;">
            현재 · {cur_desc} · 풍속 {current['windspeed']:.1f}㎞/h
          </div>
        </div>
      </div>

      <!-- 3일 예보 -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;">
        {day_cards}
      </div>
    </div>"""

# ── 이메일 발송 ───────────────────────────────────────────
def send_email():
    now_str = datetime.now(KST).strftime("%Y년 %m월 %d일 %H:%M")

    # 두 지점 카드 생성
    cards_html = ""
    for loc in LOCATIONS:
        try:
            cards_html += build_location_card(loc)
        except Exception as e:
            cards_html += f"""
            <div style="background:#fff3cd;border-radius:12px;padding:16px;margin-bottom:20px;">
              <b>{loc['label']}</b> 날씨 정보를 불러오지 못했습니다.<br>
              <small style="color:#888;">{e}</small>
            </div>"""

    html = f"""
    <html><body style="font-family:'Apple SD Gothic Neo',sans-serif;
                       background:#f0f4f8;margin:0;padding:20px;">
      <div style="max-width:600px;margin:0 auto;">

        <!-- 헤더 -->
        <div style="background:linear-gradient(135deg,#2980b9,#27ae60);
                    border-radius:16px;padding:24px;color:#fff;
                    text-align:center;margin-bottom:24px;">
          <div style="font-size:28px;margin-bottom:6px;">🌤️ 오늘의 날씨 브리핑</div>
          <div style="font-size:13px;opacity:0.85;">{now_str} 기준</div>
        </div>

        <!-- 지점 카드 -->
        {cards_html}

        <!-- 푸터 -->
        <div style="text-align:center;color:#aaa;font-size:11px;margin-top:8px;">
          Open-Meteo 제공 · GitHub Actions 자동 발송
        </div>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    today_label = datetime.now(KST).strftime("%m/%d(%a)")
    msg["Subject"] = f"🌤️ [{today_label}] 날씨 브리핑 — 양지면 · 우정읍"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    print(f"✅ 이메일 발송 완료: {now_str}")

if __name__ == "__main__":
    send_email()
