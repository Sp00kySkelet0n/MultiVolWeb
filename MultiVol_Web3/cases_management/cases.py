# cases.py
import reflex as rx
from pathlib import Path
import os, json, glob
from typing import Any, List, Dict
import shutil
from ..templates.spline_func import _spline_background
from ..templates.navbar import sidebar
from uuid import uuid4

BG = "#0b0d0f"
PANEL = "#121417"
EDGE = "#272b31"
TEXT = "#d3d6db"
MUTED = "#8b9097"


class Check(rx.Base):
    name: str
    failure: bool
    missing: bool = False


class CaseCardData(rx.Base):
    title: str
    desc: str
    os_name: str
    os_slug: str
    slug: str
    avatar_src: str
    sheet_href: str
    checks: List[Check] = []


def _slug(s: str) -> str:
    return s.replace(" ", "_")


def _json_failure_flag(data: Any) -> bool:
    if data == 0:
        return True
    """Best-effort failure flag (handles dicts & lists)."""
    if isinstance(data, dict):
        if isinstance(data.get("failure"), bool):
            return bool(data["failure"])
        if data.get("status") in {"failed", "error"}:
            return True
        if any(k in data for k in ("error", "traceback", "exception")):
            return True
        return False
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if item.get("failure") is True:
                    return True
                if item.get("status") in {"failed", "error"}:
                    return True
                if any(k in item for k in ("error", "traceback", "exception")):
                    return True
        return False
    return False


def _label_from_filename(f: str) -> str:
    name = Path(f).name
    suffix = "_output.json"
    if name.endswith(suffix):
        base = name[: -len(suffix)]
        # take the segment after the last '.' if present
        if "." in base:
            return base.split(".")[-1]
    return Path(f).stem


# -------------------- MODULE LIST PER-OS --------------------

def _collect_module_labels_by_os(cases_dir: Path) -> Dict[str, List[str]]:
    """
    Build a dict: os_slug -> sorted list of module labels,
    collecting from each case's volatility3_output but only grouped by that case's OS.
    """
    labels_by_os: Dict[str, set] = {}

    for entry in os.scandir(cases_dir):
        if not entry.is_dir():
            continue

        folder = Path(entry.path)
        details_path = folder / "case_details.json"
        if not details_path.exists():
            continue

        try:
            with open(details_path, "r", encoding="utf-8") as f:
                os_name = str(json.load(f).get("case_os", "Unknown"))
        except Exception:
            os_name = "Unknown"

        os_slug = os_name.lower()
        labels_set = labels_by_os.setdefault(os_slug, set())

        out_dir = folder / "volatility3_output"
        if out_dir.exists():
            for f in glob.glob(str(out_dir / "*.json"), recursive=True):
                labels_set.add(_label_from_filename(f))

    # sort lists for stable display order
    return {k: sorted(v) for k, v in labels_by_os.items()}


def _get_case_checks_from_master(folder: Path, module_labels: List[str]) -> List[Check]:
    """
    For a given case folder, return checks in the SAME order as module_labels.
    If a module is missing in this case, mark it as missing=True (not a failure).
    """
    out_dir = folder / "volatility3_output"
    present = {}

    if out_dir.exists():
        files = sorted(glob.glob(str(out_dir / "*.json"), recursive=True))
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    present[_label_from_filename(f)] = _json_failure_flag(data)  # True means error
            except Exception:
                present[_label_from_filename(f)] = _json_failure_flag(0)  # treat as error

    checks: List[Check] = []
    for label in module_labels:
        if label in present:
            checks.append(Check(name=label, failure=present[label], missing=False))
        else:
            # Not present: show as missing (distinct icon), not a failure
            checks.append(Check(name=label, failure=False, missing=True))
    return checks


# ----------------------------------------------------------------------


def _gather_cases() -> List[CaseCardData]:
    """Build a list of cases with all UI-ready fields precomputed."""
    cases_dir = Path(__file__).parent.parent / "cases"

    # Build per-OS canonical module lists once
    module_labels_by_os = _collect_module_labels_by_os(cases_dir)

    all_cases: List[CaseCardData] = []
    for entry in os.scandir(cases_dir):
        if not entry.is_dir():
            continue

        folder = Path(entry.path)
        case_details_path = folder / "case_details.json"
        if not case_details_path.exists():
            continue

        with open(case_details_path, "r", encoding="utf-8") as f:
            case_json = json.load(f)

        title = case_json.get("case_name", folder.name)
        desc = case_json.get("case_details", "")
        os_name = case_json.get("case_os", "Unknown")
        os_slug = str(os_name).lower()
        slug = _slug(title)

        # Use only the module labels for this case's OS
        module_labels = module_labels_by_os.get(os_slug, [])

        all_cases.append(
            CaseCardData(
                title=title,
                desc=desc,
                os_name=os_name,
                os_slug=os_slug,
                slug=slug,
                avatar_src=f"/{os_slug}.png",
                sheet_href=f"/sheet?case={slug}",
                checks=_get_case_checks_from_master(folder, module_labels),
            )
        )

    return all_cases


