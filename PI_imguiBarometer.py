from typing import Self, Optional, Any
from XPPython3 import xp
from XPPython3 import xp_imgui
from XPPython3.xp_typing import XPLMCommandRef, XPLMDataRef, XPLMFlightLoopID
import os
import imgui


# Simple imgui demo
# 1) Create command and attach it to 'IMGUI Barometer" menu item
# 2) On menu item selection, create new IMGUI window with slider widget
#    showing current barometer setting.

class PythonInterface:
    def __init__(self: Self) -> None:
        self.imgui_window: Optional[dict] = None
        self.cmd: Optional[XPLMCommandRef] = None
        self.cmdRef = None
        self.current_barometer: float = 0.0  # This will hold the value retreived from the dataref
        self.manually_changed = False  # flag tells us user has changes Barometer from GUI
        self.barometer_dataRef: Optional[XPLMDataRef] = None
        self.flight_loop: Optional[XPLMFlightLoopID] = None

    def XPluginStart(self: Self) -> tuple[str, str, str]:
        # Create command and attach to Menu, to create a new IMGUI window
        self.cmd = xp.createCommand(f"xpppython3/{os.path.basename(__file__)}/createWindow", "Create IMGUI window")
        xp.registerCommandHandler(self.cmd, self.commandHandler, 1, self.cmdRef)
        xp.appendMenuItemWithCommand(xp.findPluginsMenu(), 'IMGUI Barometer', self.cmd)

        return 'PI_imguiBarometer v1.0', 'xppython3.imgui_barometer', 'Simple IMGUI Barometer plugin'

    def XPluginEnable(self: Self):
        self.barometer_dataRef = xp.findDataRef('sim/cockpit/misc/barometer_setting')
        self.current_barometer = xp.getDataf(self.barometer_dataRef)
        self.flight_loop = xp.createFlightLoop(self.updateDataRefs)
        xp.scheduleFlightLoop(self.flight_loop, -1)
        return 1

    def updateDataRefs(self: Self, _sinceLast: float, _elapsedTime: float, _counter: int, _refcon: Any):
        if self.manually_changed:
            xp.setDataf(self.barometer_dataRef, self.current_barometer)
        self.current_barometer = xp.getDataf(self.barometer_dataRef)
        return -1

    def XPluginStop(self: Self):
        # unregister command and clean up menu
        xp.unregisterCommandHandler(self.cmd, self.commandHandler, 1, self.cmdRef)
        xp.clearAllMenuItems(xp.findPluginsMenu())

    def XPluginDisable(self: Self):
        # delete any imgui_windows, clear the structure
        if self.imgui_window:
            self.imgui_window['instance'].delete()
            del self.imgui_window

    def commandHandler(self, _cmdRef, phase, _refCon):
        if phase == xp.CommandBegin:
            if not self.imgui_window:
                self.createWindow(f'{os.path.basename(__file__)} Window')
        return 1

    def createWindow(self: Self, title: str):
        # Set my imgui_window dict with information about the new window.
        #
        # The only thing we really need is a unique reference constant, which
        # we pass into as part of initialization of the xp_imgui.Window() class
        #
        # In this example, we'll use the 'self' reference we get for free
        # due to using an instance method (drawWindow() "knows" about "self")
        # as the reference constant.

        # Determine where you want the window placed. Note these
        # windows are placed relative the global screen (composite
        # of all your monitors) rather than the single 'main' screen.
        l, t, _r, _b = xp.getScreenBoundsGlobal()
        width = 600
        height = 80
        left_offset = 110
        top_offset = 110

        # Create the imgui Window, and save it.
        self.imgui_window = {'instance': xp_imgui.Window(left=l + left_offset,
                                                         top=t - top_offset,
                                                         right=l + left_offset + width,
                                                         bottom=t - (top_offset + height),
                                                         visible=1,
                                                         draw=self.drawWindow)}

        # and (optionally) set the title of the created window using .setTitle()
        self.imgui_window['instance'].setTitle(title)
        return

    def drawWindow(self, _windowID, _refCon):
        # LABEL
        imgui.text("Barometric Setting")

        # SLIDER
        self.manually_changed, self.current_barometer = imgui.slider_float("Inches", self.current_barometer, 26.0, 32.0)
        return
