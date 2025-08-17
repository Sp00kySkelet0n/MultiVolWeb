import reflex as rx
class Spline(rx.Component):
    library = "@splinetool/react-spline"
    lib_dependencies: list[str] = ["@splinetool/runtime@1.10.48"]
    tag = "Spline"
    is_default = True

    scene: rx.Var[str]
    # add this so mouse tracking works even with pointer-events:none overlays
    events_target: rx.Var[str] = "global" 

def _spline_background(SPLINE_SCENE: str) -> rx.Component:
    spline = Spline.create
    return rx.box(
        spline(scene=SPLINE_SCENE),
        position="fixed",
        top="0",
        left="0",
        right="0",
        bottom="0",
        z_index=0,
        class_name="spline-bg-in",
        style={"pointerEvents": "none", "contain": "layout paint size"},
    )

