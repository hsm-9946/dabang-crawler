from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
from loguru import logger
import subprocess
import json
import sys
import os
import locale
from pathlib import Path as _P

# GUI 모드에서 터미널 창 숨기기
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# 한국어 로케일 설정
try:
    locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Korean_Korea.949')
    except:
        pass

# Ensure project root in path for direct execution
ROOT = _P(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402
from app.widgets.region_picker import RegionPicker  # noqa: E402
from app.updater import check_updates  # noqa: E402


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        
        # Windows 스타일 적용
        self._apply_windows_style()
        
        self.title("다방 매물 수집기 v2.0 - TypeScript 기반 개선")
        self.geometry("1200x900")
        
        # Windows 작업 표시줄 아이콘 설정
        self._set_taskbar_icon()
        
        # 한국어 폰트 최적화
        self._setup_korean_fonts()

        # state
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_output: Optional[Path] = None
        self._process: Optional[subprocess.Popen] = None

        # widgets
        self._build_widgets()
        
        # 업데이트 체크
        self._check_updates()

    def _apply_windows_style(self):
        """Windows 네이티브 스타일 적용"""
        try:
            # Windows 10/11 스타일 적용
            self.tk.call('source', 'azure.tcl')
            self.tk.call('set_theme', 'light')
        except:
            # 기본 Windows 스타일
            self.style = ttk.Style()
            self.style.theme_use('clam')
            
            # 한국어 폰트 설정
            self.style.configure('.', font=('맑은 고딕', 9))
            self.style.configure('Title.TLabel', font=('맑은 고딕', 12, 'bold'))
            self.style.configure('Header.TLabel', font=('맑은 고딕', 10, 'bold'))
            self.style.configure('Button.TButton', font=('맑은 고딕', 9))
            self.style.configure('Checkbutton.TCheckbutton', font=('맑은 고딕', 9))

    def _set_taskbar_icon(self):
        """Windows 작업 표시줄 아이콘 설정"""
        try:
            icon_path = ROOT / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except:
            pass

    def _setup_korean_fonts(self):
        """한국어 폰트 최적화"""
        # Windows 기본 한국어 폰트들
        korean_fonts = [
            '맑은 고딕',
            'Malgun Gothic', 
            'NanumGothic',
            'NanumBarunGothic',
            'Dotum',
            'Gulim'
        ]
        
        # 사용 가능한 폰트 찾기
        available_fonts = list(tk.font.families())
        for font in korean_fonts:
            if font in available_fonts:
                self.default_font = font
                break
        else:
            self.default_font = 'TkDefaultFont'

    def _check_updates(self):
        """업데이트 체크 (백그라운드)"""
        def check():
            try:
                update_available = check_updates()
                if update_available:
                    self.after(0, lambda: messagebox.showinfo(
                        "업데이트 알림", 
                        "새로운 버전이 있습니다!\nGitHub에서 최신 버전을 다운로드하세요."
                    ))
            except:
                pass
        
        threading.Thread(target=check, daemon=True).start()

    def _build_widgets(self) -> None:
        pad = 8
        
        # 제목
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=pad, pady=pad)
        ttk.Label(title_frame, text="🏠 다방 매물 수집기 v2.0 - TypeScript 기반 개선", 
                 style="Title.TLabel").pack()

        # 매물 유형 선택 (다중 선택 가능)
        property_frame = ttk.LabelFrame(self, text="매물 유형 (다중 선택 가능)")
        property_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        self.property_types = {
            "원룸": tk.BooleanVar(value=True),
            "투룸": tk.BooleanVar(value=False),
            "아파트": tk.BooleanVar(value=False),
            "주택/빌라": tk.BooleanVar(value=False),
            "오피스텔": tk.BooleanVar(value=False)
        }
        
        for i, (text, var) in enumerate(self.property_types.items()):
            ttk.Checkbutton(property_frame, text=text, variable=var).grid(row=0, column=i, padx=pad, pady=pad)

        # 지역 선택
        region_frame = ttk.LabelFrame(self, text="지역 선택")
        region_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        ttk.Label(region_frame, text="지역:").grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        self.region_picker = RegionPicker(region_frame)
        self.region_picker.grid(row=0, column=1, columnspan=3, sticky="ew", padx=pad, pady=pad)

        # 수집 설정
        settings_frame = ttk.LabelFrame(self, text="수집 설정")
        settings_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        # 최대 수집 건수
        ttk.Label(settings_frame, text="최대 수집 건수:").grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        self.var_limit = tk.StringVar(value="50")
        ttk.Entry(settings_frame, textvariable=self.var_limit, width=10).grid(row=0, column=1, padx=pad, pady=pad, sticky="w")
        
        # 브라우저 설정
        ttk.Label(settings_frame, text="브라우저:").grid(row=0, column=2, padx=pad, pady=pad, sticky="w")
        self.var_headless = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Headless 모드", variable=self.var_headless).grid(row=0, column=3, padx=pad, pady=pad, sticky="w")
        
        # 자동 엑셀 열기 설정
        self.var_auto_open_excel = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="완료 후 엑셀 자동 열기", variable=self.var_auto_open_excel).grid(row=1, column=0, columnspan=2, padx=pad, pady=pad, sticky="w")

        # 저장 경로
        save_frame = ttk.LabelFrame(self, text="저장 설정")
        save_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        ttk.Label(save_frame, text="저장 경로:").grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        self.var_outdir = tk.StringVar(value=str(Path(settings.paths.output).absolute()))
        ttk.Entry(save_frame, textvariable=self.var_outdir, width=50).grid(row=0, column=1, padx=pad, pady=pad, sticky="ew")
        ttk.Button(save_frame, text="경로 설정", command=self._choose_dir).grid(row=0, column=2, padx=pad, pady=pad)

        # 실행 버튼
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        # 업데이트 체크 버튼
        update_frame = ttk.Frame(self)
        update_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        ttk.Button(update_frame, text="🔄 업데이트 체크", 
                  command=self._check_updates).pack(side=tk.LEFT, padx=pad)
        
        self.start_btn = ttk.Button(control_frame, text="🚀 수집 시작", command=self._on_start)
        self.start_btn.pack(side=tk.LEFT, padx=pad)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹️ 중지", command=self._on_stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=pad)
        
        ttk.Button(control_frame, text="📊 엑셀 파일 열기", command=self._open_latest_excel).pack(side=tk.RIGHT, padx=pad)
        ttk.Button(control_frame, text="📁 결과 폴더 열기", command=self._open_folder).pack(side=tk.RIGHT, padx=pad)

        # 진행 상황
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=pad, pady=pad)
        
        self.progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, pad))
        
        self.var_status = tk.StringVar(value="대기 중")
        ttk.Label(progress_frame, textvariable=self.var_status, width=20).pack(side=tk.RIGHT)

        # 로그 표시
        log_frame = ttk.LabelFrame(self, text="실시간 로그")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)
        
        # 로그 텍스트 위젯과 스크롤바
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)
        
        self.log_text = tk.Text(log_container, height=20, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 로그 컨트롤
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.pack(fill=tk.X, padx=pad, pady=(0, pad))
        
        ttk.Button(log_control_frame, text="🗑️ 로그 지우기", command=self._clear_log).pack(side=tk.LEFT)
        ttk.Button(log_control_frame, text="💾 로그 저장", command=self._save_log).pack(side=tk.LEFT, padx=pad)

    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory()
        if chosen:
            self.var_outdir.set(chosen)

    def _append_log(self, msg: str) -> None:
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.update_idletasks()  # GUI 업데이트 강제

    def _clear_log(self) -> None:
        self.log_text.delete(1.0, tk.END)

    def _save_log(self) -> None:
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))

    def _on_start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
            
        # 지역 선택 확인
        sel = self.region_picker.get_selected()
        region_query = sel.get("query")
        if not region_query:
            messagebox.showerror("오류", "지역을 선택해주세요.")
            return
            
        self._stop.clear()
        self.progress.start(10)
        self.var_status.set("수집 중...")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _on_stop(self) -> None:
        self._stop.set()
        self.var_status.set("중지 요청")

        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except:
                self._process.kill()
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress.stop()

    def _open_folder(self) -> None:
        outdir = Path(self.var_outdir.get())
        if outdir.exists():
            import webbrowser
            webbrowser.open(f"file://{outdir.absolute()}")
        else:
            messagebox.showinfo("안내", "저장 폴더가 존재하지 않습니다.")
    
    def _open_latest_excel(self) -> None:
        """최신 엑셀 파일을 찾아서 열기"""
        try:
            outdir = Path(self.var_outdir.get())
            if not outdir.exists():
                self._append_log("❌ 저장 폴더가 존재하지 않습니다.")
                return
            
            # 다방 엑셀 파일들 찾기 (dabang_로 시작하는 .xlsx 파일)
            excel_files = list(outdir.glob("dabang_*.xlsx"))
            if not excel_files:
                self._append_log("❌ 엑셀 파일을 찾을 수 없습니다.")
                return
            
            # 가장 최신 파일 선택 (수정 시간 기준)
            latest_file = max(excel_files, key=lambda f: f.stat().st_mtime)
            
            self._append_log(f"📊 엑셀 파일 열기: {latest_file.name}")
            
            # 운영체제별로 엑셀 파일 열기
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(latest_file)])
            elif system == "Windows":
                subprocess.run(["start", str(latest_file)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(latest_file)])
                
            self._append_log(f"✅ 엑셀 파일이 열렸습니다: {latest_file.name}")
            
        except Exception as e:
            self._append_log(f"❌ 엑셀 파일 열기 실패: {e}")
            logger.exception("엑셀 파일 열기 중 오류: {}", e)

    def _run(self) -> None:
        try:
            # 지역 쿼리 확정
            sel = self.region_picker.get_selected()
            region_query = sel.get("query")
            
            # 선택된 매물 유형들 확인
            selected_types = [name for name, var in self.property_types.items() if var.get()]
            if not selected_types:
                self._append_log("❌ 선택된 매물 유형이 없습니다.")
                return
            
            # Python 스크래퍼 실행
            self._append_log(f"🚀 다중 매물 유형 스크래퍼 시작")
            self._append_log(f"📍 지역: {region_query}")
            self._append_log(f"🏠 선택된 매물 유형: {', '.join(selected_types)}")
            self._append_log(f"📊 최대 수집 건수: {self.var_limit.get()}")
            self._append_log("─" * 80)
            
            # Python 스크래퍼 직접 실행
            from scraper.dabang_scraper import DabangScraper, ScrapeOptions
            from storage.exporter import save_to_excel
            
            all_items = []
            
            # 각 매물 유형별로 순차 실행
            for i, property_type in enumerate(selected_types):
                if self._stop.is_set():
                    break
                    
                self._append_log(f"\n📋 [{i+1}/{len(selected_types)}] {property_type} 크롤링 시작...")
                
                try:
                    # 스크래핑 옵션 설정
                    opts = ScrapeOptions(
                        region=region_query,
                        property_type=property_type,
                        price_min=0,
                        price_max=2000000,
                        max_items=int(self.var_limit.get()),
                        max_pages=5,
                        headless=self.var_headless.get(),
                    )
                    
                    # 스크래퍼 실행
                    scraper = DabangScraper(opts, self._stop)
                    items = scraper.run()
                    
                    if items:
                        all_items.extend(items)
                        self._append_log(f"✅ {property_type} 크롤링 완료! {len(items)}개 수집")
                        
                        # 개별 매물 유형 완료 후에도 엑셀 열기 (옵션에 따라)
                        if self.var_auto_open_excel.get():
                            self._append_log(f"📊 {property_type} 결과 확인을 위해 엑셀 파일을 여는 중...")
                            self._open_latest_excel()
                    else:
                        self._append_log(f"⚠️ {property_type} 크롤링 완료했지만 수집된 데이터가 없습니다.")
                        
                except Exception as e:
                    self._append_log(f"❌ {property_type} 크롤링 중 오류 발생: {e}")
                    logger.exception(f"{property_type} 크롤링 오류")
                    continue
                
                # 다음 매물 유형으로 넘어가기 전 잠시 대기
                if i < len(selected_types) - 1 and not self._stop.is_set():
                    self._append_log("⏳ 다음 매물 유형으로 넘어가는 중...")
                    import time
                    time.sleep(2)
                

                
                # 다음 매물 유형으로 넘어가기 전 잠시 대기
                if i < len(selected_types) - 1 and not self._stop.is_set():
                    self._append_log("⏳ 다음 매물 유형으로 넘어가는 중...")
                    import time
                    time.sleep(2)
            
            # 모든 매물 유형 완료
            if not self._stop.is_set() and all_items:
                self.var_status.set("완료")
                self._append_log(f"🎉 모든 매물 유형 크롤링이 완료되었습니다! 총 {len(all_items)}개 수집")
                
                # 최종 결과를 엑셀로 저장
                try:
                    output_path = Path(settings.paths.output)
                    output_file = save_to_excel(all_items, output_path, region_query)
                    self._append_log(f"📊 결과가 저장되었습니다: {output_file}")
                    
                    # 크롤링 완료 후 자동으로 엑셀 파일 열기 (옵션에 따라)
                    if self.var_auto_open_excel.get():
                        self._append_log("📊 결과 확인을 위해 엑셀 파일을 여는 중...")
                        self._open_latest_excel()
                    else:
                        self._append_log("📊 엑셀 자동 열기가 비활성화되어 있습니다.")
                        
                except Exception as e:
                    self._append_log(f"❌ 결과 저장 중 오류 발생: {e}")
                    logger.exception("결과 저장 오류")
            elif not all_items:
                self.var_status.set("완료")
                self._append_log("⚠️ 크롤링이 완료되었지만 수집된 데이터가 없습니다.")
            else:
                self.var_status.set("중단")
                self._append_log("⏹️ 크롤링이 중단되었습니다.")
            
        except Exception as e:
            logger.exception("실행 중 오류 발생: {}", e)
            self._append_log(f"❌ 오류 발생: {e}")
            self.var_status.set("오류")
        finally:
            self.progress.stop()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self._process = None
    
    def _check_updates(self) -> None:
        """업데이트 체크"""
        try:
            self._append_log("🔄 업데이트를 확인하는 중...")
            has_update, latest_version, download_url = check_updates()
            
            if has_update:
                self._append_log(f"📦 새로운 버전이 있습니다: {latest_version}")
                self._append_log(f"🔗 다운로드: {download_url}")
                
                # 업데이트 다운로드 확인
                if messagebox.askyesno("업데이트", 
                                     f"새로운 버전 {latest_version}이 있습니다.\n다운로드 페이지를 여시겠습니까?"):
                    import webbrowser
                    webbrowser.open(download_url)
            else:
                self._append_log("✅ 최신 버전을 사용 중입니다.")
                
        except Exception as e:
            logger.exception("업데이트 체크 중 오류: {}", e)
            self._append_log(f"❌ 업데이트 체크 실패: {e}")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()


