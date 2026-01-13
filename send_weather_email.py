import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# 날씨 정보 설정
LOCATION_NAME = '경기도 용인시 처인구 양지면'
LAT = 37.2567
LON = 127.2894

# 이메일 설정
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')  # 보내는 이메일
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')  # 앱 비밀번호
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')  # 받는 이메일

# 날씨 코드 매핑
WEATHER_ICONS = {
    0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
    45: '🌫️', 48: '🌫️',
    51: '🌦️', 53: '🌦️', 55: '🌧️',
    61: '🌧️', 63: '🌧️', 65: '🌧️',
    71: '❄️', 73: '❄️', 75: '❄️',
    80: '🌧️', 81: '🌧️', 82: '🌧️',
    95: '⛈️', 96: '⛈️', 99: '⛈️'
}

WEATHER_DESC = {
    0: '맑음', 1: '대체로 맑음', 2: '부분 흐림', 3: '흐림',
    45: '안개', 48: '안개',
    51: '약한 이슬비', 53: '이슬비', 55: '강한 이슬비',
    61: '약한 비', 63: '비', 65: '강한 비',
    71: '약한 눈', 73: '눈', 75: '강한 눈',
    80: '소나기', 81: '소나기', 82: '강한 소나기',
    95: '뇌우', 96: '뇌우', 99: '강한 뇌우'
}

def get_weather_forecast():
    """3일간 날씨 예보 가져오기"""
    url = f'https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&timezone=Asia/Seoul&forecast_days=3'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"날씨 정보 가져오기 실패: {e}")
        return None

def format_email_content(data):
    """이메일 본문 HTML 생성"""
    if not data:
        return "<p>날씨 정보를 가져올 수 없습니다.</p>"
    
    daily = data['daily']
    dates = daily['time']
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .container {{ background-color: white; padding: 20px; border-radius: 10px; max-width: 600px; margin: 0 auto; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            .day-card {{ background-color: #ecf0f1; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 5px solid #3498db; }}
            .day-title {{ font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
            .weather-info {{ margin: 5px 0; font-size: 16px; }}
            .icon {{ font-size: 40px; }}
            .footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌤️ {LOCATION_NAME} 날씨 예보</h1>
            <p style="color: #7f8c8d;">업데이트: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
    """
    
    day_names = ['오늘', '내일', '모레']
    
    for i in range(3):
        date = datetime.strptime(dates[i], '%Y-%m-%d')
        day_name = day_names[i]
        date_str = date.strftime('%m월 %d일 (%a)')
        
        weather_code = daily['weather_code'][i]
        temp_max = daily['temperature_2m_max'][i]
        temp_min = daily['temperature_2m_min'][i]
        precip_prob = daily['precipitation_probability_max'][i]
        wind_speed = daily['wind_speed_10m_max'][i]
        
        icon = WEATHER_ICONS.get(weather_code, '🌡️')
        description = WEATHER_DESC.get(weather_code, '정보 없음')
        
        html_content += f"""
            <div class="day-card">
                <div class="day-title">
                    <span class="icon">{icon}</span> {day_name} ({date_str})
                </div>
                <div class="weather-info">☀️ <strong>날씨:</strong> {description}</div>
                <div class="weather-info">🌡️ <strong>기온:</strong> 최저 {temp_min}°C / 최고 {temp_max}°C</div>
                <div class="weather-info">💧 <strong>강수확률:</strong> {precip_prob}%</div>
                <div class="weather-info">💨 <strong>최대풍속:</strong> {wind_speed} km/h</div>
            </div>
        """
    
    html_content += """
            <div class="footer">
                <p>이 메일은 GitHub Actions에서 자동으로 발송되었습니다.</p>
                <p>Open-Meteo API를 사용하여 날씨 정보를 제공합니다.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def send_email(html_content):
    """이메일 발송"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🌤️ {LOCATION_NAME} 3일 날씨 예보 - {datetime.now().strftime("%m/%d")}'
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Gmail SMTP 서버 사용
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        print("이메일 발송 완료!")
        
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == '__main__':
    # 이메일 설정 확인
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("Error: 이메일 설정이 필요합니다.")
        exit(1)
    
    # 날씨 정보 가져오기
    weather_data = get_weather_forecast()
    
    # 이메일 내용 생성
    html_content = format_email_content(weather_data)
    
    # 이메일 발송
    send_email(html_content)