# --- State: loads fresh cases on each page mount ---
class CasesState(rx.State):
    cases: List[CaseCardData] = []
    menu_open_for: str = ""  # which card's menu is open (by title or slug)

    def load(self):
        # Called on page mount/refresh to repopulate cases
        self.cases = _gather_cases()

    def toggle_menu(self, title: str):
        self.menu_open_for = "" if self.menu_open_for == title else title

    def close_menu(self):
        self.menu_open_for = ""

    def menu_delete(self, title: str):
        slug = _slug(title)
        current_path_parent = Path(__file__).parent.parent
        case_path = current_path_parent / "cases" / slug
        case_details_path = case_path / "case_details.json"
        # Verify if case_details exist as safety feature
        if case_details_path.exists():
            shutil.rmtree(case_path)
            self.menu_open_for = ""
            self.cases = _gather_cases()

    @rx.event
    def menu_download_zip(self, title: str):
        # Hacky way of downloading files because apparently Reflex streams everything through the websocket 
        # So we hit a size limitation and crash the backend ????????
        slug = _slug(title)
        base = Path(__file__).parent.parent
        case_path = base / "cases" / slug
        if (case_path / "case_details.json").exists():
            # write the zip into Reflex's uploaded_files dir
            name = f"{slug}-{uuid4().hex}.zip"
            out_dir = rx.get_upload_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            base_name = out_dir / name
            shutil.make_archive(
                str(base_name.with_suffix("")),
                "zip",
                root_dir=case_path.parent,
                base_dir=case_path.name,
            )
            # trigger a browser download via URL (served at /_upload/<name>)
            url = rx.get_upload_url(name)
            yield rx.download(url=url, filename=f"{slug}.zip")


