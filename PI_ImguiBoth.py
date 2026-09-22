"""PI_ImguiBoth.py -- side-by-side comparison of the two xp_imgui render paths.

Basically, we use a different backend, depending on set window content type:

  LEFT  window: contentType = WindowContentTypeOpenGL        (XPRenderer, works <12.4.4)
  RIGHT window: contentType = WindowContentTypePanelGraphics (XPPanelGraphicsRenderer, requires 12.4.4+))

Both windows run the SAME draw function against their OWN state, so any
difference in appearance or in click behaviour is a renderer difference and
nothing else. Interactivity is handled entirely in xp_imgui/window.py (it feeds
io.mouse_pos / io.mouse_down / keyboard), which both paths share -- so if the
right-hand window ever draws but does not respond to clicks, the fault is in the
coordinate space handed to the renderer, not in the input plumbing.

xp_imgui.Window takes a contentType and picks XPRenderer or
XPPanelGraphicsRenderer from it.

Known gap in the panel-graphics renderer: pyimgui here is built with 32-bit
indices, which XPLMDrawCalls cannot take, so every draw list is narrowed to
uint16. A list needing more than 65536 vertices is SKIPPED with one log line
rather than split on vtx_offset. If part of the right-hand window silently fails
to draw, check the log for that message first.

The two windows render identically EXCEPT for translucent colors, which are
expected to differ and are NOT a renderer fault. The difference is obvious for
low-alpha fills and slight for nearly-opaque ones:

  * every color with alpha == 1.0 matches exactly -- the R/G/B bars below, and
    the button while hovered/active (those ImGui styles are opaque);
  * every color with alpha < 1.0 differs, panel graphics being brighter --
    the idle button (ImGuiCol_Button is rgba(0.26, 0.59, 0.98, 0.40)) read
    #2d4667 on OpenGL vs #3c63a2 on panel graphics, and the window background
    #121313 vs #171819.

In the demo, the color difference is most noticeable on the "Pressed n times" button:
the PanelGraphics version of the button appears lighter in color.

Blending ImGui's Button color against each window's own background reproduces
those numbers when OpenGL is modelled as compositing in sRGB and panel graphics
in LINEAR space (green channel: predicted 72 vs observed 70, and 100 vs 99,
respectively). So XPLMDrawCalls blends in linear space and the legacy
immediate-mode GL path does not. A renderer cannot compensate -- the result
depends on the destination pixel -- and linear is the physically correct one, so
exact color parity between the two paths is not an achievable goal.

XPLMPanelGraphics.h documents straight (non-pre-multiplied) alpha but never says
which color space the blend happens in; that is worth an SDK doc request.

The draw function deliberately includes:
  * a button and a text input       -- proves hit-testing and keyboard focus
  * a scrolling child region        -- forces multiple clipped draw commands
  * a wide color bar                -- forces a large vertex/index batch and makes
                                       any vertical flip or color-order error obvious
  * corner markers                  -- top-left is labelled, so an inverted Y is visible

Menu: Plugins > Imgui Both (re)open windows.
Results go to XPPython3Log.txt, prefixed [ImguiBoth].

"""
import os
from typing import Any, Optional, Self

import imgui

from XPPython3 import xp
from XPPython3 import xp_imgui
from XPPython3.xp_typing import XPLMCommandRef

WIDTH = 520
HEIGHT = 520
GAP = 40
TOP_OFFSET = 110
LEFT_OFFSET = 110


