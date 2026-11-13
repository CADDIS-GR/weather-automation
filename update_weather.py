import requests
import time
from datetime import datetime

# 날씨 정보 설정 (API 키 불필요!)
CITY = '경기도 용인시 처인구 양지면'
LAT = 37.2567  # 양지면 위도
LON = 127.2894  # 양지면 경도

# 날씨 코드에 따른 아이콘 매핑
WEATHER_ICONS = {
    0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
    45: '🌫️', 48: '🌫️',
    51: '🌦️', 53: '🌦️', 55: '🌧️',
    61: '🌧️', 63: '🌧️', 65: '🌧️',
    71: '❄️', 73: '❄️', 75: '❄️',
    80: '🌧️', 81: '🌧️', 82: '🌧️',
    95: '⛈️', 96: '⛈️', 99: '⛈️'
}

# 날씨 코드 설명
WEATHER_DESC = {
    0: '맑음', 1: '대체로 맑음', 2: '부분 흐림', 3: '흐림',
    45: '안개', 48: '안개',
    51: '약한 이슬비', 53: '이슬비', 55: '강한 이슬비',
    61: '약한 비', 63: '비', 65: '강한 비',
    71: '약한 눈', 73: '눈', 75: '강한 눈',
    80: '소나기', 81: '소나기', 82: '강한 소나기',
    95: '뇌우', 96: '뇌우', 99: '강한 뇌우'
}

def get_weather(max_retries=3, timeout=20):
    """Open-Meteo API로 날씨 정보 가져오기"""
    url = f'https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=Asia/Seoul'
    
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_err = e
            print(f"⚠️ 날씨 정보 가져오기 시도 {attempt}/{max_retries} 실패: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
    print(f"날씨 정보 가져오기 최종 실패: {last_err}")
    return None

def format_weather(data):
    """날씨 데이터를 README 형식으로 포맷팅"""
    if not data:
        return "날씨 정보를 가져올 수 없습니다."
    
    current = data['current']
    temp = current['temperature_2m']
    feels_like = current['apparent_temperature']
    humidity = current['relative_humidity_2m']
    wind_speed = current['wind_speed_10m']
    weather_code = current['weather_code']
    
    icon = WEATHER_ICONS.get(weather_code, '🌡️')
    description = WEATHER_DESC.get(weather_code, '정보 없음')
    
    now = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
    
    weather_info = f"""## {icon} 오늘의 날씨 ({CITY})

**업데이트**: {now}

- **현재 기온**: {temp}°C (체감 {feels_like}°C)
- **날씨**: {description}
- **습도**: {humidity}%
- **풍속**: {wind_speed} km/h
"""
    return weather_info

def update_readme(weather_info):
    """README.md 파일 업데이트"""
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        start_marker = '<!-- WEATHER:START -->'
        end_marker = '<!-- WEATHER:END -->'
        
        if start_marker in content and end_marker in content:
            before = content.split(start_marker)[0]
            after = content.split(end_marker)[1]
            new_content = f"{before}{start_marker}\n{weather_info}\n{end_marker}{after}"
        else:
            new_content = f"{start_marker}\n{weather_info}\n{end_marker}\n\n{content}"
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("README.md 업데이트 완료!")
        
    except Exception as e:
        print(f"README 업데이트 실패: {e}")

if __name__ == '__main__':
    weather_data = get_weather()
    weather_info = format_weather(weather_data)
    update_readme(weather_info)
