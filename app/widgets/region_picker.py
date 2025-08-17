from __future__ import annotations

import json
import os
import re
import time
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


HANGUL_INITIALS = [
    "ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"
]


def initials(s: str) -> str:
    out = []
    for ch in s:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = (code - 0xAC00) // 588
            out.append(HANGUL_INITIALS[idx])
    return "".join(out)


def normalize_name(s: str) -> str:
    return re.sub(r"[^\w가-힣]", "", s or "").strip()


@dataclass
class RegionNode:
    code: str
    name: str
    children: List["RegionNode"]


class RegionIndex:
    def __init__(self, data: Dict) -> None:
        self.provinces: List[RegionNode] = [
            RegionNode(p["code"], p["name"], [RegionNode(c["code"], c["name"], [RegionNode(t["code"], t["name"], []) for t in c.get("children", [])]) for c in p.get("children", [])])
            for p in data.get("provinces", [])
        ]
        # 인덱스
        self.by_prefix: Dict[str, List[Tuple[str, str, str]]] = {}
        self.by_initial: Dict[str, List[Tuple[str, str, str]]] = {}
        self.by_contains: Dict[str, List[Tuple[str, str, str]]] = {}
        self._build()

    def _build(self) -> None:
        for p in self.provinces:
            for c in p.children:
                key = normalize_name(c.name)
                init = initials(c.name)
                triple = (p.code, c.code, c.name)
                self.by_prefix.setdefault(key[:1], []).append(triple)
                self.by_contains.setdefault(key, []).append(triple)
                self.by_initial.setdefault(init[:1], []).append(triple)

    def search(self, q: str, limit: int = 100) -> List[Tuple[str, str, str]]:
        qn = normalize_name(q)
        if not qn:
            return []
        results: List[Tuple[str, str, str]] = []
        # 1) 접두
        for k, arr in self.by_prefix.items():
            if qn.startswith(k):
                results.extend([t for t in arr if normalize_name(t[2]).startswith(qn)])
        if len(results) < limit:
            # 2) 포함
            for k, arr in self.by_contains.items():
                if qn in k:
                    results.extend(arr)
                    if len(results) >= limit:
                        break
        if len(results) < limit:
            # 3) 초성
            qi = initials(q)
            for k, arr in self.by_initial.items():
                if qi and qi.startswith(k):
                    results.extend([t for t in arr if initials(t[2]).startswith(qi)])
                    if len(results) >= limit:
                        break
        # 중복 제거
        seen = set()
        uniq: List[Tuple[str, str, str]] = []
        for t in results:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        return uniq[:limit]


class RegionPicker(ttk.Frame):
    def __init__(self, master, data_path: Optional[Path] = None) -> None:
        super().__init__(master)
        path = data_path or Path(__file__).resolve().parents[2] / "data" / "regions_kr.json"
        data = json.loads(Path(path).read_text("utf-8"))
        self.index = RegionIndex(data)

        self.var_prov = tk.StringVar()
        self.var_city = tk.StringVar()
        self.var_town = tk.StringVar()
        self.var_search = tk.StringVar()

        # widgets
        self.cb_prov = ttk.Combobox(self, state="readonly")
        self.cb_city = ttk.Combobox(self, state="readonly")
        self.cb_town = ttk.Combobox(self, state="readonly")
        self.entry = ttk.Entry(self, textvariable=self.var_search, width=24)
        self.listbox = tk.Listbox(self, height=6)

        self.cb_prov.grid(row=0, column=0, padx=4, pady=4)
        self.cb_city.grid(row=0, column=1, padx=4, pady=4)
        self.cb_town.grid(row=0, column=2, padx=4, pady=4)
        self.entry.grid(row=0, column=3, padx=6, pady=4)
        self.listbox.grid(row=1, column=0, columnspan=4, sticky="ew")

        self._fill_provinces()
        self.cb_prov.bind("<<ComboboxSelected>>", self._on_prov)
        self.cb_city.bind("<<ComboboxSelected>>", self._on_city)
        self.cb_town.bind("<<ComboboxSelected>>", self._on_town)
        self.entry.bind("<KeyRelease>", self._on_search)
        self.listbox.bind("<<ListboxSelect>>", self._on_pick_from_list)
        self._debounce_id: Optional[str] = None

    def _fill_provinces(self) -> None:
        names = [p.name for p in self.index.provinces]
        self.cb_prov["values"] = names
        if names:
            self.cb_prov.current(0)
            self._on_prov()

    def _on_prov(self, *_):
        name = self.cb_prov.get()
        prov = next((p for p in self.index.provinces if p.name == name), None)
        cities = prov.children if prov else []
        self.cb_city["values"] = [c.name for c in cities]
        if cities:
            self.cb_city.current(0)
            self._on_city()

    def _on_city(self, *_):
        prov = next((p for p in self.index.provinces if p.name == self.cb_prov.get()), None)
        city = next((c for c in (prov.children if prov else []) if c.name == self.cb_city.get()), None)
        towns = city.children if city else []
        self.cb_town["values"] = [t.name for t in towns]
        if towns:
            self.cb_town.current(0)

    def _on_town(self, *_):
        pass

    def _on_search(self, *_):
        # debounce 150ms
        if self._debounce_id:
            try:
                self.after_cancel(self._debounce_id)
            except Exception:
                pass
        self._debounce_id = self.after(150, self._do_search)

    def _do_search(self):
        q = self.var_search.get().strip()
        self.listbox.delete(0, tk.END)
        if not q:
            return
        for _, code, name in self.index.search(q):
            self.listbox.insert(tk.END, name)

    def _on_pick_from_list(self, *_):
        if not self.listbox.curselection():
            return
        name = self.listbox.get(self.listbox.curselection()[0])
        # 해당 이름을 가진 city를 찾아 동기화
        for p in self.index.provinces:
            for c in p.children:
                if c.name == name:
                    self.cb_prov.set(p.name)
                    self._on_prov()
                    self.cb_city.set(c.name)
                    self._on_city()
                    return

    def get_selected(self) -> Dict[str, Tuple[str, str]]:
        p = next((x for x in self.index.provinces if x.name == self.cb_prov.get()), None)
        c = next((x for x in (p.children if p else []) if x.name == self.cb_city.get()), None)
        t = next((x for x in (c.children if c else []) if x.name == self.cb_town.get()), None)
        parts = [x.name for x in (p, c) if x]
        if t:
            parts.append(t.name)
        query = " ".join(parts)
        return {
            "province": (p.code if p else "", p.name if p else ""),
            "city": (c.code if c else "", c.name if c else ""),
            "town": (t.code if t else "", t.name if t else ""),
            "query": query,
        }


