# investigation.py
import reflex as rx
from .table_state import TableState
import glob
from pathlib import Path
import re
import reflex as rx
from urllib.parse import urlparse,parse_qs,urlunparse
class InvestigationState(rx.State):
    all_modules: list[dict[str, str]] = []   # [{value: path, label: cleaned}]
    active_tab: str = ""                      # matches tabs `value`
    def return_cases_path(self):
        try:
            current_url = self.router.url
            parsed_case = parse_qs(current_url.query)['case'][0]
            current_path = Path(__file__).parent.parent
            cases_path = current_path / "cases" / parsed_case / "volatility3_output"
        except: 
            return 0
        return cases_path
    
    def on_tab_change(self, value: str):
        TableState.load_entries()
        # keep local state (so Tabs is controlled)
        self.active_tab = value
        # navigate to same route with ?module=<value>
        # (uses Reflex router-aware redirect)
        current_url = self.router.url
        try:
            parsed_case = parse_qs(current_url.query)['case'][0]
            return rx.redirect(f"{current_url.path}?case={parsed_case}&module={value}")
        except:
            return rx.redirect(f"{current_url.path}?module={value}")

    def load_modules(self):
        files = glob.glob(str(self.return_cases_path() / "*.json"))   # <- robust glob
        cleaned = []
        cleaned.append({"value": "Home", "label": "Home"})
        for f in files:
            m = re.search(r"\.(.+?)_output\.json$", f)
            label = m.group(1) if m else Path(f).stem
            cleaned.append({"value": f, "label": label})
        self.all_modules = cleaned


    @staticmethod
    def tab_trigger(rec, i):
        # label is what you show, and also the tab "value"
        return rx.tabs.trigger(rec["label"], value=rec["label"])

    @staticmethod
    def tab_content(rec, i):
        return rx.tabs.content(rx.text(rec["value"]), value=rec["label"])


    def scroll_tabs_left(self):
        js = """
        const el = document.getElementById('modules-tabbar');
        if (el) el.scrollBy({ left: -240, behavior: 'smooth' });
        """
        return rx.call_script(js)

    def scroll_tabs_right(self):
        js = """
        const el = document.getElementById('modules-tabbar');
        if (el) el.scrollBy({ left: 240, behavior: 'smooth' });
        """
        return rx.call_script(js)


