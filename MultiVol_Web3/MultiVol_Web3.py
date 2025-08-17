# main file
from __future__ import annotations
import logging
from typing import Iterable, Optional
import reflex as rx
import random
from pathlib import Path
from .cases_management.cases import cases
from .investigations.investigation import table
from .profiles import index_profiles
from .investigations.investigation import TableState
from .cases_management.handle_case import after_upload
from .templates.navbar import sidebar
from .templates.spline_func import _spline_background
BG = "#0b0d0f"
PANEL = "#121417"
EDGE = "#272b31"
TEXT = "#d3d6db"
MUTED = "#8b9097"
ACCENT = "#a200ff"

def _make_logger(name: str, logfile: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(message)s")
        fh = logging.FileHandler(logfile, encoding="utf-8")
        sh = logging.StreamHandler()
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger

APP_LOG = _make_logger("app-log", "app.log")

def write_log(msg: str):
    APP_LOG.info(msg)

class LoggerList(list[str]):
    def __init__(
        self,
        logfile: str,
        initial: Optional[Iterable[str]] = None,
        name: Optional[str] = None,
    ):
        super().__init__(initial or [])
        self.logfile = logfile
        self.logger = _make_logger(name or f"LoggerList-{id(self)}", logfile)
        for msg in self:
            self.logger.info(msg)

    def append(self, item: str) -> None:
        super().append(item)
        self.logger.info(item)

    def extend(self, items: Iterable[str]) -> None:
        for it in items:
            self.append(it)

    def __iadd__(self, items: Iterable[str]):
        self.extend(items)
        return self

    def __call__(self) -> str:
        for h in self.logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
        try:
            with open(self.logfile, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def read(self) -> str:
        return self()

    def close(self) -> None:
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)
            try:
                h.flush()
            finally:
                try:
                    h.close()
                except Exception:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class State(rx.State):
    msg: str = ""
    log: list[str] = []
    log = LoggerList("app.log", initial=log)
    uploaded: list[str] = []
    uploading: bool = False
    progress: int = 0
    show_progress: bool = False
    os_values: list[str] = ["windows", "linux"]
    os_value: str = "windows"
    mode_values: list[str] = ["light", "full"]
    mode_value: str = "light"
    case_name: str = ""
    case_description: str = ""
    log_tick: int = 0

    def change_value(self):
        self.value = random.choice(self.os_values)

    def set_os_value(self, v: str):
        self.os_value = v

    async def handle_upload(self, files: list[rx.UploadFile]):
        self.log_append(f"[CASE-CREATION] The case '{self.case_name or '(empty)'}' with os '{self.os_value}' was just created.")
        yield

        saved_batch: list[str] = []
        for file in files:
            data = await file.read()
            path = rx.get_upload_dir() / file.name
            with path.open("wb") as f:
                f.write(data)
            self.uploaded.append(file.name)
            saved_batch.append(file.name)

        try:
            upload_dir = rx.get_upload_dir()
            paths = [str(upload_dir / name) for name in saved_batch]

            async for _ in after_upload(
                self,
                paths,
                self.case_name,
                self.os_value,
                self.mode_value
            ):
                yield

            self.log_append(f"[post] processed {len(saved_batch)} file(s)")
            yield
        except Exception as e:
            self.log_append(f"[post] error: {e}")
            yield


    def handle_upload_progress(self, progress: dict):
        self.uploading = True
        self.show_progress = True
        try:
            self.progress = round(progress["progress"] * 100)
        except Exception:
            self.progress = 0
        if self.progress >= 100:
            self.uploading = False

    def clear_log(self):
        open("app.log", "w", encoding="utf-8").close()
        self.log_append("[system] log cleared")

    def clear_uploads(self):
        self.uploaded = []

    def log_append(self, msg: str):
        write_log(msg)
        self.log_tick += 1

    def log_extend(self, msgs: list[str]):
        for m in msgs:
            write_log(m)
        self.log_tick += 1

    @rx.var
    def log_lines(self) -> list[str]:
        _ = self.log_tick
        for h in APP_LOG.handlers:
            try: h.flush()
            except: pass
        try:
            with open("app.log", "r", encoding="utf-8") as f:
                return f.read().splitlines()[-500:]
        except FileNotFoundError:
            return []

def terminal_box() -> rx.Component:
    return rx.box(
        rx.text(
            "Activity Log",
            style={"color": MUTED, "textTransform": "uppercase", "fontSize": "12px", "letterSpacing": "1px", "marginBottom": "8px"},
        ),
        rx.auto_scroll(
            rx.vstack(
                rx.foreach(
                    State.log_lines,
                    lambda line: rx.text(
                        line,
                        size="2",
                        style={"fontFamily": "'IBM Plex Mono', ui-monospace, monospace", "color": MUTED},
                    ),
                ),
                spacing="2",
                align_items="start",
                min_width="100%",
                style={"padding": "6px 6px 8px", "background": PANEL, "border": f"1px solid {EDGE}", "borderRadius": "6px", "marginTop": "6px"},
            ),
            height="220px",
            width="100%",
            style={
                "border": f"1px solid {EDGE}",
                "background": "#0e1013",
                "borderRadius": "8px",
                "padding": "10px",
                "fontSize": "12px",
                "color": MUTED,
                "overflowY": "auto",
            },
        ),
        rx.hstack(
            rx.button(
                "Clear",
                on_click=State.clear_log,
                style={"border": f"1px solid {EDGE}", "background": "#14171b", "color": TEXT, "borderRadius": "8px", "textTransform": "uppercase", "letterSpacing": ".5px"},
            ),
            spacing="3",
            width="100%",
            marginTop="10px",
        ),
        id="log",
    )

def upload_panel() -> rx.Component:
    selected = rx.selected_files("uploader")

    # --- Design tokens (px values OK for styles, NOT for `spacing`)
    CARD_MAX_W = "760px"
    GAP_SM = "10px"
    GAP_MD = "14px"
    GAP_LG = "18px"
    RADIUS = "12px"
    LABEL = {
        "color": MUTED,
        "fontSize": "12px",
        "letterSpacing": ".4px",
        "marginBottom": "6px",
        "opacity": 0.9,
    }
    FIELD = {"width": "100%", "background": "#0d0f12", "border": f"1px solid {EDGE}", "borderRadius": RADIUS}
    INPUT = {
        **FIELD,
        "padding": "10px 12px",
        "minHeight": "45px",
        "boxSizing": "border-box",
    }
    # Inline control so OS & Mode sit close (no extra CSS tricks)
    INPUT_INLINE = {**INPUT, "width": "auto"}

    def section_title(txt: str):
        return rx.text(
            txt,
            size="2",
            weight="medium",
            style={"color": MUTED, "letterSpacing": ".6px", "textTransform": "uppercase", "padding-bottom": "10px"},
        )

    # Outer wrapper (no rx.center)
    return rx.box(
        rx.box(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("New Case", size="4", weight="bold", style={"color": TEXT}),
                    rx.text("Upload memory dump and choose analysis options.", size="2", style={"color": MUTED}),
                    spacing="1",
                    align_items="start",
                ),
                width="100%",
                style={"marginBottom": GAP_MD},
            ),

            # Upload
            section_title("Upload"),
            rx.vstack(
                rx.upload(
                    rx.vstack(
                        rx.text("Drop files here", weight="bold", style={"color": TEXT}),
                        rx.text("or click to browse", size="2", style={"color": MUTED}),
                        spacing="1",
                        align_items="center",
                    ),
                    id="uploader",
                    multiple=True,
                    style={
                        **FIELD,
                        "width": "100%",
                        "padding": "20px",
                        "borderStyle": "dashed",
                        "textAlign": "center",
                        "transition": "border-color .15s ease, box-shadow .15s ease",
                        "boxShadow": "inset 0 1px 0 rgba(255,255,255,.03)",
                    },
                ),
                # Buttons directly under the uploader (original placement)
                rx.hstack(
                    rx.button(
                        "Upload",
                        on_click=State.handle_upload(
                            rx.upload_files(
                                upload_id="uploader",
                                on_upload_progress=State.handle_upload_progress,
                            )
                        ),
                        style={
                            "border": f"1px solid {EDGE}",
                            "background": ACCENT,
                            "color": "#0b0d10",
                            "borderRadius": RADIUS,
                            "textTransform": "uppercase",
                            "letterSpacing": ".5px",
                            "padding": "10px 14px",
                            "fontWeight": 600,
                        },
                    ),
                    rx.button(
                        "Clear selection",
                        on_click=rx.clear_selected_files("uploader"),
                        style={
                            "border": f"1px solid {EDGE}",
                            "background": "#14171b",
                            "color": TEXT,
                            "borderRadius": RADIUS,
                            "textTransform": "uppercase",
                            "letterSpacing": ".5px",
                            "padding": "10px 14px",
                        },
                    ),
                    spacing="3",
                    width="100%",
                    align_items="center",
                ),
                spacing="3",
                width="100%",
            ),

            # Selected files
            rx.cond(
                selected.length() > 0,
                rx.box(
                    rx.text("Selected files", style=LABEL),
                    rx.box(
                        rx.vstack(
                            rx.foreach(
                                selected,
                                lambda f: rx.hstack(
                                    rx.box(style={"width": "6px", "height": "6px", "borderRadius": "999px", "background": ACCENT}),
                                    rx.text(
                                        f,
                                        size="2",
                                        style={"color": TEXT, "whiteSpace": "nowrap", "textOverflow": "ellipsis", "overflow": "hidden"},
                                    ),
                                    spacing="2",
                                    align_items="center",
                                    width="100%",
                                ),
                            ),
                            spacing="2",
                            align_items="stretch",
                            width="100%",
                        ),
                        style={**FIELD, "padding": "10px 12px", "maxHeight": "160px", "overflow": "auto"},
                    ),
                    style={"marginTop": GAP_SM},
                ),
            ),

            # Progress
            rx.cond(
                State.show_progress,
                rx.vstack(
                    rx.text(
                        rx.cond(State.uploading, "Uploading…", "Upload complete"),
                        size="2",
                        style={"color": MUTED, "letterSpacing": ".5px"},
                    ),
                    rx.progress(
                        value=State.progress,
                        max=100,
                        color_scheme="purple",
                        style={
                            "width": "100%",
                            "height": "10px",
                            "background": "#0e1013",
                            "border": f"1px solid {EDGE}",
                            "borderRadius": RADIUS,
                            "accentColor": ACCENT,
                        },
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                    style={"marginTop": "2px"},
                ),
            ),

            # Divider
            rx.box(style={"height": "1px", "background": "rgba(255,255,255,.06)", "margin": f"{GAP_LG} 0 {GAP_MD} 0"}),

            # Details
            section_title("Details"),
            rx.vstack(
                rx.box(
                    rx.text("Case Name", style=LABEL),
                    rx.input(
                        value=State.case_name,
                        on_change=State.set_case_name,
                        placeholder="e.g. My Case 1",
                        aria_label="Case name",
                        style=INPUT,
                    ),
                    width="100%",
                ),
                rx.box(
                    rx.text("Case Description", style=LABEL),
                    rx.input(  # swap to rx.text_area if you prefer multiline
                        value=State.case_description,
                        on_change=State.set_case_description,
                        placeholder="Enter case description",
                        aria_label="Case description",
                        style=INPUT,
                    ),
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),

            rx.box(style={"height": "1px", "background": "rgba(255,255,255,.06)", "margin": f"{GAP_LG} 0 {GAP_MD} 0"}),
            section_title("Analysis Options"),
            rx.hstack(
                rx.vstack(
                    rx.text("OS", style={**LABEL, "textAlign": "center", "width": "100%"}),
                    rx.select(
                        State.os_values,
                        placeholder="Select OS",
                        value=State.os_value,
                        on_change=State.set_os_value,
                        style=INPUT_INLINE,
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Mode", style={**LABEL, "textAlign": "center", "width": "100%"}),
                    rx.select(
                        State.mode_values,
                        placeholder="Select Mode",
                        value=State.mode_value,
                        on_change=State.set_mode_value,
                        style=INPUT_INLINE,
                    ),
                    spacing="1",
                ),
                # New checkable buttond
                spacing="3",          # tiny gaps so everything stays close
                align_items="center",
                width="100%",
            ),

            # Card styling
            style={
                "width": f"min({CARD_MAX_W}, 92vw)",
                "padding": "22px 90px",
                "border": f"1px solid {EDGE}",
                "background": "linear-gradient(180deg, #121417 0%, #0c0f13 100%)",
                "boxShadow": "inset 0 1px 0 rgba(255,255,255,.03), 0 10px 40px rgba(0,0,0,0.45)",
                "borderRadius": RADIUS,
                "margin": "0 auto",
            },
        ),
        style={"padding": "18px 10px"},
    )
def index() -> rx.Component:
    return rx.box(
        # --- Background: Spline ---
        _spline_background("https://prod.spline.design/BusTwZ53zGkEXgPP/scene.splinecode"),

        # --- Foreground content (interactive) ---
        rx.hstack(
            sidebar("upload"),
            rx.box(
                rx.container(
                    rx.vstack(
                        upload_panel(),
                        rx.box(height="16px"),
                        terminal_box(),
                        spacing="6",
                        align_items="stretch",
                        min_height="85vh",
                    ),
                    size="3",
                ),
                style={"flex": 1, "padding": "24px"},
            ),
            align="start",
            width="100%",
            z_index=2,
            style={
                "position": "relative",
                "color": TEXT,
                "fontFamily": "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
            },
        ),
        style={
            "minHeight": "100vh",
            "position": "relative",
            "background": "transparent",
            "backgroundColor": "#0b0d0f",  # fallback if Spline fails
        },
    )



app = rx.App(
    theme=rx.theme(appearance="dark", accent_color="purple", gray_color="mauve"),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap",
        "/style.css"
    ],
)

app.add_page(index, title="MultiVol")
app.add_page(cases, route="/cases", title="Cases")
app.add_page(table, route="/sheet", title="sheet",on_load=TableState.load_entries)
app.add_page(index_profiles, route="/profiles", title="Profiles")
