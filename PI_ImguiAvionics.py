"""
PI_ImguiAvionics.py -- ImGui inside an AVIONICS DEVICE screen.

Where PI_ImguiBoth.py puts ImGui in an XPLMCreateWindowEx window, this puts the
same widgets on a createAvionicsEx() device, via xp_imgui.AvionicsDevice. Both
share host.ImguiHost -- the imgui context, frame loop and keyboard handling are
identical code; only the host differs.

Panel graphics only, by construction: the OpenGL renderer needs a windowID and
the boxel/native matrix chain, which a device has no equivalent of.

What to check, in rough order of likelihood of being wrong:
  * TOP-LEFT label at the top      -- screen touch coords are device-local with a
                                      BOTTOM-LEFT origin and get flipped by
                                      AvionicsDevice.toImguiSpace(); if the
                                      widgets respond to clicks at the wrong
                                      height, that flip is the suspect
  * button/slider respond to click -- proves the flip AND that screenTouch is
                                      wired to io.mouse_pos / io.mouse_down
  * widgets highlight on HOVER     -- screenCursor drives this; the window path
                                      has no equivalent, so this is new behaviour
  * the scroll region scrolls      -- screenScroll feeds io.mouse_wheel; the
                                      window path discards the wheel entirely, so
                                      this is also new
  * text input takes keystrokes    -- only works in the POP-UP: keyboard focus is
                                      a pop-up concept for devices

Menu: Plugins > Imgui Avionics (toggle pop-up).
Results go to XPPython3Log.txt, prefixed [ImguiAvionics].
"""
import os
from typing import Any, Optional, Self

import imgui

from XPPython3 import xp
from XPPython3 import xp_imgui
from XPPython3.xp_typing import XPLMCommandRef

SCREEN_W = 520
SCREEN_H = 460
BEZEL_PAD = 24
DEVICE_ID = "xppython3.imguiavionics"


class PythonInterface:
    def __init__(self: Self) -> None:
        self.Name = "Imgui Avionics"
        self.Sig = "xppython3.imgui_avionics"
        self.Desc = "ImGui rendered into a createAvionicsEx device screen"
        self.device: Optional[xp_imgui.AvionicsDevice] = None
        self.cmd: Optional[XPLMCommandRef] = None
        self.state = {'buttonPresses': 0, 'text': 'type here', 'slider': 4.75,
                      'checkbox': False, 'frames': 0}

    def log(self: Self, msg: str = '') -> None:
        print(f"[ImguiAvionics]: {msg}", flush=True)

    # ---- lifecycle -----------------------------------------------------------

    def XPluginStart(self: Self) -> tuple[str, str, str]:
        versions = xp.getVersions()
        self.log(f"X-Plane {versions[0]}, XPLM {versions[1]}")
        # Session-global: created once, never per enable.
        self.cmd = xp.createCommand(f"xppython3/{os.path.basename(__file__)}/togglePopup",
                                    "Toggle imgui avionics pop-up")
        xp.registerCommandHandler(self.cmd, self.commandHandler, 1, None)
        xp.appendMenuItemWithCommand(xp.findPluginsMenu(), 'Imgui Avionics', self.cmd)
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self: Self) -> int:
        try:
            self.device = xp_imgui.AvionicsDevice(
                screenWidth=SCREEN_W, screenHeight=SCREEN_H, bezelPad=BEZEL_PAD,
                draw=self.drawScreen, bezelDraw=self.drawBezel,
                deviceID=DEVICE_ID, deviceName="ImGui avionics test",
                refCon=self.state)
        except Exception as e:  # noqa: BLE001
            self.log(f"AvionicsDevice creation failed: {e!r}")
            return 1
        self.device.popup(True)
        self.log(f"device created, pop-up shown; screen {SCREEN_W}x{SCREEN_H}")
        return 1

    def XPluginDisable(self: Self) -> None:
        if self.device is not None:
            self.device.delete()
            self.device = None

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def XPluginStop(self: Self) -> None:
        # Device teardown belongs to XPluginDisable, which always runs first.
        # XPPython3 clears this module's command handlers on unload.
        xp.clearAllMenuItems(xp.findPluginsMenu())

    def commandHandler(self: Self, _cmdRef: XPLMCommandRef, phase: int, _refCon: Any) -> int:
        if phase == xp.CommandBegin and self.device is not None:
            self.device.popup(not self.device.isPopupVisible())
        return 1

    # ---- the device ----------------------------------------------------------

    def drawBezel(self: Self, _r: float, _g: float, _b: float, _refCon: Any) -> None:
        """Plain panel graphics, NOT imgui -- and only while the pop-up is visible.

        Fill the WHOLE bezel, screen area included, and fill it BLACK. The screen
        is composited OVER the bezel with alpha, so the bezel is the backdrop the
        screen blends against: leave a cut-out and you see the runway through
        anything transparent, and a light bezel washes out dark screen content.
        """
        w = SCREEN_W + 2 * BEZEL_PAD
        h = SCREEN_H + 2 * BEZEL_PAD
        xp.polygon(xp.makeColor(0, 0, 0, 1), [(0, 0), (w, 0), (w, h), (0, h)])

    def drawScreen(self: Self, _avionicsID: Any, refCon: Any) -> None:
        """ImGui, drawn into the device screen. Same widget set as PI_ImguiBoth."""
        refCon['frames'] += 1

        imgui.text_colored(text="^ TOP-LEFT  [avionics device]", r=1.0, g=0.8, b=0.0, a=1.0)
        imgui.text(f"frame {refCon['frames']}")
        imgui.separator()

        if imgui.button(f"Pressed {refCon['buttonPresses']} times"):
            refCon['buttonPresses'] += 1

        _changed, refCon['text'] = imgui.input_text("Text input", refCon['text'], 50)
        _changed, refCon['slider'] = imgui.slider_float("Slider", refCon['slider'], 0.0, 10.0)
        _changed, refCon['checkbox'] = imgui.checkbox(label="Checkbox", state=refCon['checkbox'])

        imgui.separator()
        imgui.text("colour order: red green blue")
        drawList = imgui.get_window_draw_list()
        px, py = imgui.get_cursor_screen_position()
        barH, barW = 24, 120
        for i, colour in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
            drawList.add_rect_filled(px + i * (barW + 6), py,
                                     px + i * (barW + 6) + barW, py + barH,
                                     imgui.get_color_u32_rgba(*colour, 1.0))
        imgui.dummy(0, barH + 6)

        imgui.separator()
        imgui.text("scroll me (needs io.mouse_wheel, new for this host):")
        imgui.begin_child("scroll", 0, 160, border=True)
        for i in range(60):
            imgui.text(f"row {i:02d} " + "-" * (i % 20))
        imgui.end_child()

        io = imgui.get_io()
        imgui.text(f"mouse: {io.mouse_pos.x:.0f}, {io.mouse_pos.y:.0f}   "
                   f"wheel {io.mouse_wheel:.1f}   focus {'Y' if io.want_text_input else 'n'}")