def _settings_panel() -> rx.Component:
    """Show/hide columns, add substring filters, and LIVE column widths via a controlled slider."""
    return rx.cond(
        TableState.show_settings,
        rx.box(
            rx.vstack(
                # header
                rx.hstack(
                    rx.heading("Table Settings", size="4"),
                    rx.spacer(),
                    rx.button("Close", on_click=TableState.toggle_settings, variant="surface"),
                    align="center",
                ),

                # --- Column visibility ---
                rx.vstack(
                    rx.text("Visible columns", weight="medium"),
                    rx.hstack(
                        rx.button("Show all", size="2", variant="soft", on_click=TableState.show_all_columns),
                        rx.button("Hide all", size="2", variant="soft", on_click=TableState.hide_all_columns),
                        spacing="2",
                    ),
                    rx.flex(
                        rx.foreach(
                            TableState.headers,
                            lambda header, idx: rx.hstack(
                                rx.switch(
                                    checked=TableState.visible_flags[idx],
                                    on_change=TableState.toggle_column(header),
                                ),
                                rx.text(header),
                                align="center",
                                spacing="2",
                                padding_y="4px",
                                padding_x="8px",
                                border_radius="md",
                                bg=rx.cond(
                                    TableState.visible_flags[idx],
                                    rx.color("accent", 2),
                                    rx.color("gray", 2),
                                ),
                            ),
                        ),
                        wrap="wrap",
                        gap="8px",
                    ),
                    spacing="2",
                ),

                rx.separator(orientation="horizontal"),

                # --- Filters ---
                rx.vstack(
                    rx.text("Filters (contains)", weight="medium"),
                    rx.hstack(
                        rx.select.root(
                            rx.select.trigger(placeholder="Pick a column"),
                            rx.select.content(
                                rx.foreach(
                                    TableState.headers,
                                    lambda h, _i: rx.select.item(h, value=h),
                                ),
                            ),
                            value=TableState.selected_filter_column,
                            on_change=TableState.set_selected_filter_column,
                            size="2",
                        ),
                        rx.input(
                            placeholder="substring…",
                            value=TableState.selected_filter_value,
                            on_change=TableState.set_selected_filter_value,
                            size="2",
                            variant="surface",
                            max_width="280px",
                        ),
                        rx.button("Add / Update", on_click=TableState.add_or_update_filter, size="2"),
                        rx.button("Clear all", on_click=TableState.clear_filters, size="2", variant="soft"),
                        spacing="2",
                        wrap="wrap",
                    ),
                    rx.flex(
                        rx.foreach(
                            TableState.filters_list,
                            lambda pair, _i: rx.badge(
                                rx.hstack(
                                    rx.text(pair[0], ": ", pair[1]),
                                    rx.icon_button(
                                        rx.icon("x"),
                                        size="1",
                                        variant="soft",
                                        on_click=TableState.remove_filter(pair[0]),
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                variant="soft",
                            ),
                        ),
                        wrap="wrap",
                        gap="8px",
                    ),
                    spacing="2",
                ),

                rx.separator(orientation="horizontal"),

                # --- Column widths (LIVE slider) ---
                rx.vstack(
                    rx.text("Column widths", weight="medium"),
                    rx.hstack(
                        rx.select.root(
                            rx.select.trigger(placeholder="Pick a column"),
                            rx.select.content(
                                rx.foreach(
                                    TableState.effective_headers,
                                    lambda h, _i: rx.select.item(h, value=h),
                                ),
                            ),
                            value=TableState.selected_width_column,
                            on_change=TableState.set_selected_width_column,
                            size="2",
                        ),
                        rx.spacer(),
                        rx.badge(
                            rx.hstack(
                                rx.text("Width"),
                                rx.code(TableState.width_slider_value),
                                rx.text("px"),
                                spacing="2",
                                align="center",
                            ),
                            variant="soft",
                        ),
                        rx.cond(
                            TableState.selected_width_column != "",
                            rx.icon_button(
                                rx.icon("rotate-ccw"),
                                title="Reset selected to auto",
                                size="2",
                                variant="soft",
                                on_click=TableState.clear_width(TableState.selected_width_column),
                            ),
                            rx.box(),
                        ),
                        spacing="3",
                        align="center",
                        wrap="wrap",
                    ),
                    rx.cond(
                        TableState.selected_width_column != "",
                        rx.box(
                            rx.slider(
                                # Controlled slider; value is a list per Reflex API.
                                value=[TableState.width_slider_value],
                                min=TableState.slider_min_px,
                                max=TableState.slider_max_px,
                                step=TableState.slider_step_px,
                                on_change=TableState.set_width_slider_value,  # live apply happens in handler
                                width="100%",
                            ),
                            padding_top="8px",
                            width="100%",
                        ),
                        rx.box(),
                    ),
                    spacing="2",
                ),

                # ===================== Advanced filters (manual collapsible) =====================
                rx.separator(orientation="horizontal"),

                # Master toggle
                rx.hstack(
                    rx.cond(
                        TableState.show_advanced_filters,
                        rx.icon("chevron-down"),
                        rx.icon("chevron-right"),
                    ),
                    rx.text("Advanced filters", weight="bold"),
                    on_click=TableState.toggle_advanced_filters,
                    cursor="pointer",
                    align="center",
                    spacing="2",
                ),

                rx.cond(
                    TableState.show_advanced_filters,
                    rx.vstack(
                        # ---- Starts with ----
                        rx.box(
                            rx.hstack(
                                rx.cond(
                                    TableState.sw_expanded,
                                    rx.icon("chevron-down"),
                                    rx.icon("chevron-right"),
                                ),
                                rx.text("Starts with", weight="medium"),
                                on_click=TableState.toggle_sw_section,
                                cursor="pointer",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                TableState.sw_expanded,
                                rx.vstack(
                                    rx.hstack(
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Pick a column"),
                                            rx.select.content(
                                                rx.foreach(TableState.headers, lambda h, _i: rx.select.item(h, value=h))
                                            ),
                                            value=TableState.selected_sw_column,
                                            on_change=TableState.set_selected_sw_column,
                                            size="2",
                                        ),
                                        rx.input(
                                            placeholder="prefix…",
                                            value=TableState.selected_sw_value,
                                            on_change=TableState.set_selected_sw_value,
                                            size="2",
                                            variant="surface",
                                            max_width="240px",
                                        ),
                                        rx.button("Add / Update", on_click=TableState.add_or_update_startswith, size="2"),
                                        rx.button("Clear all", on_click=TableState.clear_startswith, size="2", variant="soft"),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    rx.flex(
                                        rx.foreach(
                                            TableState.startswith_list,
                                            lambda pair, _i: rx.badge(
                                                rx.hstack(
                                                    rx.text(pair[0], " starts with: ", pair[1]),
                                                    rx.icon_button(
                                                        rx.icon("x"),
                                                        size="1",
                                                        variant="soft",
                                                        on_click=TableState.remove_startswith(pair[0]),
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                                variant="soft",
                                            ),
                                        ),
                                        wrap="wrap",
                                        gap="8px",
                                    ),
                                    spacing="2",
                                ),
                                rx.box(),
                            ),
                            padding_y="4px",
                        ),

                        rx.separator(orientation="horizontal"),

                        # ---- Ends with ----
                        rx.box(
                            rx.hstack(
                                rx.cond(
                                    TableState.ew_expanded,
                                    rx.icon("chevron-down"),
                                    rx.icon("chevron-right"),
                                ),
                                rx.text("Ends with", weight="medium"),
                                on_click=TableState.toggle_ew_section,
                                cursor="pointer",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                TableState.ew_expanded,
                                rx.vstack(
                                    rx.hstack(
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Pick a column"),
                                            rx.select.content(
                                                rx.foreach(TableState.headers, lambda h, _i: rx.select.item(h, value=h))
                                            ),
                                            value=TableState.selected_ew_column,
                                            on_change=TableState.set_selected_ew_column,
                                            size="2",
                                        ),
                                        rx.input(
                                            placeholder="suffix…",
                                            value=TableState.selected_ew_value,
                                            on_change=TableState.set_selected_ew_value,
                                            size="2",
                                            variant="surface",
                                            max_width="240px",
                                        ),
                                        rx.button("Add / Update", on_click=TableState.add_or_update_endswith, size="2"),
                                        rx.button("Clear all", on_click=TableState.clear_endswith, size="2", variant="soft"),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    rx.flex(
                                        rx.foreach(
                                            TableState.endswith_list,
                                            lambda pair, _i: rx.badge(
                                                rx.hstack(
                                                    rx.text(pair[0], " ends with: ", pair[1]),
                                                    rx.icon_button(
                                                        rx.icon("x"),
                                                        size="1",
                                                        variant="soft",
                                                        on_click=TableState.remove_endswith(pair[0]),
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                                variant="soft",
                                            ),
                                        ),
                                        wrap="wrap",
                                        gap="8px",
                                    ),
                                    spacing="2",
                                ),
                                rx.box(),
                            ),
                            padding_y="4px",
                        ),

                        rx.separator(orientation="horizontal"),

                        # ---- Regex ----
                        rx.box(
                            rx.hstack(
                                rx.cond(
                                    TableState.rx_expanded,
                                    rx.icon("chevron-down"),
                                    rx.icon("chevron-right"),
                                ),
                                rx.text("Regex (case-insensitive)", weight="medium"),
                                on_click=TableState.toggle_rx_section,
                                cursor="pointer",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                TableState.rx_expanded,
                                rx.vstack(
                                    rx.hstack(
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Pick a column"),
                                            rx.select.content(
                                                rx.foreach(TableState.headers, lambda h, _i: rx.select.item(h, value=h))
                                            ),
                                            value=TableState.selected_rx_column,
                                            on_change=TableState.set_selected_rx_column,
                                            size="2",
                                        ),
                                        rx.input(
                                            placeholder=r"e.g. ^ERR\d{3}$",
                                            value=TableState.selected_rx_pattern,
                                            on_change=TableState.set_selected_rx_pattern,
                                            size="2",
                                            variant="surface",
                                            max_width="280px",
                                        ),
                                        rx.button("Add / Update", on_click=TableState.add_or_update_regex, size="2"),
                                        rx.button("Clear all", on_click=TableState.clear_regex, size="2", variant="soft"),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    rx.flex(
                                        rx.foreach(
                                            TableState.regex_list,
                                            lambda pair, _i: rx.badge(
                                                rx.hstack(
                                                    rx.text(pair[0], " /", pair[1], "/i"),
                                                    rx.icon_button(
                                                        rx.icon("x"),
                                                        size="1",
                                                        variant="soft",
                                                        on_click=TableState.remove_regex(pair[0]),
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                                variant="soft",
                                            ),
                                        ),
                                        wrap="wrap",
                                        gap="8px",
                                    ),
                                    spacing="2",
                                ),
                                rx.box(),
                            ),
                            padding_y="4px",
                        ),

                        rx.separator(orientation="horizontal"),

                        # ---- Emptiness ----
                        rx.box(
                            rx.hstack(
                                rx.cond(
                                    TableState.emp_expanded,
                                    rx.icon("chevron-down"),
                                    rx.icon("chevron-right"),
                                ),
                                rx.text("Emptiness", weight="medium"),
                                on_click=TableState.toggle_emp_section,
                                cursor="pointer",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                TableState.emp_expanded,
                                rx.vstack(
                                    rx.hstack(
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Pick a column"),
                                            rx.select.content(
                                                rx.foreach(TableState.headers, lambda h, _i: rx.select.item(h, value=h))
                                            ),
                                            value=TableState.selected_empty_column,
                                            on_change=TableState.set_selected_empty_column,
                                            size="2",
                                        ),
                                        rx.select.root(
                                            rx.select.trigger(placeholder="is empty / is not empty"),
                                            rx.select.content(
                                                rx.select.item("is empty", value="empty"),
                                                rx.select.item("is not empty", value="nonempty"),
                                            ),
                                            value=TableState.selected_empty_choice,
                                            on_change=TableState.set_selected_empty_choice,
                                            size="2",
                                        ),
                                        rx.button("Add / Update", on_click=TableState.add_or_update_emptiness, size="2"),
                                        rx.button("Clear all", on_click=TableState.clear_emptiness, size="2", variant="soft"),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    rx.flex(
                                        rx.foreach(
                                            TableState.emptiness_list,
                                            lambda pair, _i: rx.badge(
                                                rx.hstack(
                                                    rx.text(pair[0], ": ", pair[1]),
                                                    rx.icon_button(
                                                        rx.icon("x"),
                                                        size="1",
                                                        variant="soft",
                                                        on_click=TableState.remove_emptiness(pair[0]),
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                                variant="soft",
                                            ),
                                        ),
                                        wrap="wrap",
                                        gap="8px",
                                    ),
                                    spacing="2",
                                ),
                                rx.box(),
                            ),
                            padding_y="4px",
                        ),

                        rx.separator(orientation="horizontal"),

                        # ---- Numeric comparisons ----
                        rx.box(
                            rx.hstack(
                                rx.cond(
                                    TableState.num_expanded,
                                    rx.icon("chevron-down"),
                                    rx.icon("chevron-right"),
                                ),
                                rx.text("Numeric comparisons", weight="medium"),
                                on_click=TableState.toggle_num_section,
                                cursor="pointer",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                TableState.num_expanded,
                                rx.vstack(
                                    rx.hstack(
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Pick a column"),
                                            rx.select.content(
                                                rx.foreach(TableState.headers, lambda h, _i: rx.select.item(h, value=h))
                                            ),
                                            value=TableState.selected_num_column,
                                            on_change=TableState.set_selected_num_column,
                                            size="2",
                                        ),
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Op"),
                                            rx.select.content(
                                                rx.select.item("=", value="=="),
                                                rx.select.item(">", value=">"),
                                                rx.select.item(">=", value=">="),
                                                rx.select.item("<", value="<"),
                                                rx.select.item("<=", value="<="),
                                            ),
                                            value=TableState.selected_num_op,
                                            on_change=TableState.set_selected_num_op,
                                            size="2",
                                        ),
                                        rx.input(
                                            placeholder="number…",
                                            value=TableState.selected_num_value,
                                            on_change=TableState.set_selected_num_value,
                                            size="2",
                                            variant="surface",
                                            max_width="160px",
                                        ),
                                        rx.button("Add / Update", on_click=TableState.add_or_update_numeric, size="2"),
                                        rx.button("Clear all", on_click=TableState.clear_numeric, size="2", variant="soft"),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    rx.flex(
                                        rx.foreach(
                                            TableState.numeric_filters_list,
                                            lambda rec, i: rx.badge(
                                                rx.hstack(
                                                    rx.text(rec["column"], " ", rec["op"], " ", rec["value"]),
                                                    rx.icon_button(
                                                        rx.icon("x"),
                                                        size="1",
                                                        variant="soft",
                                                        on_click=TableState.remove_numeric(i),
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                                variant="soft",
                                            ),
                                        ),
                                        wrap="wrap",
                                        gap="8px",
                                    ),
                                    spacing="2",
                                ),
                                rx.box(),
                            ),
                            padding_y="4px",
                        ),

                        rx.separator(orientation="horizontal"),

                        # ---- Date range ----
                        rx.box(
                            rx.hstack(
                                rx.cond(
                                    TableState.date_expanded,
                                    rx.icon("chevron-down"),
                                    rx.icon("chevron-right"),
                                ),
                                rx.text("Date range", weight="medium"),
                                on_click=TableState.toggle_date_section,
                                cursor="pointer",
                                align="center",
                                spacing="2",
                            ),
                            rx.cond(
                                TableState.date_expanded,
                                rx.vstack(
                                    rx.hstack(
                                        rx.select.root(
                                            rx.select.trigger(placeholder="Pick a column"),
                                            rx.select.content(
                                                rx.foreach(TableState.headers, lambda h, _i: rx.select.item(h, value=h))
                                            ),
                                            value=TableState.selected_date_column,
                                            on_change=TableState.set_selected_date_column,
                                            size="2",
                                        ),
                                        rx.input(
                                            placeholder="start…",
                                            value=TableState.selected_date_start,
                                            on_change=TableState.set_selected_date_start,
                                            size="2",
                                            variant="surface",
                                            max_width="200px",
                                        ),
                                        rx.input(
                                            placeholder="end…",
                                            value=TableState.selected_date_end,
                                            on_change=TableState.set_selected_date_end,
                                            size="2",
                                            variant="surface",
                                            max_width="200px",
                                        ),
                                        rx.button("Add / Update", on_click=TableState.add_or_update_date, size="2"),
                                        rx.button("Clear all", on_click=TableState.clear_date, size="2", variant="soft"),
                                        spacing="2",
                                        wrap="wrap",
                                    ),
                                    rx.flex(
                                        rx.foreach(
                                            TableState.date_filters_list,
                                            lambda rec, i: rx.badge(
                                                rx.hstack(
                                                    rx.text(rec["column"], " ∈ [", rec["start"], " … ", rec["end"], "]"),
                                                    rx.icon_button(
                                                        rx.icon("x"),
                                                        size="1",
                                                        variant="soft",
                                                        on_click=TableState.remove_date(i),
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                                variant="soft",
                                            ),
                                        ),
                                        wrap="wrap",
                                        gap="8px",
                                    ),
                                    spacing="2",
                                ),
                                rx.box(),
                            ),
                            padding_y="4px",
                        ),
                    ),
                    rx.box(),
                ),
                # =================== END Advanced (collapsible) ===================

                spacing="4",
            ),
            padding="1rem",
            border=f"1px solid {rx.color('gray', 5)}",
            border_radius="12px",
            bg=rx.color("gray", 1),
        ),
        rx.box(),  # hidden
    )


def table() -> rx.Component:
    return rx.box(
        rx.tabs.root(
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevron-left"),
                    variant="soft",
                    on_click=InvestigationState.scroll_tabs_left,
                ),
                rx.tabs.list(
                    rx.foreach(InvestigationState.all_modules, InvestigationState.tab_trigger),
                    id="modules-tabbar",
                    width="100%",
                    style={
                        "overflowX": "auto",   # ← scrollable
                        "display": "flex",
                        "flexWrap": "nowrap",  # ← keep on one line
                        "gap": "6px",
                        "scrollBehavior": "smooth",
                    },
                ),
                rx.icon_button(
                    rx.icon("chevron-right"),
                    variant="soft",
                    on_click=InvestigationState.scroll_tabs_right,
                ),
                align="center",
                gap="2",
                width="100%",
            ),
            value=InvestigationState.active_tab,
            on_change=InvestigationState.on_tab_change,
        ),
        # top controls
        rx.flex(
            rx.hstack(
                rx.button(
                    rx.icon("sliders-horizontal"),
                    "Columns & Filters",
                    on_click=TableState.toggle_settings,
                    size="3",
                    variant="surface",
                ),
                spacing="3",
                wrap="wrap",
            ),
            justify="between",
            width="100%",
            padding_bottom="1em",
            padding_top="1em"
        ),

        _settings_panel(),

        # table
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.foreach(
                        TableState.effective_headers,
                        lambda header, idx: rx.table.column_header_cell(
                            rx.hstack(rx.text(header.replace("_", " ").title())),
                            cursor="pointer",
                            on_click=TableState.sort_by(header),
                            style={"width": TableState.col_widths_list[idx]},  # '' => auto
                        ),
                    ),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    TableState.current_page,
                    lambda row, rindex: rx.table.row(
                        rx.foreach(
                            row,
                            lambda cell, cindex: rx.table.cell(
                                cell,
                                style={"width": TableState.col_widths_list[cindex]},
                            ),
                        ),
                        style={
                            "_hover": {
                                "bg": rx.cond(
                                    rindex % 2 == 0, rx.color("gray", 3), rx.color("accent", 3)
                                )
                            },
                            "bg": rx.cond(
                                    rindex % 2 == 0, rx.color("gray", 1), rx.color("accent", 2)
                            ),
                        },
                        align="center",
                    ),
                ),
            ),
            variant="surface",
            size="3",
            width="100%",
        ),

        # pagination
        rx.hstack(
            rx.text("Page ", rx.code(TableState.page_number), " of ", rx.code(TableState.total_pages)),
            rx.hstack(
                rx.icon_button(
                    rx.icon("chevrons-left", size=18),
                    on_click=TableState.first_page,
                    opacity=rx.cond(TableState.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(TableState.page_number == 1, "gray", "accent"),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-left", size=18),
                    on_click=TableState.prev_page,
                    opacity=rx.cond(TableState.page_number == 1, 0.6, 1),
                    color_scheme=rx.cond(TableState.page_number == 1, "gray", "accent"),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevron-right", size=18),
                    on_click=TableState.next_page,
                    opacity=rx.cond(TableState.page_number == TableState.total_pages, 0.6, 1),
                    color_scheme=rx.cond(TableState.page_number == TableState.total_pages, "gray", "accent"),
                    variant="soft",
                ),
                rx.icon_button(
                    rx.icon("chevrons-right", size=18),
                    on_click=TableState.last_page,
                    opacity=rx.cond(TableState.page_number == TableState.total_pages, 0.6, 1),
                    color_scheme=rx.cond(TableState.page_number == TableState.total_pages, "gray", "accent"),
                    variant="soft",
                ),
                align="center",
                spacing="2",
                justify="end",
            ),
            spacing="5",
            margin_top="1em",
            align="center",
            width="100%",
            justify="between",
        ),
        width="100%",
        on_mount=InvestigationState.load_modules,
    )
