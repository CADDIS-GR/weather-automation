import FinanceDataReader as fdr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import urllib.request
from datetime import datetime, timedelta
import pytz

KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST)

# ─── 날짜 계산 (월요일이면 금요일 데이터) ───────────────────────────────────
days_back = 3 if today.weekday() == 0 else 1
target_date = today - timedelta(days=days_back)
date_str = target_date.strftime('%Y-%m-%d')
display_date = target_date.strftime('%Y년 %m월 %d일')
weekday_kor = ['월', '화', '수', '목', '금', '토', '일'][target_date.weekday()]

# ─── 평균단가 (Secret 또는 기본값) ──────────────────────────────────────────
avg_prices = {
    '277630': float(os.environ.get('AVG_PRICE_277630', '50269')),
    '396500': float(os.environ.get('AVG_PRICE_396500', '31625')),
}

# ─── 1. 한국 ETF 조회 ────────────────────────────────────────────────────────
stock_codes_env = os.environ.get('STOCK_CODES', '277630,396500')
stock_codes = [s.strip() for s in stock_codes_env.split(',')]

kr_rows_html = ''
for code in stock_codes:
    try:
        df = fdr.DataReader(code, date_str, date_str)
        if df.empty:
            # 데이터 없으면 최근 1주 시도
            df = fdr.DataReader(code, (target_date - timedelta(days=7)).strftime('%Y-%m-%d'), date_str)

        if df.empty:
            kr_rows_html += f'<tr><td colspan="5" style="padding:10px 16px; color:#999">{code} 데이터 없음</td></tr>'
            continue

        row = df.iloc[-1]
        close = int(row['Close'])
        open_p = int(row['Open'])
        change = close - open_p
        change_pct = (change / open_p) * 100

        avg = avg_prices.get(code)
        if avg:
            profit = close - avg
            profit_pct = (profit / avg) * 100
            profit_color = '#e74c3c' if profit >= 0 else '#3498db'
            profit_sign = '+' if profit >= 0 else ''
            profit_str = f'{profit_sign}{profit:,.0f}원 ({profit_sign}{profit_pct:.2f}%)'
        else:
            profit_color = '#999'
            profit_str = '-'

        change_color = '#e74c3c' if change >= 0 else '#3498db'
        change_sign = '+' if change >= 0 else ''

        # 종목명 매핑
        name_map = {
            '277630': 'TIGER KOSPI',
            '396500': 'TIGER Fn반도체TOP10',
        }
        name = name_map.get(code, code)

        kr_rows_html += f'''
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:12px 16px; font-weight:600; color:#2c3e50">{name}<br>
              <span style="font-size:11px; color:#999; font-weight:400">{code}</span></td>
          <td style="padding:12px 16px; text-align:right; font-size:15px; font-weight:700">{close:,}원</td>
          <td style="padding:12px 16px; text-align:right; color:{change_color}; font-weight:600">{change_sign}{change_pct:.2f}%</td>
          <td style="padding:12px 16px; text-align:right; font-size:12px; color:#999">{avg:,.0f}원</td>
          <td style="padding:12px 16px; text-align:right; color:{profit_color}; font-size:13px; font-weight:600">{profit_str}</td>
        </tr>'''

    except Exception as e:
        kr_rows_html += f'<tr><td colspan="5" style="padding:10px 16px; color:#e74c3c">{code} 오류: {e}</td></tr>'

# ─── 2. 미국 시장 (나스닥 / S&P500 / SOX) ───────────────────────────────────
us_symbols = {
    'IXIC': '나스닥 종합',
    'SP500': 'S&P 500',
    'SOX': '필라델피아 반도체 (SOX)',
}

us_target = target_date - timedelta(days=1)  # 한국 전일 = 미국 전전날 장
us_start = (us_target - timedelta(days=5)).strftime('%Y-%m-%d')
us_end = us_target.strftime('%Y-%m-%d')

us_rows_html = ''
for symbol, name in us_symbols.items():
    try:
        df = fdr.DataReader(symbol, us_start, us_end)
        if df.empty:
            us_rows_html += f'<tr><td colspan="3" style="padding:8px 16px; color:#999">{name} 데이터 없음</td></tr>'
            continue

        close = float(df.iloc[-1]['Close'])
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]['Close'])
            change_pct = (close - prev_close) / prev_close * 100
            change_sign = '+' if change_pct >= 0 else ''
            change_color = '#e74c3c' if change_pct >= 0 else '#3498db'
            change_str = f'{change_sign}{change_pct:.2f}%'
        else:
            change_color = '#999'
            change_str = '-'

        us_rows_html += f'''
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:10px 16px; color:#2c3e50">{name}</td>
          <td style="padding:10px 16px; text-align:right; font-weight:600">{close:,.2f}</td>
          <td style="padding:10px 16px; text-align:right; color:{change_color}; font-weight:600">{change_str}</td>
        </tr>'''
    except Exception as e:
        us_rows_html += f'<tr><td colspan="3" style="padding:8px 16px; color:#e74c3c">{name} 오류: {e}</td></tr>'

# ─── 3. 원/달러 환율 ─────────────────────────────────────────────────────────
fx_html = ''
try:
    df_fx = fdr.DataReader('USD/KRW', us_start, us_end)
    if not df_fx.empty:
        fx_close = float(df_fx.iloc[-1]['Close'])
        if len(df_fx) >= 2:
            fx_prev = float(df_fx.iloc[-2]['Close'])
            fx_change = fx_close - fx_prev
            fx_sign = '+' if fx_change >= 0 else ''
            fx_color = '#e74c3c' if fx_change >= 0 else '#3498db'  # 원화 입장: 상승=약세=빨강
            fx_str = f'{fx_sign}{fx_change:.2f}원'
        else:
            fx_color = '#999'
            fx_str = '-'

        fx_html = f'''
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:10px 16px; color:#2c3e50">원/달러 환율</td>
          <td style="padding:10px 16px; text-align:right; font-weight:600">{fx_close:,.2f}원</td>
          <td style="padding:10px 16px; text-align:right; color:{fx_color}; font-weight:600">{fx_str}</td>
        </tr>'''
