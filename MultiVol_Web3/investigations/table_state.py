from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import json
from urllib.parse import urlparse,parse_qs,urlunparse
import reflex as rx
# ---- ADDED ----
import re
from datetime import datetime

class TableState(rx.State):
    """JSON-driven table with dynamic columns, search, per-column filters,
    show/hide, LIVE slider widths, sort, paginate.
    """

    # ---------- raw data ----------
    items: List[Dict[str, Any]] = []

    # ---------- ui state ----------
    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    # column visibility
    visible_columns: List[str] = []

    # per-column filters (AND)
    column_filters: Dict[str, str] = {}

    # column widths (CSS strings; '' => auto)
    col_widths: Dict[str, str] = {}

    # width slider controls (controlled)
    selected_width_column: str = ""
    width_slider_value: int = 200          # bound to slider.value
    col_width_default_px: int = 200
    slider_min_px: int = 80
    slider_max_px: int = 480
    slider_step_px: int = 10

    # filter inputs
    selected_filter_column: str = ""
    selected_filter_value: str = ""

    # settings panel
    show_settings: bool = False

    # pagination
    offset: int = 0
    limit: int = 12

    # ---------- data loading ----------
    def load_entries(self):
        current_url = self.router.url
        try:
            parsed_module = parse_qs(current_url.query)['module'][0]
            parsed_case = parse_qs(current_url.query)['case'][0]
            parsed_hostname = urlparse(current_url)
            if parsed_module == "Home":
                original_path = urlunparse((parsed_hostname.scheme, parsed_hostname.netloc, '', '', '', ''))
                return rx.redirect(f"{original_path}")
            else:
                current_path = Path(__file__).parent.parent
                cases_dir = current_path / "cases" / parsed_case / "volatility3_output"
                # Try both Windows and Linux outputs
                for system in ("windows", "linux"):
                    candidate = cases_dir / f"{system}.{parsed_module}_output.json"
                    if candidate.exists():
                        cases_path = candidate
                        break
                path = cases_path
                if path.exists():
                    try:
                        with path.open(encoding="utf-8") as f:
                            data = json.load(f)
                    except:
                        data = json.loads(f'[{{"error": "Error while treating file", "filename": "{cases_path}"}}]')
                    if isinstance(data, dict) and isinstance(data.get("data"), list):
                        data = data["data"]
                    if not isinstance(data, list):
                        data = []
                    self.items = [
                        {k: "" if v is None else str(v) for k, v in row.items()}
                        for row in data
                        if isinstance(row, dict)
                    ]
                else:
                    self.items = []

                self.visible_columns = list(self.headers) if self.headers else []
                self.offset = 0
        except Exception as e:
            # import os,sys
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            # print(exc_type, fname, exc_tb.tb_lineno)
            pass

    # ---------- derived vars ----------
    @rx.var(cache=True)
    def headers(self) -> List[str]:
        return list(self.items[0].keys()) if self.items else []

    @rx.var(cache=True)
    def effective_headers(self) -> List[str]:
        if not self.headers:
            return []
        vis = set(self.visible_columns or self.headers)
        return [h for h in self.headers if h in vis]

    @rx.var(cache=True)
    def visible_flags(self) -> List[bool]:
        vis = set(self.visible_columns or self.headers)
        return [h in vis for h in self.headers]

    @rx.var(cache=True)
    def filters_list(self) -> List[List[str]]:
        order = {h: i for i, h in enumerate(self.headers)}
        pairs = [[k, v] for k, v in self.column_filters.items() if v]
        return sorted(pairs, key=lambda kv: order.get(kv[0], 1_000_000))

    @rx.var(cache=True)
    def col_widths_list(self) -> List[str]:
        return [self.col_widths.get(h, "") for h in self.effective_headers]

    @rx.var(cache=True)
    def selected_width_px(self) -> int:
        """Current width (px) for the selected column (fallback to default)."""
        col = self.selected_width_column
        if not col:
            return self.col_width_default_px
        w = self.col_widths.get(col, "")
        try:
            if isinstance(w, str) and w.endswith("px"):
                return max(10, int(float(w[:-2])))
        except Exception:
            pass
        return self.col_width_default_px

    @rx.var(cache=True)
    def filtered_items(self) -> List[Dict[str, str]]:
        rows = self.items
        if self.search_value:
            q = self.search_value.lower()
            rows = [r for r in rows if any(q in str(v).lower() for v in r.values())]
        if self.column_filters:
            def ok(row: Dict[str, str]) -> bool:
                for col, sub in self.column_filters.items():
                    if not sub:
                        continue
                    if sub.lower() not in str(row.get(col, "")).lower():
                        return False
                return True
            rows = [r for r in rows if ok(r)]
        if self.sort_value:
            rows = sorted(rows, key=lambda r: r.get(self.sort_value, ""))
            if self.sort_reverse:
                rows.reverse()
        # Starts with
        if self.startswith_filters:
            def _ok_sw(row):
                for c, v in self.startswith_filters.items():
                    if v and not str(row.get(c, "")).lower().startswith(v.lower()):
                        return False
                return True
            rows = [r for r in rows if _ok_sw(r)]
        # Ends with
        if self.endswith_filters:
            def _ok_ew(row):
                for c, v in self.endswith_filters.items():
                    if v and not str(row.get(c, "")).lower().endswith(v.lower()):
                        return False
                return True
            rows = [r for r in rows if _ok_ew(r)]
        # Regex (case-insensitive)
        if self.regex_filters:
            compiled = {}
            for c, pattern in self.regex_filters.items():
                if pattern:
                    try:
                        compiled[c] = re.compile(pattern, re.IGNORECASE)
                    except Exception:
                        compiled[c] = None
                else:
                    compiled[c] = None
            def _ok_rx(row):
                for c, rxp in compiled.items():
                    if rxp is None:
                        return False
                    if not rxp.search(str(row.get(c, ""))):
                        return False
                return True
            rows = [r for r in rows if _ok_rx(r)]
        # Emptiness
        if self.emptiness_filters:
            def _ok_emp(row):
                for c, mode in self.emptiness_filters.items():
                    val = str(row.get(c, ""))
                    empty = (val.strip() == "")
                    if mode == "empty" and not empty:
                        return False
                    if mode == "nonempty" and empty:
                        return False
                return True
            rows = [r for r in rows if _ok_emp(r)]
        # Numeric comparisons
        if self.numeric_filters:
            def _try_float(s):
                try:
                    return float(str(s).strip())
                except Exception:
                    return None
            def _ok_num(row):
                for rec in self.numeric_filters:
                    col = rec.get("column", "")
                    op = rec.get("op", "==")
                    val = rec.get("value", "")
                    try:
                        target = float(val)
                    except Exception:
                        return False
                    x = _try_float(row.get(col, ""))
                    if x is None:
                        return False
                    if op == "==":
                        if not (x == target): return False
                    elif op == ">":
                        if not (x > target): return False
                    elif op == ">=":
                        if not (x >= target): return False
                    elif op == "<":
                        if not (x < target): return False
                    elif op == "<=":
                        if not (x <= target): return False
                    else:
                        return False
                return True
            rows = [r for r in rows if _ok_num(r)]
        # Date ranges
        if self.date_filters:
            def _to_dt(s: str):
                s = str(s).strip()
                if not s:
                    return None
                try:
                    # handle Z
                    if s.endswith("Z"):
                        s = s[:-1] + "+00:00"
                    return datetime.fromisoformat(s)
                except Exception:
                    return None
            def _ok_date(row):
                for rec in self.date_filters:
                    col = rec.get("column", "")
                    start = rec.get("start", "").strip()
                    end = rec.get("end", "").strip()
                    v = _to_dt(row.get(col, ""))
                    if v is None:
                        return False
                    if start:
                        sdt = _to_dt(start)
                        if sdt and v < sdt:
                            return False
                    if end:
                        edt = _to_dt(end)
                        if edt and v > edt:
                            return False
                return True
            rows = [r for r in rows if _ok_date(r)]
        return rows

    @rx.var(cache=True)
    def rows_matrix(self) -> List[List[str]]:
        cols = self.effective_headers
        return [[row.get(c, "") for c in cols] for row in self.filtered_items]

    @rx.var(cache=True)
    def page_number(self) -> int:
        total = len(self.rows_matrix)
        return (self.offset // self.limit) + 1 if total else 1

    @rx.var(cache=True)
    def total_pages(self) -> int:
        total = len(self.rows_matrix)
        return (total - 1) // self.limit + 1 if total else 1

    @rx.var(cache=True, initial_value=[])
    def current_page(self) -> List[List[str]]:
        s, e = self.offset, self.offset + self.limit
        return self.rows_matrix[s:e]

    # ---------- events: pagination ----------
    def first_page(self): self.offset = 0
    def prev_page(self):
        if self.page_number > 1: self.offset -= self.limit
    def next_page(self):
        if self.page_number < self.total_pages: self.offset += self.limit
    def last_page(self): self.offset = (self.total_pages - 1) * self.limit

    # ---------- events: sort ----------
    def sort_by(self, column: str):
        if self.sort_value == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_value = column
            self.sort_reverse = False

    # ---------- events: visibility ----------
    def toggle_column(self, column: str):
        if column in self.visible_columns:
            self.visible_columns = [c for c in self.visible_columns if c != column]
        else:
            self.visible_columns = [*self.visible_columns, column]

    def show_all_columns(self): self.visible_columns = list(self.headers)
    def hide_all_columns(self): self.visible_columns = []

    # ---------- events: filters ----------
    def set_selected_filter_column(self, col: str): self.selected_filter_column = col
    def set_selected_filter_value(self, s: str): self.selected_filter_value = s

    def add_or_update_filter(self):
        if not self.selected_filter_column:
            return
        d = dict(self.column_filters)
        d[self.selected_filter_column] = self.selected_filter_value
        self.column_filters = {k: v for k, v in d.items() if v}
        self.selected_filter_value = ""

    def remove_filter(self, col: str):
        d = dict(self.column_filters); d.pop(col, None); self.column_filters = d

    def clear_filters(self):
        self.column_filters = {}
        self.selected_filter_column = ""
        self.selected_filter_value = ""

    def set_selected_width_column(self, col: str):
        """Pick a column; sync the slider to that column's current width."""
        self.selected_width_column = col or ""
        self.width_slider_value = self.selected_width_px

    def set_width_slider_value(self, value: List[int | float]):
        """Reflex slider on_change sends a list like [180]. Make it live."""
        if not value:
            return
        try:
            px = int(float(value[0]))
        except Exception:
            return
        px = max(self.slider_min_px, min(self.slider_max_px, px))
        self.width_slider_value = px
        if self.selected_width_column:
            self.col_widths = {
                **self.col_widths,
                self.selected_width_column: f"{px}px",
            }

    def clear_width(self, col: str):
        d = dict(self.col_widths); d.pop(col, None); self.col_widths = d

    def clear_all_widths(self): self.col_widths = {}

    def toggle_settings(self): self.show_settings = not self.show_settings

    # Starts with
    startswith_filters: Dict[str, str] = {}
    selected_sw_column: str = ""
    selected_sw_value: str = ""

    @rx.var(cache=True)
    def startswith_list(self) -> List[List[str]]:
        order = {h: i for i, h in enumerate(self.headers)}
        pairs = [[k, v] for k, v in self.startswith_filters.items() if v]
        return sorted(pairs, key=lambda kv: order.get(kv[0], 1_000_000))

    def set_selected_sw_column(self, col: str): self.selected_sw_column = col
    def set_selected_sw_value(self, v: str): self.selected_sw_value = v

    def add_or_update_startswith(self):
        if not self.selected_sw_column:
            return
        d = dict(self.startswith_filters)
        d[self.selected_sw_column] = self.selected_sw_value
        self.startswith_filters = {k: v for k, v in d.items() if v}

    def remove_startswith(self, col: str):
        d = dict(self.startswith_filters); d.pop(col, None); self.startswith_filters = d

    def clear_startswith(self):
        self.startswith_filters = {}
        self.selected_sw_column = ""
        self.selected_sw_value = ""

    # Ends with
    endswith_filters: Dict[str, str] = {}
    selected_ew_column: str = ""
    selected_ew_value: str = ""

    @rx.var(cache=True)
    def endswith_list(self) -> List[List[str]]:
        order = {h: i for i, h in enumerate(self.headers)}
        pairs = [[k, v] for k, v in self.endswith_filters.items() if v]
        return sorted(pairs, key=lambda kv: order.get(kv[0], 1_000_000))

    def set_selected_ew_column(self, col: str): self.selected_ew_column = col
    def set_selected_ew_value(self, v: str): self.selected_ew_value = v

    def add_or_update_endswith(self):
        if not self.selected_ew_column:
            return
        d = dict(self.endswith_filters)
        d[self.selected_ew_column] = self.selected_ew_value
        self.endswith_filters = {k: v for k, v in d.items() if v}

    def remove_endswith(self, col: str):
        d = dict(self.endswith_filters); d.pop(col, None); self.endswith_filters = d

    def clear_endswith(self):
        self.endswith_filters = {}
        self.selected_ew_column = ""
        self.selected_ew_value = ""

    # Regex (case-insensitive)
    regex_filters: Dict[str, str] = {}
    selected_rx_column: str = ""
    selected_rx_pattern: str = ""

    @rx.var(cache=True)
    def regex_list(self) -> List[List[str]]:
        order = {h: i for i, h in enumerate(self.headers)}
        pairs = [[k, v] for k, v in self.regex_filters.items() if v]
        return sorted(pairs, key=lambda kv: order.get(kv[0], 1_000_000))

    def set_selected_rx_column(self, col: str): self.selected_rx_column = col
    def set_selected_rx_pattern(self, p: str): self.selected_rx_pattern = p

    def add_or_update_regex(self):
        if not self.selected_rx_column:
            return
        d = dict(self.regex_filters)
        d[self.selected_rx_column] = self.selected_rx_pattern
        self.regex_filters = {k: v for k, v in d.items() if v}

    def remove_regex(self, col: str):
        d = dict(self.regex_filters); d.pop(col, None); self.regex_filters = d

    def clear_regex(self):
        self.regex_filters = {}
        self.selected_rx_column = ""
        self.selected_rx_pattern = ""

    # Emptiness
    emptiness_filters: Dict[str, str] = {}  # "empty" | "nonempty"
    selected_empty_column: str = ""
    selected_empty_choice: str = ""

    @rx.var(cache=True)
    def emptiness_list(self) -> List[List[str]]:
        order = {h: i for i, h in enumerate(self.headers)}
        pairs = [[k, v] for k, v in self.emptiness_filters.items() if v]
        return sorted(pairs, key=lambda kv: order.get(kv[0], 1_000_000))

    def set_selected_empty_column(self, col: str): self.selected_empty_column = col
    def set_selected_empty_choice(self, choice: str): self.selected_empty_choice = choice

    def add_or_update_emptiness(self):
        if not self.selected_empty_column or not self.selected_empty_choice:
            return
        d = dict(self.emptiness_filters)
        d[self.selected_empty_column] = self.selected_empty_choice
        self.emptiness_filters = d

    def remove_emptiness(self, col: str):
        d = dict(self.emptiness_filters); d.pop(col, None); self.emptiness_filters = d

    def clear_emptiness(self):
        self.emptiness_filters = {}
        self.selected_empty_column = ""
        self.selected_empty_choice = ""

    # Numeric comparisons
    numeric_filters: List[Dict[str, str]] = []   # {"column":..., "op":..., "value":...}
    selected_num_column: str = ""
    selected_num_op: str = ""
    selected_num_value: str = ""

    @rx.var(cache=True)
    def numeric_filters_list(self) -> List[Dict[str, str]]:
        return list(self.numeric_filters)

    def set_selected_num_column(self, col: str): self.selected_num_column = col
    def set_selected_num_op(self, op: str): self.selected_num_op = op
    def set_selected_num_value(self, v: str): self.selected_num_value = v

    def add_or_update_numeric(self):
        if not self.selected_num_column or not self.selected_num_op or self.selected_num_value.strip() == "":
            return
        # replace existing for the same column if any; else append
        updated = False
        new_rec = {"column": self.selected_num_column, "op": self.selected_num_op, "value": self.selected_num_value}
        nf = list(self.numeric_filters)
        for i, rec in enumerate(nf):
            if rec.get("column") == self.selected_num_column:
                nf[i] = new_rec
                updated = True
                break
        if not updated:
            nf.append(new_rec)
        self.numeric_filters = nf

    def remove_numeric(self, index: int):
        nf = list(self.numeric_filters)
        if 0 <= index < len(nf):
            nf.pop(index)
        self.numeric_filters = nf

    def clear_numeric(self):
        self.numeric_filters = []
        self.selected_num_column = ""
        self.selected_num_op = ""
        self.selected_num_value = ""

    # Date ranges
    date_filters: List[Dict[str, str]] = []   # {"column":..., "start":..., "end":...}
    selected_date_column: str = ""
    selected_date_start: str = ""
    selected_date_end: str = ""

    @rx.var(cache=True)
    def date_filters_list(self) -> List[Dict[str, str]]:
        return list(self.date_filters)

    def set_selected_date_column(self, col: str): self.selected_date_column = col
    def set_selected_date_start(self, v: str): self.selected_date_start = v
    def set_selected_date_end(self, v: str): self.selected_date_end = v

    def add_or_update_date(self):
        if not self.selected_date_column:
            return
        rec = {"column": self.selected_date_column, "start": self.selected_date_start, "end": self.selected_date_end}
        df = list(self.date_filters)
        # replace existing column
        replaced = False
        for i, r in enumerate(df):
            if r.get("column") == self.selected_date_column:
                df[i] = rec
                replaced = True
                break
        if not replaced:
            df.append(rec)
        self.date_filters = df

    def remove_date(self, index: int):
        df = list(self.date_filters)
        if 0 <= index < len(df):
            df.pop(index)
        self.date_filters = df

    def clear_date(self):
        self.date_filters = []
        self.selected_date_column = ""
        self.selected_date_start = ""
        self.selected_date_end = ""

    show_advanced_filters: bool = False
    sw_expanded: bool = False
    ew_expanded: bool = False
    rx_expanded: bool = False
    emp_expanded: bool = False
    num_expanded: bool = False
    date_expanded: bool = False

    def toggle_advanced_filters(self): self.show_advanced_filters = not self.show_advanced_filters
    def toggle_sw_section(self): self.sw_expanded = not self.sw_expanded
    def toggle_ew_section(self): self.ew_expanded = not self.ew_expanded
    def toggle_rx_section(self): self.rx_expanded = not self.rx_expanded
    def toggle_emp_section(self): self.emp_expanded = not self.emp_expanded
    def toggle_num_section(self): self.num_expanded = not self.num_expanded
    def toggle_date_section(self): self.date_expanded = not self.date_expanded