class PythonInterface:
    def __init__(self: Self) -> None:
        self.Name = "Imgui Both"
        self.Sig = "xppython3.imgui_both"
        self.Desc = "Side-by-side OpenGL vs panel-graphics imgui rendering"
        self.windows: dict[str, dict] = {}
        self.cmd: Optional[XPLMCommandRef] = None

    def log(self, msg: str = '') -> None:
        print(f"[ImguiBoth]: {msg}", flush=True)

    # ---- lifecycle -----------------------------------------------------------

    def XPluginStart(self: Self) -> tuple[str, str, str]:
        versions = xp.getVersions()
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")
        self.cmd = xp.createCommand(f"xppython3/{os.path.basename(__file__)}/openWindows",
                                    "Open imgui comparison windows")
        xp.registerCommandHandler(self.cmd, self.commandHandler, 1, None)
        xp.appendMenuItemWithCommand(xp.findPluginsMenu(), 'Imgui Both', self.cmd)
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self: Self) -> int:
        self.openWindows()
        return 1

    def XPluginDisable(self: Self) -> None:
        self.closeWindows()

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def XPluginStop(self: Self) -> None:
        self.closeWindows()
        xp.unregisterCommandHandler(self.cmd, self.commandHandler, 1, None)
        xp.clearAllMenuItems(xp.findPluginsMenu())

    def commandHandler(self: Self, _cmdRef: XPLMCommandRef, phase: int, _refCon: Any) -> int:
        if phase == xp.CommandBegin:
            self.closeWindows()
            self.openWindows()
        return 1

    # ---- window management ---------------------------------------------------

    def openWindows(self: Self) -> None:
        left, top, _right, _bottom = xp.getScreenBoundsGlobal()
        x0 = left + LEFT_OFFSET
        y0 = top - TOP_OFFSET

        self.makeWindow('OpenGL', xp.WindowContentTypeOpenGL, x0, y0)
        self.makeWindow('PanelGraphics', xp.WindowContentTypePanelGraphics,
                        x0 + WIDTH + GAP, y0)

    def makeWindow(self: Self, label: str, contentType: int, x: int, y: int) -> None:
        state = {'label': label,
                 'buttonPresses': 0,
                 'text': 'type here',
                 'slider': 4.75,
                 'checkbox': False,
                 'frames': 0,
                 'stress': 0}
        try:
            win = xp_imgui.Window(left=x, top=y, right=x + WIDTH, bottom=y - HEIGHT,
                                  visible=1, draw=self.drawWindow, refCon=state,
                                  contentType=contentType)
        except Exception as e:  # noqa: BLE001
            self.log(f"{label}: window creation failed: {e!r}")
            return

        win.setTitle(f"imgui -- {label}")
        state['instance'] = win
        self.windows[label] = state
        self.log(f"{label}: window created at ({x}, {y}) {WIDTH}x{HEIGHT}")

    def closeWindows(self: Self) -> None:
        for label in list(self.windows):
            inst = self.windows[label].get('instance')
            if inst is not None:
                try:
                    inst.delete()
                except Exception as e:  # noqa: BLE001
                    self.log(f"{label}: delete() raised {e!r}")
            del self.windows[label]

    # ---- the shared draw function -------------------------------------------

    def drawWindow(self: Self, _windowID, refCon) -> None:
        """Run for BOTH windows. Identical output is the pass condition."""
        refCon['frames'] += 1

        # Corner marker: imgui's origin is TOP-LEFT. If this label is not at the
        # top of the window, the renderer flipped Y.
        imgui.text_colored(text=f"^ TOP-LEFT  [{refCon['label']}]", r=1.0, g=0.8, b=0.0, a=1.0)
        imgui.text(f"frame {refCon['frames']}")
        imgui.separator()

        # Hit-testing.
        if imgui.button(f"Pressed {refCon['buttonPresses']} times"):
            refCon['buttonPresses'] += 1

        # Keyboard focus.
        _changed, refCon['text'] = imgui.input_text("Text input", refCon['text'], 50)

        # Drag + continuous update.
        _changed, refCon['slider'] = imgui.slider_float("Slider", refCon['slider'], 0.0, 10.0)
        _changed, refCon['checkbox'] = imgui.checkbox(label="Checkbox", state=refCon['checkbox'])

        imgui.separator()

        # Color bar: pure R, G, B blocks. A byte-order error in the packed RGBA8
        # vertex color shows up here immediately (red and blue would swap).
        imgui.text("color order: red green blue")
        drawList = imgui.get_window_draw_list()
        px, py = imgui.get_cursor_screen_position()
        barH = 24
        barW = 120
        for i, color in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
            drawList.add_rect_filled(px + i * (barW + 6), py,
                                     px + i * (barW + 6) + barW, py + barH,
                                     imgui.get_color_u32_rgba(*color, 1.0))
        imgui.dummy(0, barH + 6)

        imgui.separator()

        # Scrolling child region -- forces several clipped draw commands, which is
        # where a wrong scissor rect (or wrong scissor coordinate space) shows up.
        imgui.text("scroll me (clipped draw commands):")
        imgui.begin_child("scroll", 0, 180, border=True)
        for i in range(60 + refCon['stress']):
            imgui.text(f"row {i:02d} " + "-" * (i % 20))
        imgui.end_child()

        # Stress knob: rows are emitted with NO ImGuiListClipper, so every row costs
        # vertices whether or not it is visible -- which is the point. Sweep this to
        # get cost-per-vertex rather than a single data point. Note the panel-graphics
        # path starts SKIPPING draw lists once one exceeds 65536 vertices; the log
        # says so when it happens, and that threshold is worth finding here.
        _changed, refCon['stress'] = imgui.slider_int("stress rows", refCon['stress'], 0, 3000)

        imgui.text(f"mouse: {imgui.get_io().mouse_pos.x:.0f}, {imgui.get_io().mouse_pos.y:.0f}")
