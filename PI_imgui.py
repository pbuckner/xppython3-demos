import os
import traceback
from XPPython3 import xp
from XPPython3 import xp_imgui
from XPPython3 import imgui


# Simple imgui demo
# 1) Create command and attach it to 'IMGUI Window" menu item
# 2) On menu item selection, create new IMGUI window with a few standard imgui widgets
#    imgui code is executed during new window's draw() callback.
# We don't actually do much with the window's data other than
# store it (per-window) in a data-structure associated with the window's
# reference constant. Presumably, you'd be working with datarefs or other
# storage in a "real" plugin.

class PythonInterface:
    def __init__(self):
        self.windowNumber = 0  # Number we increment, just to "know" which window I've just created
        self.imgui_windows = {}  # {'xp_imgui.Window' instances}
        self.cmd = None
        self.cmdRef = []

    def XPluginStart(self):
        # Create command and attach to Menu, to create a new IMGUI window
        self.cmd = xp.createCommand("xpppython3/{}/createWindow".format(os.path.basename(__file__)), "Create IMGUI window")
        xp.registerCommandHandler(self.cmd, self.commandHandler, 1, self.cmdRef)
        xp.appendMenuItemWithCommand(xp.findPluginsMenu(), 'IMGUI Window', self.cmd)

        return os.path.basename(__file__), 'xppython3.imgui_test', 'Simple IMGUI test plugin'

    def XPluginEnable(self):
        return 1

    def XPluginStop(self):
        # unregister command and clean up menu
        xp.unregisterCommandHandler(self.cmd, self.commandHandler, 1, self.cmdRef)
        xp.clearAllMenuItems(xp.findPluginsMenu())

    def XPluginReceiveMessage(self, *args, **kwargs):
        pass

    def XPluginDisable(self):
        # delete any imgui_windows, clear the structure
        for x in list(self.imgui_windows):
            self.imgui_windows[x]['instance'].delete()
            del self.imgui_windows[x]

    def commandHandler(self, cmdRef, phase, refCon):
        if phase == xp.CommandBegin:
            # For fun, we'll create a NEW window each time the command is invoked.
            self.createWindow('{} Window #{}'.format(os.path.basename(__file__), self.windowNumber))
            self.windowNumber += 1
        return 1

    def createWindow(self, title):
        # Update my imgui_windows dict with information about the new window, including (for
        # demo purposes) stored values of the various widgets.
        #
        # The only thing we really need is a unique reference constant, which
        # we pass into as part of initialization of the xp_imgui.Window() class
        #
        # In this example, we'll use this local data as the reference constant.
        self.imgui_windows[title] = {'instance': None,
                                     'title': title,
                                     'numButtonPressed': 0,
                                     'checkbox1': False,
                                     'checkbox2': True,
                                     'radio': 1,
                                     'slider': 4.75,
                                     'text': 'type here'}

        # Determine where you want the window placed. Note these
        # windows are placed relative the global screen (composite
        # of all your monitors) rather than the single 'main' screen.
        l, t, r, b = xp.getScreenBoundsGlobal()
        width = 600
        height = 600
        left_offset = 110
        top_offset = 110

        pok = [l + left_offset, t - top_offset, l + left_offset + width, t - (top_offset + height), 1,
               self.drawWindow, self.handleMouseClick, self.handleKey,
               self.handleCursor, self.handleMouseWheel,
               self.imgui_windows[title],  # reference constant
               xp.WindowDecorationRoundRectangle, xp.WindowLayerFloatingWindows,
               self.handleRightClick]

        self.imgui_windows[title].update({'instance': xp_imgui.Window(pok)})

        # and (optionally) set the title of the created window using .setTitle()
        self.imgui_windows[title]['instance'].setTitle(title)
        return

    def drawWindow(self, inWindowID, inRefCon):
        try:
            # LABEL
            imgui.text("Simple Label")

            # COLORED LABEL
            imgui.text_colored(text="Colored Label", r=1.0, g=0.0, b=0.0, a=1.0)

            # BUTTON
            if imgui.button("Button Pressed #{} times".format(inRefCon['numButtonPressed'])):
                # every time it's pressed, we increment it's label.
                inRefCon['numButtonPressed'] += 1

            # TEXT INPUT
            changed, inRefCon['text'] = imgui.input_text("Text Input", inRefCon['text'], 50)

            # CHECKBOX
            changed, inRefCon['checkbox1'] = imgui.checkbox(label="Check 1", state=inRefCon['checkbox1'])
            changed, inRefCon['checkbox2'] = imgui.checkbox(label="Check 2", state=inRefCon['checkbox2'])

            # RADIO
            if imgui.radio_button("A", inRefCon['radio'] == 0):
                inRefCon['radio'] = 0
            imgui.same_line()
            if imgui.radio_button("B", inRefCon['radio'] == 1):
                inRefCon['radio'] = 1
            imgui.same_line()
            if imgui.radio_button("C", inRefCon['radio'] == 2):
                inRefCon['radio'] = 2

            # SLIDER
            changed, inRefCon['slider'] = imgui.slider_float("Slider", inRefCon['slider'], 0.0, 10.0)

        except Exception:
            xp.log('{}\n{}'.format('Error within drawWindow', traceback.format_exc()))
        return

    def handleMouseClick(self, inWindowID, x, y, inMouse, inRefCon):
        return 1

    def handleRightClick(self, inWindowID, x, y, inMouse, inRefCon):
        return 1

    def handleCursor(self, inWindowID, x, y, inRefCon):
        return xp.CursorDefault

    def handleMouseWheel(self, inWindowID, x, y, wheel, clicks, inRefCon):
        return 1

    def handleKey(self, inWindowID, inKey, inFlags, inVirtualKey, inRefCon, losingFocus):
        return
