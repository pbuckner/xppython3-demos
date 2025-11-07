import traceback
import re
import sys
import io
import os
import webbrowser
import contextlib
import codeop
from XPPython3.utils import paste
from XPPython3.utils import xp_web_api
from XPPython3 import xp
from XPPython3.XPListBox import XPCreateListBox, Prop, XPListBox, xpMessage_ListBoxItemSelected
from XPPython3.xp_typing import XPWidgetID, XPLMCommandRef
from typing import Any, Self, Tuple, List

# Change log
# v2.3 * Fixed resizing of the popped-out window, to make sure it will correctly get docked
#        in the future.
#      * Changed lookup of datarefs to use X-Plane 12.1 dataref feature.
#      * added lookup of X-Plane Commands
#      * added 'copy-to-clipboard' on selection (you still need to paste it into text buffer, if you like.)
# v2.2 * Corrected placing history into history buffer
#      * Fixed 'previous' command display to correctly get the next entry (previously, first
#        'previous' invocation returned empty command.
#      * improved type hinting
# v2.1 * Fixed scroll position of textWidget: on long input, we didn't reset left-most scroll position
#      * Automatically store and restore 'history'... To maintain sanity, maximum lines restored is Max_History
#      * Also, on input, we _always_ scroll to the bottom (you can scroll up, but as input is added, we'll
#        scroll back to the bottom.

Max_History = 20  # read in this number of (unique) previous command history on startup.
History_Filename = 'minipython_history.txt'


class IncompleteError(Exception):
    pass


