import traceback
import re
import sys
import io
import os
import webbrowser
import contextlib
import codeop
from XPPython3.utils import paste
from XPPython3 import xp
from XPPython3.XPListBox import XPCreateListBox, Prop

# Change log
# v2.1 * Fixed scroll position of textWidget: on long input, we didn't reset left-most scroll position
#      * Automatically store and restore 'history'... To maintain sanity, maximum lines restored is Max_History
#      * Also, on input, we _always_ scroll to the bottom (you can scroll up, but as input is added, we'll
#        scroll back to the bottom.

Max_History = 20  # read in this number of (unique) previous command history on startup.
History_Filename = 'minipython_history.txt'


class IncompleteError(Exception):
    pass


class PythonInterface:
    def __init__(self):
        self.historyIdx = -1
        self.partialCommand = []
        self.prevCommands = None
        self.widget1 = None
        self.textWidget = None
        self.doButton = None
        self.helpButton = None
        self.popOutButton = None
        self.listboxWidget = None
        self.toggleCommandRef = None
        self.menuIdx = None
        self.popout = False

    def XPluginStart(self):
        self.toggleCommandRef = xp.createCommand('xppython3/mini-python/toggle', 'Toggle Mini-Python window')
        xp.registerCommandHandler(self.toggleCommandRef, self.toggleCommand, 1, None)
        self.menuIdx = xp.appendMenuItemWithCommand(xp.findPluginsMenu(), 'Mini Python', self.toggleCommandRef)
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
                    #     self.prevCommands.append(line[0:-1])
            self.prevCommands = self.prevCommands[-Max_History:]
        except OSError:
            pass
        self.prevCommands.append('>>> ')
        return ('Mini Python Interpreter v2.1',
                'xppython3.minipython',
                'For debugging / testing: provides a mini python interpreter')

    def resizePopup(self):
        # resizes to fit
        win = xp.getWidgetUnderlyingWindow(self.widget1)
        if xp.windowIsPoppedOut(win):
            (leftWin, topWin, rightWin, bottomWin) = xp.getWindowGeometryOS(win)
        elif xp.windowIsInVR(win):
            (widthWin, heightWin) = xp.getWindowGeometryVR(win)
            (leftWin, topWin, rightWin, bottomWin) = (0, heightWin, widthWin, 0)
        else:
            (leftWin, topWin, rightWin, bottomWin) = xp.getWindowGeometry(win)

        (listLeft, _listTop, _listRight, listBottom) = xp.getWidgetGeometry(self.listboxWidget.widgetID)

        newLeft = listLeft
        newTop = listBottom + topWin - bottomWin - 100
        newRight = listLeft + rightWin - leftWin - 10
        newBottom = listBottom

        xp.setWidgetGeometry(self.listboxWidget.widgetID, newLeft, newTop, newRight, newBottom)
        _fontWidth, fontHeight, _other = xp.getFontDimensions(xp.Font_Basic)
        listbox_item_height = int(fontHeight * 1.2)
        numVisible = int((newTop - newBottom) / listbox_item_height)

        xp.setWidgetProperty(self.listboxWidget.widgetID, Prop.ListBoxMaxListBoxItems, numVisible)

        (left, top, _right, bottom) = xp.getWidgetGeometry(self.textWidget)
        xp.setWidgetGeometry(self.textWidget, left, top, newRight - 20, bottom)

    def createPopup(self, windowLeft=100, windowTop=500, windowWidth=600, windowHeight=390, popout=False):
        _width, height, _ignored = xp.getFontDimensions(xp.Font_Basic)
        self.widget1 = xp.createWidget(windowLeft, windowTop, windowLeft + windowWidth, windowTop - windowHeight, 0,
                                       "Mini Python Interpreter", 1, 0, xp.WidgetClass_MainWindow)
        self.popout = popout
        row = windowTop - 25
        self.listboxWidget = XPCreateListBox(windowLeft + 10,
                                             row,
                                             windowLeft + windowWidth,
                                             row - 295,
                                             1, self.widget1)

        row = row - 295
        self.textWidget = xp.createWidget(windowLeft + 10,
                                          row,
                                          windowLeft + windowWidth - 20,
                                          row - 20, 1,
                                          self.prevCommands[-1], 0, self.widget1, xp.WidgetClass_TextField)

        row = row - 20
        self.doButton = xp.createWidget(110, row - 20, 150, row - 40, 1, "Do", 0, self.widget1, xp.WidgetClass_Button)
        self.helpButton = xp.createWidget(590, row - 20, 630, row - 40, 1, "Help", 0, self.widget1, xp.WidgetClass_Button)
        self.popOutButton = xp.createWidget(640, row - 20, 685, row - 40, 1, "Pop ➚", 0, self.widget1, xp.WidgetClass_Button)
        xp.setWidgetProperty(self.popOutButton, xp.Property_ButtonType, xp.PushButton)
        xp.setWidgetProperty(self.popOutButton, xp.Property_ButtonBehavior, xp.ButtonBehaviorPushButton)

        col1 = 160
        col2 = 350
        col3 = 470
        xp.createWidget(col1, row, 480, row - height, 1,
                        '^A ^E: Beginning / End of line', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(col2, row, 480, row - height, 1,
                        '^D: Delete char', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(col3, row, col3 + 100, row - height, 1,
                        '<Return>: Execute line', 0, self.widget1, xp.WidgetClass_Caption)
        row -= height + 4
        xp.createWidget(col1, row, 480, row - height, 1,
                        '^N ^P: Next / Previous line', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(col2, row, 480, row - height, 1,
                        '^K: Kill to EOL', 0, self.widget1, xp.WidgetClass_Caption)
        row -= height + 4
        xp.createWidget(col1, row, 480, row - height, 1,
                        '^F ^B: Move Forward / Back', 0, self.widget1, xp.WidgetClass_Caption)
        xp.createWidget(col2, row, 480, row - height, 1,
                        '^V: Paste from clipboard', 0, self.widget1, xp.WidgetClass_Caption)

        xp.setWidgetProperty(self.doButton, xp.Property_ButtonType, xp.PushButton)
        xp.setWidgetProperty(self.doButton, xp.Property_ButtonBehavior, xp.ButtonBehaviorPushButton)
        xp.setWidgetProperty(self.helpButton, xp.Property_ButtonType, xp.PushButton)
        xp.setWidgetProperty(self.helpButton, xp.Property_ButtonBehavior, xp.ButtonBehaviorPushButton)

        xp.setWidgetProperty(self.widget1, xp.Property_MainWindowHasCloseBoxes, 1)
        xp.addWidgetCallback(self.widget1, self.widgetMsgs)
        xp.addWidgetCallback(self.textWidget, self.textEdit)

    def textEdit(self, message, widgetID, param1, _param2):
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
                xp.setWidgetDescriptor(widgetID, self.prevCommands[self.historyIdx])
                self.historyIdx = (self.historyIdx - 1) % len(self.prevCommands)
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelStart, len(xp.getWidgetDescriptor(widgetID)))
                xp.setWidgetProperty(widgetID, xp.Property_EditFieldSelEnd, len(xp.getWidgetDescriptor(widgetID)))
                return 1
        return 0

    def widgetMsgs(self, message, widgetID, param1, param2):
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
            except Exception as e:
                xp.log(f"Caught other exception in widget messages, after try_execute: {e}")
                xp.log()
            return 1
        return 0

    def toggleCommand(self, _commandRef, phase, _refCon):
        if phase != xp.CommandBegin:
            return 0
        if not self.widget1:
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

        return 1

    def XPluginStop(self):
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

    def XPluginEnable(self):
        # initialize with leading blank lines -- this puts the "next" input at the very
        # bottom of the window. This mimics scrolling input better.
        self.createPopup(popout=False)
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

    def XPluginDisable(self):
        if self.widget1:
            xp.destroyWidget(self.widget1, 1)
            self.widget1 = None

        if self.listboxWidget is not None:
            self.listboxWidget.destroy()
            self.listboxWidget = None

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def try_execute(self, s):
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
            # with open(os.path.join(xp.getSystemPath(), 'Resources', 'plugins', 'Commands.txt'), "r", encoding='utf-8') as fp_c:
            with open(os.path.join(xp.getSystemPath(), 'Resources', 'plugins', 'DataRefs.txt'), "r", encoding='utf-8') as fp_d:
                items = [x for x in fp_d.readlines() if re.search(s[5:], x, flags=re.IGNORECASE)]
                # items += [x for x in fp_c.readlines() if s[5:].lower() in x.lower()]
            sorted(items)
            for i in items:
                self.listboxWidget.add(i)
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
        except SystemExit:
            raise
        except Exception:
            # do it anyway -- this captures the exception output and
            # adds it to the window
            try:
                self.do('\n'.join(self.partialCommand))
            except Exception:
                pass
            xp.setWidgetDescriptor(self.textWidget, '>>> ')
            self.partialCommand = []

    def do(self, s):
        f = io.StringIO()
        e = io.StringIO()
        num_lines = len(s.split('\n'))
        if s.strip().startswith('#'):
            return
        if s == '':
            self.listboxWidget.add('>>> ')
            return

        with contextlib.redirect_stderr(e):
            with contextlib.redirect_stdout(f):
                print(f">>> {s}")
                try:
                    exec(compile(s, '<string>', 'single'), globals())
                except SystemExit:
                    raise
                except Exception:
                    e_type, value, tb = sys.exc_info()
                    traceback.print_exception(e_type, value, tb)

        s = f.getvalue().strip()
        if s:
            # print stdout, but SKIP the length of the incoming commands. (we already display them)
            for line in s.split('\n')[(num_lines):]:
                self.listboxWidget.add(line)
        s = e.getvalue().strip()
        if s:
            for line in s.split('\n'):
                self.listboxWidget.add(line)

    def paste(self):
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


def getPluginList():
    """
    return list of python plugin signatures
    """
    return [x[1] for x in xp.pythonGetDicts()['plugins'].values()]


def getPluginInstance(signature='xppython3.minipython'):
    """
    For (optional) python plugin signature, return its PythonInterface instance
    """
    for instance, data in xp.pythonGetDicts()['plugins'].items():
        if data[1] == signature:
            return instance
    return None