except Exception as e:
    fx_html = f'<tr><td colspan="3" style="padding:8px 16px; color:#e74c3c">환율 오류: {e}</td></tr>'

# ─── 4. 오늘의 주요 일정 (한국 경제 캘린더 — 고정 텍스트 fallback) ───────────
# 무료 API로 실시간 경제 일정 조회가 어려우므로,
# 주요 정기 이벤트 기반으로 요일별 안내 제공
weekday = today.weekday()
schedule_notes = {
    0: '미국 시장 주간 개막. 주요 연준 인사 발언 일정 확인 권장.',
    1: '국내 기관 수급 동향 집중 확인일. 미국 소비자 신뢰지수 발표 가능.',
    2: '미국 ADP 고용 / FOMC 의사록 발표 가능일 (격주).',
    3: '미국 주간 실업수당 청구건수 발표일.',
    4: '미국 고용보고서 발표 가능일 (매월 첫째 금요일). 주간 마감.',
}
today_note = schedule_notes.get(weekday, '주말 — 시장 휴장.')

# ─── HTML 이메일 조립 ────────────────────────────────────────────────────────
html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#f4f6f8; font-family: 'Apple SD Gothic Neo', Arial, sans-serif;">
  <div style="max-width:580px; margin:24px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,.08);">

    <!-- 헤더 -->
    <div style="background:#1a2332; padding:20px 24px;">
      <h2 style="margin:0; color:#fff; font-size:17px;">📊 아침 시장 브리핑</h2>
      <p style="margin:4px 0 0; font-size:12px; color:#8899aa;">{display_date} ({weekday_kor}) 장마감 기준</p>
    </div>

    <!-- 섹션 1: 보유 ETF -->
    <div style="padding:16px 0 0;">
      <div style="padding:6px 16px 8px; background:#f8f9fa; border-left:3px solid #1a2332; margin:0 16px 4px;">
        <span style="font-size:12px; font-weight:700; color:#1a2332; letter-spacing:.5px;">🇰🇷 보유 ETF</span>
      </div>
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr style="background:#f8f9fa; font-size:11px; color:#888;">
            <th style="padding:8px 16px; text-align:left; font-weight:600;">종목</th>
            <th style="padding:8px 16px; text-align:right; font-weight:600;">종가</th>
            <th style="padding:8px 16px; text-align:right; font-weight:600;">당일</th>
            <th style="padding:8px 16px; text-align:right; font-weight:600;">평균단가</th>
            <th style="padding:8px 16px; text-align:right; font-weight:600;">평가손익</th>
          </tr>
        </thead>
        <tbody>
          {kr_rows_html}
        </tbody>
      </table>
    </div>

    <!-- 섹션 2: 미국 시장 + 환율 -->
    <div style="padding:16px 0 0;">
      <div style="padding:6px 16px 8px; background:#f8f9fa; border-left:3px solid #2980b9; margin:0 16px 4px;">
        <span style="font-size:12px; font-weight:700; color:#2980b9; letter-spacing:.5px;">🇺🇸 미국 전일 시장 · 환율</span>
      </div>
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr style="background:#f8f9fa; font-size:11px; color:#888;">
            <th style="padding:8px 16px; text-align:left; font-weight:600;">지수 / 항목</th>
            <th style="padding:8px 16px; text-align:right; font-weight:600;">종가</th>
            <th style="padding:8px 16px; text-align:right; font-weight:600;">등락</th>
          </tr>
        </thead>
        <tbody>
          {us_rows_html}
          {fx_html}
        </tbody>
      </table>
    </div>

    <!-- 섹션 3: 오늘의 일정 -->
    <div style="padding:16px 16px 8px;">
      <div style="padding:6px 16px 8px; background:#f8f9fa; border-left:3px solid #27ae60; margin:0 -0px 8px;">
        <span style="font-size:12px; font-weight:700; color:#27ae60; letter-spacing:.5px;">📅 오늘의 주요 일정</span>
      </div>
      <p style="margin:4px 0 8px; font-size:13px; color:#555; padding:0 4px;">
        {today_note}
      </p>
    </div>

    <!-- 푸터 -->
    <div style="padding:12px 16px; border-top:1px solid #f0f0f0; text-align:center;">
      <p style="margin:0; font-size:10px; color:#ccc;">자동 발송 · CADDIS-GR weather-automation</p>
    </div>

  </div>
</body>
</html>
"""

# ─── 발송 ────────────────────────────────────────────────────────────────────
msg = MIMEMultipart('alternative')
msg['Subject'] = f'[브리핑] {display_date} ({weekday_kor}) 시장 요약'
msg['From'] = os.environ['SENDER_EMAIL']
msg['To'] = os.environ['RECEIVER_EMAIL']
msg.attach(MIMEText(html, 'html'))

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(os.environ['SENDER_EMAIL'], os.environ['SENDER_PASSWORD'])
    server.sendmail(os.environ['SENDER_EMAIL'], os.environ['RECEIVER_EMAIL'], msg.as_string())

print(f"✅ 브리핑 이메일 발송 완료 ({display_date})")
