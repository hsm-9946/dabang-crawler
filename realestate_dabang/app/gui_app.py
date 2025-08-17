from __future__ import annotations

import queue
import threading
import tkinter.filedialog as fd
import webbrowser
from pathlib import Path
from typing import List

import customtkinter as ctk  # type: ignore[reportMissingImports]
from loguru import logger

from .config import ensure_dirs, OUTPUT_DIR
from .core.exporter import save_excel
from .core.filters import apply_filters
from .core.models import CrawlerInput
from .crawler.dabang_crawler import DabangCrawler, PauseSignal


class TkLogHandler:
    """loguru를 Text 위젯으로 보냄."""

    def __init__(self, text_widget: ctk.CTkTextbox) -> None:
        self.text_widget = text_widget
        self.queue: queue.Queue[str] = queue.Queue()
        logger.add(self._write_from_loguru, level="INFO")

    def _write_from_loguru(self, message) -> None:
        try:
            # message는 loguru의 Message 객체
            self.queue.put_nowait(str(message))
        except Exception:
            pass

    def pump(self) -> None:
        try:
            while True:
                msg = self.queue.get_nowait()
                self.text_widget.insert("end", msg)
                self.text_widget.insert("end", "\n")
                self.text_widget.see("end")
        except queue.Empty:
            return


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self.title("다방 매물 수집기")
        self.geometry("920x700")

        # 입력 필드
        self.region_var = ctk.StringVar(value="부산 기장")
        self.price_min_var = ctk.StringVar(value="0")
        self.price_max_var = ctk.StringVar(value="2000000")

        self.type_vars = {
            "원룸": ctk.BooleanVar(value=True),
            "투룸": ctk.BooleanVar(value=False),
            "오피스텔": ctk.BooleanVar(value=False),
            "아파트": ctk.BooleanVar(value=False),
            "주택": ctk.BooleanVar(value=False),
            "빌라": ctk.BooleanVar(value=False),
        }
        # 유형 변경 시 필터 패널 가시성 갱신
        for var in self.type_vars.values():
            try:
                var.trace_add("write", lambda *_: self._refresh_filter_visibility())
            except Exception:
                pass

        self.headless_var = ctk.BooleanVar(value=True)
        self.dedupe_var = ctk.BooleanVar(value=True)
        self.diagnostics_var = ctk.BooleanVar(value=False)

        # 분양 관련 필터(선택)
        self.sale_building_vars = {
            "아파트": ctk.BooleanVar(value=False),
            "오피스텔": ctk.BooleanVar(value=False),
            "도시형생활주택": ctk.BooleanVar(value=False),
        }
        self.sale_stage_vars = {
            "분양예정": ctk.BooleanVar(value=False),
            "접수중": ctk.BooleanVar(value=False),
            "접수마감": ctk.BooleanVar(value=False),
            "입주예정": ctk.BooleanVar(value=False),
        }
        self.sale_schedule_vars = {
            "모집공고": ctk.BooleanVar(value=False),
            "특별공급": ctk.BooleanVar(value=False),
            "1순위청약": ctk.BooleanVar(value=False),
            "2순위청약": ctk.BooleanVar(value=False),
            "청약접수": ctk.BooleanVar(value=False),
            "당첨자발표": ctk.BooleanVar(value=False),
            "계약기간": ctk.BooleanVar(value=False),
            "준공시기": ctk.BooleanVar(value=False),
        }
        self.sale_supply_vars = {
            "공공분양": ctk.BooleanVar(value=False),
            "민간분양": ctk.BooleanVar(value=False),
            "공공임대": ctk.BooleanVar(value=False),
            "민간임대": ctk.BooleanVar(value=False),
        }

        self.pause_signal = PauseSignal()
        self.worker: threading.Thread | None = None
        self.records_count = 0
        self.done_count = 0
        self.latest_output: Path | None = None
        self.advanced_visible = False

        self._build_ui()

        # 로깅 → Text
        self.tk_log_handler = TkLogHandler(self.log_text)
        self.after(200, self._poll_logs)

    def _build_ui(self) -> None:
        pad = 8
        frm = ctk.CTkFrame(self)
        frm.pack(fill="x", padx=pad, pady=pad)

        # 1행: 지역/가격
        ctk.CTkLabel(frm, text="지역").grid(row=0, column=0, padx=pad, pady=pad)
        ctk.CTkEntry(frm, textvariable=self.region_var, width=220).grid(row=0, column=1, padx=pad, pady=pad)

        ctk.CTkLabel(frm, text="최소가격").grid(row=0, column=2, padx=pad, pady=pad)
        ctk.CTkEntry(frm, textvariable=self.price_min_var, width=120).grid(row=0, column=3, padx=pad, pady=pad)
        ctk.CTkLabel(frm, text="최대가격").grid(row=0, column=4, padx=pad, pady=pad)
        ctk.CTkEntry(frm, textvariable=self.price_max_var, width=120).grid(row=0, column=5, padx=pad, pady=pad)

        # 2행: 유형 체크박스
        ctk.CTkLabel(frm, text="유형").grid(row=1, column=0, padx=pad, pady=pad)
        col = 1
        for name, var in self.type_vars.items():
            ctk.CTkCheckBox(frm, text=name, variable=var).grid(row=1, column=col, padx=pad, pady=pad)
            col += 1

        # 3행: 옵션
        ctk.CTkCheckBox(frm, text="Headless", variable=self.headless_var).grid(row=2, column=1, padx=pad, pady=pad)
        ctk.CTkCheckBox(frm, text="중복제거", variable=self.dedupe_var).grid(row=2, column=2, padx=pad, pady=pad)
        ctk.CTkCheckBox(frm, text="진단 모드", variable=self.diagnostics_var).grid(row=2, column=3, padx=pad, pady=pad)

        # 버튼 행 (다방 상단바 유사: 실행/토글을 상단에 배치)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=pad, pady=pad)
        self.start_btn = ctk.CTkButton(btn_frame, text="수집 시작", command=self.on_start)
        self.start_btn.pack(side="left", padx=pad)
        self.stop_btn = ctk.CTkButton(btn_frame, text="중지", command=self.on_stop, fg_color="#ad2e24")
        self.stop_btn.pack(side="left", padx=pad)
        self.resume_btn = ctk.CTkButton(btn_frame, text="재개", command=self.on_resume, fg_color="#3b7ddd")
        self.resume_btn.pack(side="left", padx=pad)
        self.adv_btn = ctk.CTkButton(btn_frame, text="추가필터 ▼", command=self.on_toggle_advanced)
        self.adv_btn.pack(side="left", padx=pad)
        self.open_btn = ctk.CTkButton(btn_frame, text="엑셀 열기", command=self.on_open_excel)
        self.open_btn.pack(side="right", padx=pad)

        # 진행/로그
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=pad, pady=pad)
        self.progress_label = ctk.CTkLabel(info_frame, text="진행: 0건")
        self.progress_label.pack(side="left", padx=pad)

        self.path_label = ctk.CTkLabel(info_frame, text=f"저장경로: {OUTPUT_DIR}")
        self.path_label.pack(side="right", padx=pad)

        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=pad, pady=pad)
        self.log_text = ctk.CTkTextbox(body)
        self.log_text.pack(fill="both", expand=True)

        # 원룸/투룸 관련 필터(안내 위주, 기본 접힘)
        room = ctk.CTkFrame(self)
        self.room_frame = room
        ctk.CTkLabel(room, text="방구조: 원룸/투룸 관련 필터", font=("", 13, "bold")).grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        ctk.CTkLabel(room, text="원룸 선택 시 '추가필터 > 방구조 > 원룸'을 자동 적용합니다.").grid(row=1, column=0, padx=pad, pady=pad, sticky="w")

        # 분양 필터 구역 (기본 접힘)
        sale = ctk.CTkFrame(self)
        self.sale_frame = sale
        ctk.CTkLabel(sale, text="분양 건물유형").grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        col = 1
        for name, var in self.sale_building_vars.items():
            ctk.CTkCheckBox(sale, text=name, variable=var).grid(row=0, column=col, padx=pad, pady=pad)
            col += 1

        ctk.CTkLabel(sale, text="분양 단계").grid(row=1, column=0, padx=pad, pady=pad, sticky="w")
        col = 1
        for name, var in self.sale_stage_vars.items():
            ctk.CTkCheckBox(sale, text=name, variable=var).grid(row=1, column=col, padx=pad, pady=pad)
            col += 1

        ctk.CTkLabel(sale, text="분양 일정").grid(row=2, column=0, padx=pad, pady=pad, sticky="w")
        col = 1
        for name, var in self.sale_schedule_vars.items():
            ctk.CTkCheckBox(sale, text=name, variable=var).grid(row=2, column=col, padx=pad, pady=pad)
            col += 1

        ctk.CTkLabel(sale, text="공급 유형").grid(row=3, column=0, padx=pad, pady=pad, sticky="w")
        col = 1
        for name, var in self.sale_supply_vars.items():
            ctk.CTkCheckBox(sale, text=name, variable=var).grid(row=3, column=col, padx=pad, pady=pad)
            col += 1

        # 저장 경로 선택 버튼
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(fill="x", padx=pad, pady=pad)
        ctk.CTkButton(path_frame, text="저장 경로 변경", command=self.on_change_output).pack(side="left")

    def _poll_logs(self) -> None:
        self.tk_log_handler.pump()
        self.progress_label.configure(text=f"진행: {self.done_count}건 완료")
        self.after(300, self._poll_logs)

    def _collect_types(self) -> List[str]:
        return [k for k, v in self.type_vars.items() if v.get()]

    def _collect_selected(self, mapping: dict[str, ctk.BooleanVar]) -> List[str]:
        return [k for k, v in mapping.items() if v.get()]

    def _run_worker(self) -> None:
        try:
            types = self._collect_types()
            price_min = int(self.price_min_var.get() or "0")
            price_max_str = self.price_max_var.get().strip()
            price_max = int(price_max_str) if price_max_str else None

            user_input = CrawlerInput(
                region_keyword=self.region_var.get().strip(),
                price_min=price_min,
                price_max=price_max,
                property_types=types,
                headless=self.headless_var.get(),
                dedupe=self.dedupe_var.get(),
                diagnostics=self.diagnostics_var.get(),
                sale_building_types=self._collect_selected(self.sale_building_vars),
                sale_stages=self._collect_selected(self.sale_stage_vars),
                sale_schedules=self._collect_selected(self.sale_schedule_vars),
                sale_supply_types=self._collect_selected(self.sale_supply_vars),
            )

            crawler = DabangCrawler(
                user_input,
                pause_signal=self.pause_signal,
                progress_callback=lambda m: None,
            )
            records, total_cards = crawler.run()
            self.done_count = len(records)
            filtered = apply_filters(records, user_input)
            self.done_count = len(filtered)
            output = save_excel(filtered, user_input.region_keyword, dedupe=user_input.dedupe)
            self.latest_output = output
            self.path_label.configure(text=f"저장경로: {output}")
            logger.success(f"완료. 카드 {total_cards}개 중 {len(filtered)}건 저장")
        except Exception as e:  # noqa: BLE001
            logger.exception("작업 실패: {}", e)
        finally:
            self.start_btn.configure(state="normal")

    def on_start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        self.done_count = 0
        self.pause_signal = PauseSignal()
        self.start_btn.configure(state="disabled")
        self.worker = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.start()

    def on_stop(self) -> None:
        self.pause_signal.request_stop()

    def on_resume(self) -> None:
        self.pause_signal.resume()

    def on_change_output(self) -> None:
        chosen = fd.askdirectory(title="출력 폴더 선택")
        if chosen:
            from . import config as cfg

            cfg.OUTPUT_DIR = Path(chosen)
            self.path_label.configure(text=f"저장경로: {cfg.OUTPUT_DIR}")

    def on_open_excel(self) -> None:
        if self.latest_output and self.latest_output.exists():
            webbrowser.open(self.latest_output.as_uri())

    def on_toggle_advanced(self) -> None:
        if self.advanced_visible:
            try:
                self.sale_frame.pack_forget()
                self.room_frame.pack_forget()
            except Exception:
                pass
            self.advanced_visible = False
            self.adv_btn.configure(text="추가필터 ▼")
        else:
            self.advanced_visible = True
            self._refresh_filter_visibility()
            self.advanced_visible = True
            self.adv_btn.configure(text="추가필터 ▲")

    def _refresh_filter_visibility(self) -> None:
        # 접힘 상태면 모두 숨김
        if not self.advanced_visible:
            try:
                self.sale_frame.pack_forget()
                self.room_frame.pack_forget()
            except Exception:
                pass
            return

        # 어떤 유형이 선택되었는지에 따라 패널 전환
        selected_types = {k for k, v in self.type_vars.items() if v.get()}
        # 우선순위: 원룸/투룸 → room_frame, 그 외(아파트/오피스텔/주택/빌라) → sale_frame
        show_room = bool({"원룸", "투룸"} & selected_types)
        show_sale = bool({"아파트", "오피스텔", "주택", "빌라"} & selected_types)

        try:
            self.sale_frame.pack_forget()
            self.room_frame.pack_forget()
        except Exception:
            pass

        if show_room and not show_sale:
            try:
                self.room_frame.pack(fill="x", padx=8, pady=8)
            except Exception:
                pass
        elif show_sale:
            try:
                self.sale_frame.pack(fill="x", padx=8, pady=8)
            except Exception:
                pass


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()


