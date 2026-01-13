import os
import requests
from datetime import datetime

# OpenWeatherMap API 설정
API_KEY = os.environ.get('OPENWEATHER_API_KEY')
CITY = 'Seoul'
COUNTRY = 'KR'

# 날씨 아이콘 매핑
WEATHER_ICONS = {
    '01d': '☀️', '01n': '🌙',
    '02d': '⛅', '02n': '☁️',
    '03d': '☁️', '03n': '☁️',
    '04d': '☁️', '04n': '☁️',
    '09d': '🌧️', '09n': '🌧️',
    '10d': '🌦️', '10n': '🌧️',
    '11d': '⛈️', '11n': '⛈️',
    '13d': '❄️', '13n': '❄️',
    '50d': '🌫️', '50n': '🌫️'
}

def get_weather():
    """OpenWeatherMap API로 날씨 정보 가져오기"""
    url = f'http://api.openweathermap.org/data/2.5/weather?q={CITY},{COUNTRY}&appid={API_KEY}&units=metric&lang=kr'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"날씨 정보 가져오기 실패: {e}")
        return None

def format_weather(data):
    """날씨 데이터를 README 형식으로 포맷팅"""
    if not data:
        return "날씨 정보를 가져올 수 없습니다."
    
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    description = data['weather'][0]['description']
    icon_code = data['weather'][0]['icon']
    humidity = data['main']['humidity']
    wind_speed = data['wind']['speed']
    
    icon = WEATHER_ICONS.get(icon_code, '🌡️')
    
    now = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
    
    weather_info = f"""## {icon} 오늘의 날씨 ({CITY})

**업데이트**: {now}

- **현재 기온**: {temp:.1f}°C (체감 {feels_like:.1f}°C)
- **날씨**: {description}
- **습도**: {humidity}%
- **풍속**: {wind_speed} m/s
"""
    return weather_info

def update_readme(weather_info):
    """README.md 파일 업데이트"""
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 날씨 섹션 구분자
        start_marker = '<!-- WEATHER:START -->'
        end_marker = '<!-- WEATHER:END -->'
        
        if start_marker in content and end_marker in content:
            # 기존 날씨 정보 교체
            before = content.split(start_marker)[0]
            after = content.split(end_marker)[1]
            new_content = f"{before}{start_marker}\n{weather_info}\n{end_marker}{after}"
        else:
            # 날씨 섹션이 없으면 맨 위에 추가
            new_content = f"{start_marker}\n{weather_info}\n{end_marker}\n\n{content}"
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("README.md 업데이트 완료!")
        
    except FileNotFoundError:
        print("README.md 파일이 없습니다.")
    except Exception as e:
        print(f"README 업데이트 실패: {e}")

if __name__ == '__main__':
    weather_data = get_weather()
    weather_info = format_weather(weather_data)
    update_readme(weather_info)
