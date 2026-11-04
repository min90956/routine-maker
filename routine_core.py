"""
루틴 생성 로직 (GUI와 분리)
- 불가 요일 제외 및 헬스/러닝 분배, 지난주 강도 반영 종목 배정
- 날씨 정보가 있으면 러닝을 비 올 확률이 낮은 요일에 배치하고 장소를 추천
"""
import weather as wx

DAYS = ["월", "화", "수", "목", "금", "토", "일"]
PARTS = ["가슴", "등", "하체", "어깨/팔"]

EXERCISES = {
    "가슴": [("바벨 벤치프레스", "바벨 & 플랫 벤치", "덤벨 벤치프레스 / 푸시업"),
            ("인클라인 덤벨 프레스", "인클라인 벤치 & 덤벨", "체스트 프레스 머신"),
            ("딥스 & 펙덱 플라이", "딥스 바 / 펙덱 머신", "케이블 크로스오버 / 밴드")],
    "등": [("랫 풀다운", "랫 풀다운 머신", "풀업(턱걸이) / 튜빙 밴드"),
          ("바벨 벤트오버 로우", "바벨 & 원판", "원암 덤벨 로우 / 시티드 로우"),
          ("시티드 케이블 로우", "케이블 머신", "인버티드 로우 / 덤벨 로우")],
    "하체": [("바벨 백스쿼트", "파워랙 & 바벨", "덤벨 고블렛 스쿼트 / 레그 프레스"),
            ("레그 프레스", "레그 프레스 머신", "불가리안 스플릿 스쿼트 / 런지"),
            ("레그 익스텐션 & 컬", "레그 머신", "덤벨 스티프 데드리프트 / 맨몸 스쿼트")],
    "어깨/팔": [("오버헤드 덤벨 프레스", "덤벨 & 조절식 벤치", "바벨 밀리터리 프레스 / 머신"),
              ("사이드 레터럴 레이즈", "덤벨", "케이블 사이드 레이즈 / 밴드"),
              ("바벨 컬 & 트라이셉스 익스텐션", "이지바(EZ-bar)", "덤벨 컬 & 벤치 딥스")]
}
RUN_SESSIONS = [
    ("지속주 (조깅 / LSD)", "야외 트랙 / 공원 로드", "실내 트레드밀 / 실내 자전거"),
    ("인터벌 러닝 (고강도)", "우레탄 400m 트랙", "트레드밀 속도 조절 / 로잉머신"),
    ("템포런 (페이스 감각 훈련)", "평지 로드 코스", "트레드밀 인터벌 모드")
]
CHEERS = [
    "꾸준함이 최고의 재능입니다!!!! 이번 주도 부상 없이 득근 & 안전 러닝하세요! (파이팅!)",
    "시작이 반입니다! 오늘 세운 루틴을 즐기며 활기차고 멋진 한 주 보내세요!",
    "건강한 땀방울은 절대 배신하지 않습니다. 이번 주 목표 완주를 진심으로 응원합니다!"
]

def default_slots(avail, gym_cnt, run_cnt):
    """날씨 정보가 없을 때: 헬스 → 러닝 → 휴식 순서로 번갈아 배치"""
    g_pool, r_pool = ["헬스"] * gym_cnt, ["러닝"] * run_cnt
    rest_pool = ["휴식(리커버리)"] * (len(avail) - gym_cnt - run_cnt)
    slots = []
    while g_pool or r_pool or rest_pool:
        if g_pool: slots.append(g_pool.pop(0))
        if r_pool: slots.append(r_pool.pop(0))
        if rest_pool: slots.append(rest_pool.pop(0))
    return dict(zip(avail, slots))

def weather_line(w):
    return (f"  ☂ 날씨({w['date']:%m/%d}): 강수확률 {w['pop']}% · 강수량 {w['rain_mm']}mm"
            f" · {w['tmin']:.0f}~{w['tmax']:.0f}°C")

