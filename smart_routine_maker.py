"""
주간 헬스 & 러닝 맞춤형 스마트 루틴 메이커 (실행 파일, tkinter GUI)
- 불가 요일 제외 및 헬스/러닝 최적 분배
- 지난주 기록(부위별 강도) 연계: 부위 분산, 순서, 추천/대체 기구 매칭
- 로컬 텍스트 파일 저장 및 응원 메시지와 함께 종료
- [API] 다음 주 날씨(강수 확률)로 러닝 요일 배치 및 야외/트레드밀 추천
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random, os
import weather as wx
from routine_core import DAYS, PARTS, CHEERS, generate_routine_text

class RoutineApp:
    def __init__(self, root):
        self.root = root
        self.root.title("주간 헬스 & 러닝 맞춤형 스마트 루틴 메이커")
        self.root.geometry("880x660")
        self.root.minsize(820, 600)
        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="[ 주간 헬스 & 러닝 맞춤형 스마트 루틴 메이커 ]",
                 font=("Malgun Gothic", 13, "bold"), bg="#2c3e50", fg="white", pady=8).pack(fill="x")
        paned = tk.PanedWindow(self.root, orient="horizontal", sashrelief="groove")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        left = tk.Frame(paned, padx=4, pady=4)
        paned.add(left, width=330)

        # 1. 불가 요일
        lf1 = tk.LabelFrame(left, text="1. 운동 불가 요일 선택", font=("Malgun Gothic", 9, "bold"), padx=5, pady=4)
        lf1.pack(fill="x", pady=3)
        self.unavail_vars = {}
        row_f = tk.Frame(lf1)
        row_f.pack(fill="x")
        for d in DAYS:
            var = tk.BooleanVar()
            self.unavail_vars[d] = var
            tk.Checkbutton(row_f, text=d, variable=var).pack(side="left", expand=True)

        # 2. 목표 횟수
        lf2 = tk.LabelFrame(left, text="2. 이번 주 목표 횟수(회)", font=("Malgun Gothic", 9, "bold"), padx=5, pady=4)
        lf2.pack(fill="x", pady=3)
        f2 = tk.Frame(lf2)
        f2.pack(fill="x")
        tk.Label(f2, text="헬스:").pack(side="left")
        self.gym_spin = ttk.Spinbox(f2, from_=0, to=7, width=4)
        self.gym_spin.set(3)
        self.gym_spin.pack(side="left", padx=4)
        tk.Label(f2, text="러닝:").pack(side="left", padx=(8, 0))
        self.run_spin = ttk.Spinbox(f2, from_=0, to=7, width=4)
        self.run_spin.set(2)
        self.run_spin.pack(side="left", padx=4)

        # 3. 지난주 기록 및 강도
        lf3 = tk.LabelFrame(left, text="3. 지난주 헬스 종목 및 부위별 강도", font=("Malgun Gothic", 9, "bold"), padx=5, pady=4)
        lf3.pack(fill="x", pady=3)
        self.intensity_vars = {}
        for p in PARTS:
            row = tk.Frame(lf3)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{p:4s}:", width=7, anchor="w").pack(side="left")
            combo = ttk.Combobox(row, values=["미수행", "중강도", "고강도"], state="readonly", width=8)
            combo.set("미수행")
            combo.pack(side="left", padx=3)
            self.intensity_vars[p] = combo

        # 4. 날씨 API
        lf4 = tk.LabelFrame(left, text="4. 다음 주 날씨 반영 (Open-Meteo API)", font=("Malgun Gothic", 9, "bold"), padx=5, pady=4)
        lf4.pack(fill="x", pady=3)
        self.use_weather = tk.BooleanVar(value=True)
        tk.Checkbutton(lf4, text="강수 확률로 러닝/트레드밀 추천", variable=self.use_weather).pack(anchor="w")

        tk.Button(left, text="★ 다음 주 루틴 자동 생성", bg="#2980b9", fg="white",
                  font=("Malgun Gothic", 10, "bold"), command=self.on_generate).pack(fill="x", pady=8)

        # 우측 결과창
        right = tk.Frame(paned, padx=4, pady=4)
        paned.add(right)
        tk.Label(right, text="[ 맞춤 주간 루틴 결과 ]", font=("Malgun Gothic", 9, "bold")).pack(anchor="w")
        self.txt_result = scrolledtext.ScrolledText(right, wrap="word", font=("Consolas", 10))
        self.txt_result.pack(fill="both", expand=True, pady=4)
        tk.Button(right, text="[저장 후 종료] 텍스트 파일 저장", bg="#27ae60", fg="white",
                  font=("Malgun Gothic", 10, "bold"), pady=6, command=self.save_and_exit).pack(fill="x")

    def on_generate(self):
        unavail = [d for d, v in self.unavail_vars.items() if v.get()]
        try:
            g, r = int(self.gym_spin.get()), int(self.run_spin.get())
        except ValueError:
            messagebox.showerror("입력 오류", "목표 횟수는 숫자여야 합니다.")
            return
        intensities = {p: combo.get() for p, combo in self.intensity_vars.items()}
        weather, settings = None, None
        if self.use_weather.get():
            settings = wx.get_settings()
            try:
                weather = wx.fetch_weekly_weather(settings["lat"], settings["lon"], wx.next_week_dates())
            except wx.WeatherError as e:
                messagebox.showwarning("날씨 조회 실패", f"{e}\n\n날씨 없이 기본 루틴으로 생성합니다.")
        result = generate_routine_text(unavail, g, r, intensities, weather, settings)
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, result)

    def save_and_exit(self):
        content = self.txt_result.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("저장 불가", "먼저 [루틴 자동 생성]을 실행해주세요.")
            return
        out_path = os.path.abspath("weekly_workout_routine.txt")
        with open(out_path, "w", encoding="utf-8-sig") as f:
            f.write(content)
        cheer = random.choice(CHEERS)
        messagebox.showinfo("저장 완료 및 종료", f"스케줄이 성공적으로 저장되었습니다!\n\n경로: {out_path}\n\n[응원 메시지]\n{cheer}")
        self.root.destroy()

if __name__ == "__main__":
    tk_root = tk.Tk()
    app = RoutineApp(tk_root)
    tk_root.mainloop()
