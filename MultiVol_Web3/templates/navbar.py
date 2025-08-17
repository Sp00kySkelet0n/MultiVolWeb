import reflex as rx

BG = "#0b0d0f"
PANEL = "#121417"
EDGE = "#272b31"
TEXT = "#d3d6db"
MUTED = "#8b9097"

def nav_link(label: str, href: str = "#", active: bool = False) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.text(label, size="3", weight="medium"),
            width="100%",
            justify="start",
            align="center",
            spacing="2",
        ),
        href=href,
        aria_current="page" if active else "false",
        style={
            "display": "block",
            "width": "100%",
            "color": TEXT,
            "textDecoration": "none",
            "padding": "10px 12px",
            "borderRadius": "10px",
            "border": f"1px solid {EDGE}" if active else "1px solid transparent",
            "background": "linear-gradient(180deg, #1a1d22 0%, #171a1e 100%)" if active else "transparent",
            "boxShadow": "0 1px 0 rgba(0,0,0,.3)" if active else "none",
            "transition": "background .18s ease, border-color .18s ease, transform .08s ease",
            "cursor": "pointer",
        },
        _hover={"background": "#191d21", "borderColor": EDGE, "transform": "translateY(-1px)"},
        _focus={"outline": "none", "boxShadow": "0 0 0 2px rgba(211,214,219,.16)"},
    )

def sidebar(active_tab: str) -> rx.Component:
    is_upload_active = active_tab == "upload"
    is_cases_active = active_tab == "cases"
    is_profiles_active = active_tab == "profiles"
    return rx.box(
        # ── Header with favicon on the left ─────────────────────────────────────
        rx.box(
            rx.hstack(
                rx.image(
                    src="/favicon.ico",
                    alt="App icon",
                    width="40px",
                    height="40px",
                    object_fit="contain",
                    draggable=False,
                    fallback_src="/favicon-32x32.png",  # optional PNG fallback
                    style={
                        "display": "block",
                        "userSelect": "none",
                        "borderRadius": "4px",
                        "filter": "drop-shadow(0 1px 0 rgba(0,0,0,.35))",
                    },
                ),
                rx.image(
                    src="/multivol_header.png",
                    alt="Multivol",
                    height="36px",
                    width="auto",
                    object_fit="contain",
                    draggable=False,
                    fallback_src="/multivol_header@2x.png",
                    style={
                        "display": "block",
                        "userSelect": "none",
                        "filter": "drop-shadow(0 1px 0 rgba(0,0,0,.35))",
                    },
                ),
                align="center",
                spacing="2",
            ),
            style={
                "padding": "16px 14px",
                "borderBottom": f"1px solid {EDGE}",
                "position": "sticky",
                "top": 0,
                "zIndex": 2,
                "background": "linear-gradient(180deg, rgba(18,20,23,.98), rgba(18,20,23,.86))",
                "backdropFilter": "blur(2px)",
            },
        ),

        # Nav list
        rx.box(
            rx.vstack(
                nav_link("Upload", "/", active=is_upload_active),
                nav_link("Cases", "/cases", active=is_cases_active),
                nav_link("Profiles", "/profiles", active=is_profiles_active),
                spacing="1",
                align_items="stretch",
                width="100%",
                style={"padding": "6px", "display": "grid", "gap": "6px"},
            ),
            style={
                "padding": "8px",
                "overflowY": "auto",
                "maxHeight": "calc(100vh - 68px)",
            },
        ),

        # Optional footer
        rx.box(
            rx.text("v1.0 • Multivol", size="1", color=MUTED),
            style={"padding": "10px 14px", "marginTop": "auto", "opacity": .9},
        ),

        style={
            "background": PANEL,
            "borderRight": f"1px solid {EDGE}",
            "minHeight": "100vh",
            "width": "240px",
            "position": "sticky",
            "top": 0,
            "left": 0,
            "display": "flex",
            "flexDirection": "column",
        },
    )