def generate_routine_text(unavail_days, gym_goal, run_goal, part_intensities, weather=None, settings=None):
    avail = [d for d in DAYS if d not in unavail_days]
    if not avail:
        return "선택 가능한 요일이 없습니다. 운동 불가 요일을 다시 확인해주세요."
    total = gym_goal + run_goal
    notice = ""
    if total > len(avail):
        scale = len(avail) / total
        gym_cnt = max(1 if gym_goal > 0 else 0, round(gym_goal * scale))
        run_cnt = len(avail) - gym_cnt
        notice = f"[안내] 가능 요일({len(avail)}일)에 맞춰 헬스 {gym_cnt}회, 러닝 {run_cnt}회로 자동 분배되었습니다.\n\n"
    else:
        gym_cnt, run_cnt = gym_goal, run_goal

    if weather:
        slot_map = wx.arrange_slots(avail, gym_cnt, run_cnt, weather)
        dates = [w["date"] for w in weather.values()]
        notice += (f"[날씨 반영] {settings['location']} {dates[0]:%m/%d}~{dates[-1]:%m/%d} 예보 기준, "
                   f"러닝은 비 올 확률이 낮은 요일에 배치 (트레드밀 기준: {settings['threshold']}% 이상)\n\n")
    else:
        slot_map = default_slots(avail, gym_cnt, run_cnt)

    weight = {"미수행": 0, "중강도": 1, "고강도": 2}
    sorted_parts = sorted(PARTS, key=lambda p: weight.get(part_intensities.get(p, "미수행"), 0))
    lines = [notice + "=" * 62, "      [ 주간 맞춤형 헬스 & 러닝 스마트 루틴 ]", "=" * 62]
    part_idx, run_idx = 0, 0

    for day in DAYS:
        if day in unavail_days:
            lines.append(f"\n【 {day}요일 】 [X] 운동 불가 (개인 일정 및 휴식)")
            continue
        act = slot_map.get(day, "휴식(리커버리)")
        lines.append(f"\n【 {day}요일 】 ★ [{act}]")
        if weather:
            lines.append(weather_line(weather[day]))
        if act == "헬스":
            part = sorted_parts[part_idx % len(sorted_parts)]
            part_idx += 1
            ex_list = EXERCISES[part]
            intensity = part_intensities.get(part, "미수행")
            offset = 1 if intensity == "고강도" else (2 if intensity == "중강도" else 0)
            main_ex, sub_ex = ex_list[offset % len(ex_list)], ex_list[(offset + 1) % len(ex_list)]
            lines.extend([
                f"  ▶ 집중 부위: {part} (지난주: {intensity} 반영 맞춤 배정)",
                "  [운동 순서 및 세부 가이드]",
                "  1. 웜업: 전신 동적 스트레칭 & 모빌리티 (5분)",
                f"  2. 메인 종목: {main_ex[0]} (추천: {main_ex[1]} / 대체: {main_ex[2]})",
                f"  3. 보조 종목: {sub_ex[0]} (추천: {sub_ex[1]} / 대체: {sub_ex[2]})",
                "  4. 쿨다운: 코어 플랭크(3세트) & 정적 스트레칭 (5분)"
            ])
        elif act == "러닝":
            run_ex = RUN_SESSIONS[run_idx % len(RUN_SESSIONS)]
            run_idx += 1
            place = f"추천 장소/기구: {run_ex[1]} | 대체 장소/기구: {run_ex[2]}"
            if weather:
                verdict, why = wx.run_advice(weather[day]["pop"], settings["threshold"])
                lines.append(f"  ▶ 장소 추천: [{verdict}] {why}")
                if verdict == "트레드밀":
                    place = f"추천 장소/기구: {run_ex[2]} (우천) | 대체: 날씨가 개면 {run_ex[1]}"
            lines.extend([
                f"  ▶ 러닝 세션: {run_ex[0]}",
                "  [운동 순서 및 세부 가이드]",
                "  1. 웜업: 하체 관절 회전 & 가벼운 피치 훈련 (5분)",
                f"  2. 본 러닝: {run_ex[0]} (30~45분, 적정 페이스 유지)",
                f"     - {place}",
                "  3. 쿨다운: 햄스트링/종아리 스트레칭 및 폼롤러 (5분)"
            ])
        else:
            lines.append("  ▶ 가벼운 산책(20분) 및 전신 폼롤러 이완 권장")

    lines.append("\n" + "=" * 62)
    return "\n".join(lines)
