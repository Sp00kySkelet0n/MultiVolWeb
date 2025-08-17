# main file
from __future__ import annotations
import reflex as rx
from .templates.navbar import sidebar
from .templates.spline_func import _spline_background

BG = "#0b0d0f"
PANEL = "#121417"
EDGE = "#272b31"
TEXT = "#d3d6db"
MUTED = "#8b9097"
ACCENT = "#a200ff"

class State(rx.State):
    show_progress: bool = False
    uploaded: list[str] = []
    uploading: bool = False
    progress: int = 0
    profile_name: str = ""
    async def handle_upload(self, files: list[rx.UploadFile]):
        from pathlib import Path
        # Save uploads under <this_file_dir>/profiles_json
        root_profiles_path = Path(__file__).parent / "profiles_json"
        root_profiles_path.mkdir(parents=True, exist_ok=True)

        saved_batch: list[str] = []
        for file in files:
            data = await file.read()
            path = root_profiles_path / file.name
            with path.open("wb") as f:
                f.write(data)
            self.uploaded.append(file.name)
            saved_batch.append(file.name)

        try:
            paths = [str(root_profiles_path / name) for name in saved_batch]
            yield
        except Exception as e:
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
        "padding": "10px 12px",     # symmetric top/bottom
        "minHeight": "45px",        # a touch taller to clear descenders
        "boxSizing": "border-box",
    }

    def section_title(txt: str):
        return rx.text(
            txt,
            size="2",
            weight="medium",
            style={"color": MUTED, "letterSpacing": ".6px", "textTransform": "uppercase"},
        )

    # Outer wrapper (no rx.center to keep it simple)
    return rx.box(
        rx.box(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("Upload Custom Profile", size="4", weight="bold", style={"color": TEXT}),
                    rx.text("Upload a custom profile to use in analysis", size="2", style={"color": MUTED}),
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
                ),
                spacing="3",  # token, not px
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
                    rx.text("Profile Name", style=LABEL),
                    rx.input(
                        value=State.profile_name,
                        on_change=State.set_profile_name,
                        placeholder="e.g. My Profile 1",
                        aria_label="Profile name",
                        style=INPUT,
                    ),
                    width="100%",
                ),
                spacing="3",  # token
                width="100%",
            ),

            # Card styling
            style={
                "width": f"min({CARD_MAX_W}, 92vw)",
                "padding": "22px 24px",
                "border": f"1px solid {EDGE}",
                "background": "linear-gradient(180deg, #121417 0%, #0c0f13 100%)",
                "boxShadow": "inset 0 1px 0 rgba(255,255,255,.03), 0 10px 40px rgba(0,0,0,0.45)",
                "borderRadius": RADIUS,
                "margin": "0 auto",
            },
        ),
        style={"padding": "18px 10px"},
    )

def index_profiles() -> rx.Component:
    return rx.box(
        _spline_background("https://prod.spline.design/BusTwZ53zGkEXgPP/scene.splinecode"),

        # 1) Optional readability overlay (semi-transparent)
        rx.box(
            position="fixed", top="0", left="0", right="0", bottom="0",
            z_index=1,
            style={
                "pointerEvents": "none",
                "background": (
                    "radial-gradient(1200px 800px at 10% -10%, rgba(20,23,27,0.35) 0%, transparent 60%),"
                    "radial-gradient(1000px 600px at 110% 110%, rgba(15,18,22,0.35) 0%, transparent 60%)"
                ),
            },
        ),

        # 2) Foreground content (interactive)
        rx.hstack(
            sidebar("profiles"),
            rx.box(
                rx.container(
                    rx.vstack(
                        upload_panel(),
                        rx.box(height="16px"),
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
                "position": "relative",   # needed so z_index works
                "minHeight": "100vh",
                "background": "transparent",   # <-- important: no opaque gradient here
                "color": TEXT,
                "fontFamily": "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
            },
        ),

        # page wrapper
        style={
            "minHeight": "100vh",
            "position": "relative",
            "isolation": "isolate",        # stable stacking context
            "background": "transparent",
            "backgroundColor": "#0b0d0f",  # fallback if Spline fails
        },
    )
