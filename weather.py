"""
날씨 API 모듈 (Open-Meteo, API 키 불필요)
- 다음 주(월~일) 일별 강수 확률/강수량/기온 조회
- 강수 확률 기반 러닝 장소(야외/트레드밀) 추천
- 러닝을 비 올 확률이 낮은 요일에 우선 배치
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date, timedelta

API_URL = "https://api.open-meteo.com/v1/forecast"
DAYS = ["월", "화", "수", "목", "금", "토", "일"]


class WeatherError(Exception):
    """날씨 조회 실패 (네트워크 오류, 응답 형식 오류 등)"""


def load_env(path=".env"):
    """.env 파일의 KEY=VALUE 줄을 환경변수로 읽어온다. 파일이 없으면 무시."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_settings():
    """위치와 기준 강수 확률을 .env(없으면 기본값: 서울, 60%)에서 가져온다."""
    load_env()
    return {
        "lat": float(os.getenv("WEATHER_LAT", "37.5665")),
        "lon": float(os.getenv("WEATHER_LON", "126.9780")),
        "location": os.getenv("WEATHER_LOCATION_NAME", "서울"),
        "threshold": int(os.getenv("RAIN_THRESHOLD", "60")),
    }


def next_week_dates(today=None):
    """오늘 기준 다음 주 월요일~일요일 날짜 7개를 돌려준다."""
    today = today or date.today()
    monday = today + timedelta(days=7 - today.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def fetch_weekly_weather(lat, lon, dates, timeout=10):
    """Open-Meteo에서 dates 기간의 일별 예보를 받아 {요일: {...}} 형태로 돌려준다."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_probability_max,precipitation_sum,"
                 "temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Seoul",
        "start_date": dates[0].isoformat(),
        "end_date": dates[-1].isoformat(),
    }
    url = API_URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise WeatherError(f"날씨 API 요청 실패: {e}") from e
    return parse_daily(data, dates)


def parse_daily(data, dates):
    """API 응답(JSON)에서 필요한 값만 뽑아 요일별 딕셔너리로 정리한다."""
    try:
        daily = data["daily"]
        by_date = {t: i for i, t in enumerate(daily["time"])}
        result = {}
        for d in dates:
            i = by_date[d.isoformat()]
            result[DAYS[d.weekday()]] = {
                "date": d,
                "pop": daily["precipitation_probability_max"][i] or 0,
                "rain_mm": daily["precipitation_sum"][i] or 0.0,
                "tmax": daily["temperature_2m_max"][i],
                "tmin": daily["temperature_2m_min"][i],
            }
        return result
    except (KeyError, IndexError, TypeError) as e:
        raise WeatherError(f"날씨 응답 형식이 예상과 다릅니다: {e}") from e


def run_advice(pop, threshold):
    """강수 확률로 러닝 장소를 추천한다. (판정, 설명)"""
    if pop >= threshold:
        return "트레드밀", "비 예보 → 실내 트레드밀 러닝 추천"
    if pop >= threshold // 2:
        return "야외(주의)", "비 가능성 있음 → 야외 러닝하되 트레드밀을 대비책으로"
    return "야외", "맑음/흐림 → 야외 러닝 추천"


def arrange_slots(avail_days, gym_cnt, run_cnt, weather):
    """러닝은 강수 확률이 낮은 요일부터, 헬스는 나머지 요일에 배치한다."""
    by_dry = sorted(avail_days, key=lambda d: (weather[d]["pop"], DAYS.index(d)))
    run_days = set(by_dry[:run_cnt])
    others = [d for d in avail_days if d not in run_days]
    gym_days = set(others[:gym_cnt])
    return {d: "러닝" if d in run_days else "헬스" if d in gym_days else "휴식(리커버리)"
            for d in avail_days}