def case_card(title, desc, os_name, avatar_src, sheet_href, checks) -> rx.Component:
    """All inputs can be Vars; strings are precomputed to avoid concat."""

    def _check_item(chk):
        return rx.list.item(
            rx.hstack(
                rx.cond(
                    chk.missing,
                    rx.icon("circle_help", color="orange", size=12),
                    rx.cond(
                        chk.failure,
                        rx.icon("octagon_x", color="red", size=12),     # error icon
                        rx.icon("circle_check_big", color="green", size=12),  # ok icon
                    ),
                ),
                rx.text(
                    chk.name,
                    size="1",
                    style={
                        "lineHeight": "1.1",
                        "whiteSpace": "nowrap",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "display": "block",
                        "minWidth": 0,
                    },
                ),
                spacing="1",
                align="center",
                style={"minWidth": 0, "width": "100%"},
            ),
            style={"breakInside": "avoid"},
        )

    return rx.card(
        rx.box(
            rx.link(
                rx.hstack(
                    rx.box(
                        rx.image(
                            src=avatar_src,
                            alt=os_name,
                            style={"width": "28px", "height": "28px", "objectFit": "contain"},
                        ),
                        href=sheet_href,
                        style={
                            "width": "36px",
                            "height": "36px",
                            "padding": "4px",
                            "borderRadius": "8px",
                            "border": f"1px solid {EDGE}",
                            "background": "#0e1013",
                            "display": "block",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "flexShrink": 0,
                            "overflow": "hidden",
                        },
                    ),
                    rx.vstack(
                        rx.box(
                            rx.text(title, style={"color": TEXT, "fontWeight": 700}),
                            rx.text(
                                desc,
                                size="1",
                                style={
                                    "color": MUTED,
                                    "whiteSpace": "normal",
                                    "wordBreak": "break-word",
                                },
                            ),
                            rx.text(os_name, size="1", style={"color": MUTED, "opacity": 0.8}),
                            spacing="1",
                            align_items="start",
                            style={"minWidth": 0},
                        ),
                        rx.box(
                            rx.list(
                                rx.foreach(checks, _check_item),
                                list_style_type="none",
                                style={
                                    "margin": 0,
                                    "padding": 0,
                                    "fontSize": "12px",
                                    "columnCount": 2,
                                    "columnGap": "12px",
                                },
                                spacing="1",
                            ),
                            style={
                                "display": "block",
                                "overflowY": "auto",
                                "width": "100%",
                                "paddingRight": "2px",
                                "minHeight": "0",
                                "maxHeight": "100%",
                                "flex": "1 1 0",
                            },
                        ),
                        spacing="2",
                        align_items="start",
                        style={
                            "minWidth": 0,
                            "display": "flex",
                            "flexDirection": "column",
                            "height": "100%",
                            "minHeight": "0",
                        },
                    ),
                    style={"height": "100%", "minHeight": "0"},
                ),
                href=sheet_href,
                style={"display": "block", "height": "100%", "position": "relative", "zIndex": 10},
            ),

            # top-right custom menu
            rx.box(
                rx.box(
                    "☰",
                    on_click=CasesState.toggle_menu(title),
                    role="button",
                    aria_label="Open menu",
                    style={
                        "all": "unset",
                        "background": "#0b0d0f",
                        "fontSize": "20px",
                        "color": TEXT,
                        "border": f"1px solid {EDGE}",
                        "height": "32px",
                        "lineHeight": "32px",
                        "padding": "0 8px",
                        "display": "inline-flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "borderRadius": "6px",
                        "cursor": "pointer",
                        "userSelect": "none",
                        "position": "relative",
                        "zIndex": 60,
                    },
                ),
                # Panel
                rx.cond(
                    CasesState.menu_open_for == title,
                    rx.box(
                        # caret
                        rx.box(
                            style={
                                "position": "absolute",
                                "top": "-5px",
                                "right": "12px",
                                "width": "10px",
                                "height": "10px",
                                "background": "#111419",
                                "borderLeft": f"1px solid {EDGE}",
                                "borderTop": f"1px solid {EDGE}",
                                "transform": "rotate(45deg)",
                                "pointerEvents": "none",
                            }
                        ),
                        rx.vstack(
                            rx.button(
                                "Download as zip",
                                on_click=CasesState.menu_download_zip(title).prevent_default,
                                style={
                                    "all": "unset",
                                    "boxSizing": "border-box",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "flex-start",
                                    "gap": "8px",
                                    "width": "100%",
                                    "height": "32px",
                                    "padding": "0 10px",
                                    "borderRadius": "8px",
                                    "cursor": "pointer",
                                    "fontWeight": 600,
                                    "fontSize": "12px",
                                    "lineHeight": "1",
                                    "textAlign": "left",
                                    "color": TEXT,
                                    "whiteSpace": "nowrap",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "margin": 0,
                                    "background": "rgba(26,29,33,.6)",
                                    "border": f"1px solid {EDGE}",
                                },
                            ),
                            rx.button(
                                "Delete",
                                on_click=CasesState.menu_delete(title),
                                style={
                                    "all": "unset",
                                    "boxSizing": "border-box",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "flex-start",
                                    "gap": "8px",
                                    "width": "100%",
                                    "height": "32px",
                                    "padding": "0 10px",
                                    "borderRadius": "8px",
                                    "cursor": "pointer",
                                    "fontWeight": 600,
                                    "fontSize": "12px",
                                    "lineHeight": "1",
                                    "textAlign": "left",
                                    "color": "#ff6b70",
                                    "whiteSpace": "nowrap",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "margin": 0,
                                    "background": "rgba(40,16,18,.6)",
                                    "border": "1px solid rgba(255,77,79,.35)",
                                },
                            ),
                            spacing="1",
                            width="100%",
                            style={"alignItems": "stretch"},
                        ),
                        style={
                            "position": "absolute",
                            "top": "32px",
                            "right": "0",
                            "width": "180px",
                            "padding": "6px",
                            "borderRadius": "10px",
                            "background": "#111419",
                            "backdropFilter": "blur(6px)",
                            "border": f"1px solid {EDGE}",
                            "boxShadow": "0 12px 32px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.04)",
                            "zIndex": 100,
                            "overflow": "hidden",
                        },
                    ),
                ),
                style={
                    "position": "absolute",
                    "top": "-6px",
                    "right": "-6px",
                    "zIndex": 50,
                },
            ),

            style={"height": "100%", "position": "relative", "overflow": "visible"},
        ),
        style={"height": "100%"},
    )


def cases() -> rx.Component:
    grid = rx.flex(
        rx.foreach(
            CasesState.cases,
            lambda item: case_card(
                item.title,
                item.desc,
                item.os_name,
                item.avatar_src,
                item.sheet_href,
                item.checks,
            ),
        ),
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fill, minmax(220px, 1fr))",
            "gap": "12px",
            "gridAutoRows": "260px",
        },
    )

    return rx.box(
        _spline_background("https://prod.spline.design/290CoJlvjCRaIn3S/scene.splinecode"),
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
        rx.hstack(
            sidebar('cases'),
            rx.box(
                rx.container(
                    rx.vstack(
                        rx.text(
                            "Cases",
                            style={
                                "color": TEXT,
                                "textTransform": "uppercase",
                                "fontSize": "12px",
                                "letterSpacing": "1px",
                                "marginBottom": "8px",
                            },
                        ),
                        grid,
                        spacing="4",
                        align_items="stretch",
                        min_height="85vh",
                    ),
                    size="3",
                    on_mount=CasesState.load,
                ),
                style={"flex": 1, "padding": "24px"},
            ),
            align="start",
            width="100%",
            style={
                "minHeight": "100vh",
                "background": (
                    "radial-gradient(1200px 800px at 10% -10%, #14171b 0%, transparent 60%),"
                    "radial-gradient(1000px 600px at 110% 110%, #0f1216 0%, transparent 60%),"
                    "linear-gradient(#0b0d0f, #0b0d0f)"
                ),
                "color": TEXT,
                "fontFamily": "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
            },
        ),
    )