class PythonInterface:
    def __init__(self: Self):
        self.historyIdx = -1
        self.partialCommand: List[str] = []
        self.prevCommands: List[str] = []
        self.widget1: XPWidgetID = None
        self.textWidget: XPWidgetID = None
        self.doButton: XPWidgetID = None
        self.helpButton: XPWidgetID = None
        self.popOutButton: XPWidgetID = None
        self.listboxWidget: XPListBox = None
        self.toggleCommandRef: XPLMCommandRef = None
        self.menuIdx: int = None
        self.popout = False

    def XPluginStart(self: Self) -> Tuple[str, str, str]:
        self.toggleCommandRef = xp.createCommand('xppython3/mini-python/toggle', 'Toggle Mini-Python window')
        xp.registerCommandHandler(self.toggleCommandRef, self.toggleCommand, 1, None)
        self.menuIdx = xp.appendMenuItemWithCommand(xp.findPluginsMenu(), 'Mini Python', self.toggleCommandRef)
        self.loadPrevCommands()
        self.prevCommands.append('>>> ')
        return ('Mini Python Interpreter v2.1',
                'xppython3.minipython',
                'For debugging / testing: provides a mini python interpreter')

    def resizePopup(self: Self) -> None:
        # resizes to fit
        (windowLeft, windowTop, windowRight, windowBottom) = xp.getWidgetGeometry(self.widget1)

        #
        # list box
        position = self.getPosition('listbox', windowLeft, windowTop, windowRight, windowBottom)
        xp.setWidgetGeometry(self.listboxWidget.widgetID,
                             position[0], position[1], position[2], position[3])
        _fontWidth, fontHeight, _other = xp.getFontDimensions(xp.Font_Basic)
        listbox_item_height = int(fontHeight * 1.2)
        numVisible = int((position[1] - position[3]) / (listbox_item_height))
        xp.setWidgetProperty(self.listboxWidget.widgetID, Prop.ListBoxMaxListBoxItems, numVisible)

        #
        # text box
        (left, top, _right, bottom) = xp.getWidgetGeometry(self.textWidget)
        position = self.getPosition('textbox', windowLeft, windowTop, windowRight, windowBottom)
        xp.setWidgetGeometry(self.textWidget, position[0], position[1], position[2], position[3])
        (left, top, _right, bottom) = xp.getWidgetGeometry(self.textWidget)

        #
        # buttons
        position = self.getPosition('do_button', windowLeft, windowTop, windowRight, windowBottom)
        xp.setWidgetGeometry(self.doButton, position[0], position[1], position[2], position[3])
        position = self.getPosition('help_button', windowLeft, windowTop, windowRight, windowBottom)
        xp.setWidgetGeometry(self.helpButton, position[0], position[1], position[2], position[3])
        position = self.getPosition('pop_button', windowLeft, windowTop, windowRight, windowBottom)
        xp.setWidgetGeometry(self.popOutButton, position[0], position[1], position[2], position[3])

        # we don't bother to resize the help text -- it's tedious to either save all of the child widgets
        # (which we don't do), or interate through getNthChildWidget() in order to find & them move
        # them all correctly. There's probably a somewhat clever solution to this, but I'm not going
        # to bother with it.

    def getPosition(self: Self, name: str, left: int, top: int, right: int, bottom: int) -> List[int]:
        windowMarginLeft = 10
        windowMarginTop = 25
        bottomBuffer = 95
        scrollBarWidth = 20
        _width, height, _ignored = xp.getFontDimensions(xp.Font_Basic)
        if name == 'listbox':
            wleft = left + windowMarginLeft
            wtop = top - windowMarginTop
            wright = right
            wbottom = bottom + bottomBuffer - windowMarginTop
        elif name == 'textbox':
            wleft = left + windowMarginLeft
            wtop = bottom + bottomBuffer - 25
            wright = right - scrollBarWidth
            wbottom = bottom + bottomBuffer - windowMarginTop - 20
        elif name == 'do_button':
            wleft = left + windowMarginLeft
            wtop = bottom + bottomBuffer - 25 - 40
            wright = wleft + 40
            wbottom = wtop - 20
        elif name == 'help_button':
            wleft = right - scrollBarWidth - 40
            wtop = bottom + bottomBuffer - 25 - 20
            wright = right - scrollBarWidth
            wbottom = wtop - 20
        elif name == 'pop_button':
            wleft = right - scrollBarWidth - 40
            wtop = bottom + bottomBuffer - 25 - 20 - 20
            wright = right - scrollBarWidth
            wbottom = wtop - 20
        elif name == 'help_col1':
            wleft = left + 60
            wtop = bottom + bottomBuffer - 25 - 20
            wright = left + 100
            wbottom = wtop - height
        elif name == 'help_col2':
            wleft = left + 220
            wtop = bottom + bottomBuffer - 25 - 20
            wright = wleft + 100
            wbottom = wtop - height
        elif name == 'help_col3':
            wleft = left + 350
            wtop = bottom + bottomBuffer - 25 - 20
            wright = wleft + 100
            wbottom = wtop - height
        else:
            return [0, 100, 100, 0]

        return [wleft, wtop, wright, wbottom]

    def createPopup(self: Self,
                    windowLeft: int = 100, windowTop: int = 500, windowRight: int = 700, windowBottom: int = 110,
                    popout: bool = False) -> None:
        _width, height, _ignored = xp.getFontDimensions(xp.Font_Basic)
        self.widget1 = xp.createWidget(windowLeft, windowTop, windowRight, windowBottom, 0,
                                       "Mini Python Interpreter", 1, 0, xp.WidgetClass_MainWindow)
        xp.setWidgetProperty(self.widget1, xp.Property_MainWindowHasCloseBoxes, 1)

        xp.addWidgetCallback(self.widget1, self.widgetMsgs)

        (left, top, right, bottom) = xp.getScreenBoundsGlobal()
        xp.setWindowResizingLimits(xp.getWidgetUnderlyingWindow(self.widget1),
                                   minWidth=460, minHeight=150,
                                   maxWidth=right - left - 50, maxHeight=top - bottom - 50)
        self.popout = popout

        #
        # list box
        position = self.getPosition('listbox', windowLeft, windowTop, windowRight, windowBottom)
        self.listboxWidget = XPCreateListBox(position[0], position[1], position[2], position[3], 1, self.widget1)

        #
        # text box
        position = self.getPosition('textbox', windowLeft, windowTop, windowRight, windowBottom)
        self.textWidget = xp.createWidget(position[0], position[1], position[2], position[3],
                                          1, self.prevCommands[-1], 0, self.widget1, xp.WidgetClass_TextField)
        xp.addWidgetCallback(self.textWidget, self.textEdit)

        #
        # buttons
        position = self.getPosition('do_button', windowLeft, windowTop, windowRight, windowBottom)
        self.doButton = xp.createWidget(position[0], position[1], position[2], position[3],
                                        1, "Do", 0, self.widget1, xp.WidgetClass_Button)
        xp.setWidgetProperty(self.doButton, xp.Property_ButtonType, xp.PushButton)
        xp.setWidgetProperty(self.doButton, xp.Property_ButtonBehavior, xp.ButtonBehaviorPushButton)

        position = self.getPosition('help_button', windowLeft, windowTop, windowRight, windowBottom)
        self.helpButton = xp.createWidget(position[0], position[1], position[2], position[3],
                                          1, "Help", 0, self.widget1, xp.WidgetClass_Button)
        xp.setWidgetProperty(self.helpButton, xp.Property_ButtonType, xp.PushButton)
        xp.setWidgetProperty(self.helpButton, xp.Property_ButtonBehavior, xp.ButtonBehaviorPushButton)

        position = self.getPosition('pop_button', windowLeft, windowTop, windowRight, windowBottom)
        self.popOutButton = xp.createWidget(position[0], position[1], position[2], position[3],
                                            1, "Pop ➚", 0, self.widget1, xp.WidgetClass_Button)
        if self.popout:
            xp.setWidgetDescriptor(self.popOutButton, "Dock ↙︎")
        xp.setWidgetProperty(self.popOutButton, xp.Property_ButtonType, xp.PushButton)
        xp.setWidgetProperty(self.popOutButton, xp.Property_ButtonBehavior, xp.ButtonBehaviorPushButton)

        #
        # help text
        position = self.getPosition('help_col1', windowLeft, windowTop, windowRight, windowBottom)
        xp.createWidget(position[0], position[1], position[2], position[3],
                        1, '^A ^E: Start / End of line', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(position[0], position[1] - (height + 4), position[2], position[3] - (height + 4),
                        1, '^N ^P: Next / Previous line', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(position[0], position[1] - 2 * (height + 4), position[2], position[3] - 2 * (height + 4),
                        1, '^F ^B: Move Forward / Back', 0, self.widget1, xp.WidgetClass_Caption)

        position = self.getPosition('help_col2', windowLeft, windowTop, windowRight, windowBottom)
        xp.createWidget(position[0], position[1], position[2], position[3],
                        1, '^D: Delete char', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(position[0], position[1] - (height + 4), position[2], position[3] - (height + 4),
                        1, '^K: Kill to EOL', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(position[0], position[1] - 2 * (height + 4), position[2], position[3] - 2 * (height + 4),
                        1, '^V: Paste from CB', 0, self.widget1, xp.WidgetClass_Caption)

        position = self.getPosition('help_col3', windowLeft, windowTop, windowRight, windowBottom)
        xp.createWidget(position[0], position[1], position[2], position[3],
                        1, '^R ^Q: Reload / Quit X-Plane', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(position[0], position[1] - (height + 4), position[2], position[3] - (height + 4),
                        1, '/<phrase>: Search SDK', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(position[0], position[1] - 2 * (height + 4), position[2], position[3] - 2 * (height + 4),
                        1, '<Return>: Execute line', 0, self.widget1, xp.WidgetClass_Caption)

    def textEdit(self: Self, message: int, widgetID: XPWidgetID, param1: Any, _param2: Any) -> int:
        if widgetID != self.textWidget:
            xp.log(f"got textEdit callback but not for correct widget: {widgetID}")
            return 0
        # Normally, most key presses (of printable keys) is handled by the TextField widget
        # Here, we want to intercept the keypress _first_
        if message == xp.Msg_KeyPress and not param1[1] & xp.UpFlag:
            ignoreFirst = 4
            if param1[1] & xp.ControlFlag:
                if param1[2] == xp.VK_K:
                    start = xp.getWidgetProperty(widgetID, xp.Property_EditFieldSelStart, None)
                    xp.setWidgetDescriptor(widgetID, xp.getWidgetDescriptor(widgetID)[0:start])
                    return 1
                elif param1[2] == xp.VK_F:
                    numChars = len(xp.getWidgetDescriptor(widgetID))
                    start = min(numChars, xp.getWidgetProperty(widgetID, xp.Property_EditFieldSelStart, None) + 1)
                    xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, start)
                    xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, start)
                    return 1
                elif param1[2] == xp.VK_A:
                    xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, ignoreFirst)
                    xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, ignoreFirst)
                    return 1
                elif param1[2] == xp.VK_E:
                    numChars = len(xp.getWidgetDescriptor(widgetID))
                    xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, numChars)
                    xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, numChars)
                    return 1
                elif param1[2] == xp.VK_V:
                    self.paste()
                    return 1
                elif param1[2] == xp.VK_Q:
                    xp.commandOnce(xp.findCommand('sim/operation/quit'))
                    return 1
                elif param1[2] == xp.VK_R:
                    xp.commandOnce(xp.findCommand('XPPython3/reloadScripts'))
                    return 1

            if param1[2] == xp.VK_DELETE or (param1[2] == xp.VK_D and param1[1] & xp.ControlFlag):
                start = xp.getWidgetProperty(widgetID, xp.Property_EditFieldSelStart, None)
                text = xp.getWidgetDescriptor(widgetID)
                xp.setWidgetDescriptor(widgetID, text[0:start] + text[start + 1:])
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, start)
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, start)
                return 1

            if param1[2] == xp.VK_BACK:
                if ignoreFirst == xp.getWidgetProperty(widgetID, xp.Property_EditFieldSelStart, None):
                    return 1
                start = max(ignoreFirst, xp.getWidgetProperty(widgetID, xp.Property_EditFieldSelStart, None) - 1)
                text = xp.getWidgetDescriptor(widgetID)
                xp.setWidgetDescriptor(widgetID, text[0:start] + text[start + 1:])
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, start)
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, start)
                return 1

            if param1[2] == xp.VK_LEFT or (param1[2] == xp.VK_B and param1[1] & xp.ControlFlag):
                start = max(ignoreFirst, xp.getWidgetProperty(widgetID, xp.Property_EditFieldSelStart, None) - 1)
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, start)
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, start)
                return 1

            if param1[2] == xp.VK_DOWN or (param1[2] == xp.VK_N and param1[1] & xp.ControlFlag):
                self.historyIdx = (self.historyIdx + 1) % len(self.prevCommands)
                xp.setWidgetDescriptor(widgetID, self.prevCommands[self.historyIdx])
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, len(xp.getWidgetDescriptor(widgetID)))
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, len(xp.getWidgetDescriptor(widgetID)))
                return 1
            if param1[2] == xp.VK_UP or (param1[2] == xp.VK_P and param1[1] & xp.ControlFlag):
                self.historyIdx = (self.historyIdx - 1) % len(self.prevCommands)
                xp.setWidgetDescriptor(widgetID, self.prevCommands[self.historyIdx])
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, len(xp.getWidgetDescriptor(widgetID)))
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, len(xp.getWidgetDescriptor(widgetID)))
                return 1
        return 0

    def widgetMsgs(self: Self, message: int, widgetID: XPWidgetID, param1: Any, param2: Any) -> int:
        if widgetID != self.widget1:
            xp.log(f"got widgetMsg callback but not for correct widget: {widgetID}")
            return 0
        if message == xp.Msg_Reshape:
            # -- regenerate widgets and repopulate with data...
            if param2[2] != 0 or param2[3] != 0:
                self.resizePopup()
                return 1

        if message == xp.Message_CloseButtonPushed:
            xp.hideWidget(self.widget1)
            return 1

        if message == xp.Msg_PushButtonPressed and param1 == self.popOutButton:
            win = xp.getWidgetUnderlyingWindow(self.widget1)
            if self.popout:
                xp.setWindowPositioningMode(win, xp.WindowPositionFree, 1)
                (left, top, right, bottom) = xp.getWindowGeometry(win)
                (s_left, s_top, s_right, s_bottom) = xp.getScreenBoundsGlobal()
                change = False
                if left < s_left:
                    change = True
                    right = min(right + s_left - left, s_right - 5)
                    left = s_left
                if right > s_right:
                    change = True
                    left = max(s_left + 5, left - right - s_right)
                    right = s_right
                if top > s_top:
                    change = True
                    bottom = max(s_bottom + 5, bottom - top - s_top)
                    top = s_top - 5
                if bottom < s_bottom:
                    change = True
                    top = min(top + s_bottom - bottom, s_top - 5)
                    bottom = s_bottom
                if change:
                    xp.setWindowGeometry(win, left, top, right, bottom)
                xp.setWidgetDescriptor(self.popOutButton, "Pop ➚")
            else:
                xp.setWindowPositioningMode(win, xp.WindowPopOut, 1)
                xp.setWidgetDescriptor(self.popOutButton, "Dock ↙︎")
            self.popout = not self.popout
            return 1

        if message == xp.Msg_PushButtonPressed and param1 == self.helpButton:
            webbrowser.open('https://xppython3.rtfd.io/en/latest/development/index.html')
            return 1

        execute = False
        if message == xp.Msg_PushButtonPressed and param1 == self.doButton:
            execute = True
        if not execute:
            if message == xp.Msg_KeyPress:
                if param1[2] == xp.VK_RETURN and param1[1] & xp.DownFlag:
                    execute = True
        if message == xpMessage_ListBoxItemSelected:
            command = xp.getWidgetDescriptor(self.listboxWidget.widgetID)[4:]
            paste.putClipboard(command)

        if execute:
            # See if we need to scroll to the bottom
            position = xp.getWidgetProperty(self.listboxWidget.widgetID, Prop.ListBoxScrollBarSliderPosition)
            max_items = xp.getWidgetProperty(self.listboxWidget.widgetID, Prop.ListBoxMaxListBoxItems)
            if position >= max_items:
                # Yes, scroll to the bottom
                xp.setWidgetProperty(self.listboxWidget.widgetID, Prop.ListBoxScrollBarSliderPosition, max_items - 1)
            try:
                self.try_execute(xp.getWidgetDescriptor(self.textWidget))
            except SystemExit:
                xp.hideWidget(self.widget1)
            except Exception as e:  # pylint: disable=broad-except
                xp.log(f"Caught other exception in widget messages, after try_execute: {e}")
                xp.log()
            return 1
        return 0

    def toggleCommand(self: Self, _commandRef: XPLMCommandRef, phase: int, _refCon: Any) -> int:
        if phase != xp.CommandEnd or not self.widget1:
            return 0

        win = xp.getWidgetUnderlyingWindow(self.widget1)
        if xp.isWidgetVisible(self.widget1) and xp.getWindowIsVisible(win):
            xp.hideWidget(self.widget1)
        else:
            xp.showWidget(self.widget1)
            xp.setWindowIsVisible(win, 1)
            if self.popout:
                xp.setWindowPositioningMode(win, xp.WindowPopOut, 1)
            xp.bringWindowToFront(win)
            xp.setKeyboardFocus(self.textWidget)
            xp.setWidgetProperty(self.textWidget, xp.Property_EditFieldSelStart, 4)
            xp.setWidgetProperty(self.textWidget, xp.Property_EditFieldSelEnd, 4)

        return 1

    def XPluginEnable(self: Self) -> int:
        # initialize with leading blank lines -- this puts the "next" input at the very
        # bottom of the window. This mimics scrolling input better.
        self.createPopup(50, 500, 650, 110, popout=False)
        num_added = 0
        for line in self.prevCommands[0:-1]:
            if line != '>>> ':
                num_added += 1
                self.listboxWidget.add(line)

        num_blank_lines = xp.getWidgetProperty(self.listboxWidget.widgetID,
                                               Prop.ListBoxMaxListBoxItems, None)
        num_blank_lines -= 2 + num_added

        for _i in range(num_blank_lines):
            self.listboxWidget.add('')

        return 1

    def XPluginDisable(self: Self) -> None:
        if self.widget1:
            xp.destroyWidget(self.widget1, 1)
            self.widget1 = None

        if self.listboxWidget is not None:
            self.listboxWidget.destroy()
            self.listboxWidget = None

    def XPluginStop(self: Self) -> None:
        if self.prevCommands:
            # Write command history to file
            filename = os.path.join(os.path.dirname(xp.getPrefsPath()), History_Filename)
            with open(filename, 'w', encoding='utf-8') as fp:
                for i in self.prevCommands:
                    fp.write(i + '\n')

        if self.toggleCommandRef:
            xp.unregisterCommandHandler(self.toggleCommandRef,
                                        self.toggleCommand,
                                        1, None)
            self.toggleCommandRef = None
        if self.menuIdx:
            xp.removeMenuItem(xp.findPluginsMenu(), self.menuIdx)
            self.menuIdx = None

    def try_execute(self: Self, s: str) -> None:
        xp.setWidgetProperty(self.textWidget, xp.Property_ScrollPosition, 0)  # reset left-most in text widget
        if s.startswith('>>> /'):
            self.listboxWidget.add(s)
            items = [x for x in dir(xp) if re.search(s[5:], x, flags=re.IGNORECASE)]
            sorted(items)
            for i in items:
                self.listboxWidget.add(i)
            xp.setWidgetDescriptor(self.textWidget, '>>> ')
            return
        elif s.startswith('>>> ?'):
            self.listboxWidget.add(s)
            datarefs = xp.getDataRefsByIndex(count=xp.countDataRefs())
            items = [xp.getDataRefInfo(d).name for d in datarefs]
            items = [x for x in items if re.search(s[5:].strip(), x, flags=re.IGNORECASE)]

            sorted(items)
            for i in items:
                self.listboxWidget.add(i)
            xp.setWidgetDescriptor(self.textWidget, '>>> ')
            return
        elif s.startswith('>>> :'):
            self.listboxWidget.queue.put("[searching commands]")
            xp_web_api.getCommands(self.listboxWidget.queue, s[5:].strip())
            xp.setWidgetDescriptor(self.textWidget, '>>> ')
            return

        self.prevCommands.append(s)
        self.historyIdx = -1
        try:
            self.partialCommand.append(self.prevCommands[self.historyIdx][4:])
            self.listboxWidget.add(s)
            if codeop.compile_command('\n'.join(self.partialCommand), symbol='single'):
                if (s.startswith('...') or s.startswith('    ')) and (s != '... ' and s != '    '):
                    xp.setWidgetDescriptor(self.textWidget, '... ')
                else:
                    if len(self.partialCommand) == 1 and self.partialCommand[0] == '':
                        self.partialCommand = []
                        return
                    self.do('\n'.join(self.partialCommand))
                    xp.setWidgetDescriptor(self.textWidget, '>>> ')
                    self.partialCommand = []
            else:
                xp.setWidgetDescriptor(self.textWidget, '... ')
        except IncompleteError:
            pass
        except Exception as e:  # pylint: disable=broad-except
            if isinstance(e, SystemExit):
                raise e
            # do it anyway -- this captures the exception output and
            # adds it to the window
            try:
                self.do('\n'.join(self.partialCommand))
            except Exception:  # pylint: disable=broad-except
                pass
            xp.setWidgetDescriptor(self.textWidget, '>>> ')
            self.partialCommand = []
        self.historyIdx = 0

    def do(self: Self, s: str) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        num_lines = len(s.split('\n'))
        if s.strip().startswith('#'):
            return
        if s == '':
            self.listboxWidget.add('>>> ')
            return

        with contextlib.redirect_stderr(stderr):
            with contextlib.redirect_stdout(stdout):
                print(f">>> {s}")
                try:
                    exec(compile(s, '<string>', 'single'), globals())  # pylint: disable=exec-used
                except Exception as e:  # pylint: disable=broad-except
                    if isinstance(e, SystemExit):
                        raise e
                    e_type, value, tb = sys.exc_info()
                    traceback.print_exception(e_type, value, tb)

        s = stdout.getvalue().strip()
        if s:
            # print stdout, but SKIP the length of the incoming commands. (we already display them)
            for line in s.split('\n')[(num_lines):]:
                self.listboxWidget.add(line)
        s = stderr.getvalue().strip()
        if s:
            for line in s.split('\n'):
                self.listboxWidget.add(line)

    def paste(self: Self) -> None:
        if sys.version_info.minor >= 7:
            lines = paste.getClipboard()
            # 'removePrefix' allows us work with pasted code which, itself includes '>>> '. e.g.:
            #    >>> def log(s):
            #    ...   print("f{s}")
            #    ...
            #  will work exactly the same as:
            #    def log(s):
            #      print("f{s}")
            # This makes it easier to cut and paste from python documentation examples
            removePrefix = lines and (lines[0].startswith('>>> ') or lines[0].startswith('... '))
            for idx, line in enumerate(lines):
                line = line[4:] if removePrefix else line
                if idx == 0:
                    # For first pasted line, get current text box content, and merge
                    # pasted line with content.
                    currentText = xp.getWidgetDescriptor(self.textWidget)
                    selStart = xp.getWidgetProperty(self.textWidget, xp.Property_EditFieldSelStart, None)
                    selEnd = xp.getWidgetProperty(self.textWidget, xp.Property_EditFieldSelEnd, None)
                    currentText = currentText[:selStart] + line + currentText[selEnd:]
                    xp.setWidgetProperty(self.textWidget, xp.Property_EditFieldSelStart, selStart + len(line))
                    xp.setWidgetProperty(self.textWidget, xp.Property_EditFieldSelEnd, selStart + len(line))
                    xp.setWidgetDescriptor(self.textWidget, currentText.split('\n')[-1])
                    continue
                # if there is existing code in textWidget, execute it first.
                if len(xp.getWidgetDescriptor(self.textWidget)) > 4:
                    self.try_execute(xp.getWidgetDescriptor(self.textWidget))
                # On paste, we may get a blank line, say between lines of code,
                # which should not terminate code / function def, so
                # IF we see a fully blank line and it's not the last line of paste
                # we add same number of blanks from the _next_ line
                # (this will fail if you try to paste two blank lines in a row, within
                # a control block... so don't.)
                if line == '' and idx != len(lines) - 1:
                    next_line = lines[idx + 1][4:] if removePrefix else lines[idx + 1]
                    line = ' ' * (len(next_line) - len(next_line.lstrip()))
                if line == '':
                    if not self.partialCommand:
                        continue

                self.try_execute(('... ' if self.partialCommand else '>>> ') + line)
        else:
            xp.log("Paste supported Python 3.7+")

    def loadPrevCommands(self: Self) -> None:
        self.prevCommands = []
        try:
            filename = os.path.join(os.path.dirname(xp.getPrefsPath()), History_Filename)
            with open(filename, 'r', encoding='utf-8') as fp:
                for line in fp.readlines():
                    if line.startswith('>>> exit()') or line == '>>> \n':
                        continue
                    # comment out.... Actually, it's best to store all commands, not just "unique", at least until
                    # we can Search back previous commands...
                    # if line[0:-1] not in self.prevCommands:
                    self.prevCommands.append(line[0:-1])
            self.prevCommands = self.prevCommands[-Max_History:]
        except OSError:
            pass
