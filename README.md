# 주간 헬스 & 러닝 스마트 루틴 메이커 (날씨 API 버전)

운동 불가 요일, 목표 횟수, 지난주 부위별 강도를 입력하면 **다음 주(월~일)** 헬스·러닝 루틴을 짜 주는 데스크톱(tkinter) 프로그램입니다.
이번 업데이트에서 **Open-Meteo 날씨 API**를 붙여, 강수 확률을 보고 러닝 요일을 정하고 **야외 러닝 / 트레드밀**을 추천합니다.

## 1. 실행 방법 (uv)
```bash
git clone https://github.com/min90956/routine-maker.git
cd routine-maker
uv sync                       # Python 3.14 가상환경 생성 (외부 패키지 없음)
uv run smart_routine_maker.py # 프로그램 실행
```
- 필요한 것: [uv](https://docs.astral.sh/uv/), 인터넷 연결(날씨 기능 사용 시)
- 외부 라이브러리 없이 표준 라이브러리(`tkinter`, `urllib`, `json`)만 사용합니다.

## 2. API 키 / `.env` 설정
**Open-Meteo는 API 키가 필요 없습니다.** 따라서 제출할 키도 없습니다.
위치와 기준값만 `.env`로 바꿀 수 있고, `.env`가 없으면 기본값(서울, 60%)으로 동작합니다.

```bash
cp .env.example .env   # Windows PowerShell: copy .env.example .env
```
`.env` 형식 (`KEY=VALUE`, 한 줄에 하나):
```
WEATHER_LOCATION_NAME=서울
WEATHER_LAT=37.5665
WEATHER_LON=126.9780
RAIN_THRESHOLD=60
```
| 키 | 의미 | 기본값 |
|---|---|---|
| `WEATHER_LOCATION_NAME` | 결과에 표시할 지역 이름 | 서울 |
| `WEATHER_LAT`, `WEATHER_LON` | 예보를 조회할 위도/경도 | 서울시청 |
| `RAIN_THRESHOLD` | 이 강수 확률(%) 이상이면 트레드밀 추천 | 60 |

`.env`는 `.gitignore`에 등록되어 있어 저장소에 올라가지 않습니다.

## 3. 사용 방법
1. 운동 불가 요일 체크, 헬스/러닝 목표 횟수 입력, 지난주 부위별 강도 선택
2. **4. 다음 주 날씨 반영**(기본 켜짐) 확인 후 `★ 다음 주 루틴 자동 생성`
3. 결과 확인 후 `[저장 후 종료]` → `weekly_workout_routine.txt`로 저장되고 응원 메시지와 함께 종료

출력 예시 (러닝 날):
```
【 목요일 】 ★ [러닝]
  ☂ 날씨(11/12): 강수확률 5% · 강수량 0.0mm · 6~15°C
  ▶ 장소 추천: [야외] 맑음/흐림 → 야외 러닝 추천
```

## 4. 파일 구성
| 파일 | 역할 |
|---|---|
| `smart_routine_maker.py` | 실행 파일. tkinter 화면, 입력 처리, 날씨 조회 호출, 파일 저장 |
| `routine_core.py` | 루틴 생성 로직. 운동 데이터, 요일 배치, 종목/기구 배정, 결과 문자열 생성 |
| `weather.py` | 날씨 API 모듈. `.env` 읽기, 다음 주 날짜 계산, API 호출/응답 파싱, 러닝 추천 규칙 |
| `api-plan.md` | 이번 API 적용 기획안 |
| `plan-2.md`, `new_plan.md` | 이전 주차 기획안 |
| `CONVERSATION_*.md` | AI와 나눈 대화 원문 |
| `.env.example` | `.env` 작성 예시 |

기획안의 "한 파일 200줄 이하, 최대 3개 파일" 제약에 맞춰 화면/로직/API를 3개 파일로 나눴습니다.

## 5. 코드 동작 설명

### 5-1. 날씨 가져오기 (`weather.py`)
- `next_week_dates()` : 오늘 요일(`weekday()`)로 다음 주 월요일을 계산해 월~일 7개 날짜를 만듭니다.
- `fetch_weekly_weather(lat, lon, dates)` : 아래 형태로 요청을 보냅니다.
  ```
  https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..
    &daily=precipitation_probability_max,precipitation_sum,temperature_2m_max,temperature_2m_min
    &timezone=Asia/Seoul&start_date=다음주월요일&end_date=다음주일요일
  ```
  `urllib.request.urlopen`으로 받은 JSON을 `parse_daily()`가 `{"월": {"date", "pop", "rain_mm", "tmax", "tmin"}, ...}` 형태로 바꿉니다.
- 네트워크 오류나 응답 형식 오류는 모두 `WeatherError`로 바꿔 던집니다. 화면 쪽에서 이를 잡아 경고만 띄우고 **날씨 없이 기본 루틴**을 만들기 때문에 프로그램이 멈추지 않습니다.

### 5-2. 러닝 요일 배치 (`weather.arrange_slots`)
가능한 요일을 **강수 확률이 낮은 순**으로 정렬해 앞에서부터 러닝 횟수만큼 러닝으로 정하고, 남은 요일에 헬스(실내 운동)를, 그래도 남으면 휴식을 넣습니다.
날씨를 쓰지 않으면 기존처럼 `default_slots()`가 헬스 → 러닝 → 휴식 순서로 번갈아 배치합니다.

### 5-3. 야외/트레드밀 추천 (`weather.run_advice`)
| 강수 확률 | 판정 |
|---|---|
| `RAIN_THRESHOLD` 이상 | 트레드밀 (추천 장소와 대체 장소를 서로 바꿔 표시) |
| 기준의 절반 이상 | 야외(주의), 트레드밀을 대비책으로 |
| 그 미만 | 야외 |

러닝 횟수가 맑은 날보다 많아 비 오는 날에도 러닝이 잡히는 경우, 이 규칙으로 트레드밀을 추천합니다.

### 5-4. 기존 기능 (`routine_core.generate_routine_text`)
- 불가 요일 제외, 목표 횟수가 가능 요일보다 많으면 비율대로 줄여 재분배
- 지난주 강도가 낮은 부위부터 배정하고, 강도에 따라 메인/보조 종목을 바꿔 같은 종목 반복을 피함
- 종목마다 추천 기구와 대체 기구 표시

## 6. 한계
- 예보 특성상 다음 주 후반(6~10일 뒤)은 정확도가 떨어집니다.
- 위치는 `.env`의 위도/경도로만 지정합니다(도시 이름 검색 없음).
