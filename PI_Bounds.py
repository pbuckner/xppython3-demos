import xp


def whichMonitor(winID):
    """
    Determine which monitor you window is being displayed on. (Technically, which monitor contains
    the upper left corner of your window.)

    Returns idx of monitor, or -1 if there are no full-screen windows.
    """

    if xp.windowIsInVR(winID):
        return -1

    def getMonitorBoundsGlobal(idx, left, t, r, b, data):
        data[idx] = (left, t, r, b)

    data = {}
    xp.getAllMonitorBoundsGlobal(getMonitorBoundsGlobal, data)
    if not data:
        return -1
    if xp.windowIsPoppedOut(winID):
        left, top, right, bottom = xp.getWindowGeometryOS(winID)
    else:
        left, top, right, bottom = xp.getWindowGeometry(winID)
    idx = None
    for idx, values in data.items():
        if left >= values[0] and left <= values[2] and top <= values[1] and top >= values[3]:
            break
    if idx is None:
        for idx, values in data.items():
            if right >= values[0] and right <= values[2] and top <= values[1] and top >= values[3]:
                break
        if idx is None:
            for idx, values in data.items():
                if left >= values[0] and left <= values[2] and bottom <= values[1] and bottom >= values[3]:
                    break
            if idx is None:
                for idx, values in data.items():
                    if right >= values[0] and right <= values[2] and bottom <= values[1] and bottom >= values[3]:
                        break
    return idx


class PythonInterface:
    def XPluginStart(self):
        self.inVR = False
        return 'PI_Bounds v.1', 'xppython.bounds', 'Simple monitor bounds reporter'

    def XPluginEnable(self):
        xp.log("ScreenSize: {} x {}".format(*xp.getScreenSize()))
        left, top, right, bottom = xp.getScreenBoundsGlobal()
        describe("ScreenBoundsGlobal", left, top, right, bottom)

        self.monitorBoundsGlobal = {}
        self.monitorBoundsGlobalOS = {}

        xp.getAllMonitorBoundsGlobal(self.getMonitorBoundsGlobal, self.monitorBoundsGlobal)
        for i in self.monitorBoundsGlobal:
            left, top, right, bottom = self.monitorBoundsGlobal[i]
            describe("AllGlobal: [{}]".format(i), left, top, right, bottom)

        xp.getAllMonitorBoundsOS(self.getMonitorBoundsGlobal, self.monitorBoundsGlobalOS)
        for i in self.monitorBoundsGlobalOS:
            left, top, right, bottom = self.monitorBoundsGlobalOS[i]
            describe("AllGlobalOS: [{}]".format(i), left, top, right, bottom)

        xp.log("Mouse is: {}".format(xp.getMouseLocationGlobal()))
        decoration = xp.WindowDecorationRoundRectangle
        layer = xp.WindowLayerFloatingWindows
        self.refcon = []
        pos = [0, 50, 200, -50, 1,
               self.draw, self.click, self.key, self.cursor, self.wheel, self.refcon,
               decoration, layer, None]
        self.winID = xp.createWindowEx(pos)
        self.onMonitor = None

        # Positioning Mode:
        #   * WindowCenterOnMonitor: monitorIdx=-1 means "main x-plane monitor", 0+ is monitor index, if monitor
        #       does not exist, place on main monitor
        #   * WindowPositionFree: monitorIdx is ignored (convention is to use -1)
        #   * WindowVR: monitorIdx is ignored as there is no "monitor". The window is centered in the user's view
        #
        # If you use something other than WindowPositionFree, the (left, top, right, bottom)
        # values provided with CreateWindowEx are stored with the window, BUT, then
        # actual window's position will be changed. For example, if using WindowCenterOnMonitor,
        # then the window's width and height are calculated from (left, top, right, bottom), and
        # a window of the specified dimension is placed in the center of the monitor.

        if self.inVR:
            xp.setWindowPositioningMode(self.winID, xp.WindowVR, -1)
        else:
            xp.setWindowPositioningMode(self.winID, xp.WindowCenterOnMonitor, 5)
        # xp.setWindowPositioningMode(self.winID, xp.WindowPositionFree, -1)

        # So, say you want to position your window in the lower left corner of the "main" window:
        # 1) create window using WindowCenterOnMonitor, -1... the window is now centered on main screen
        # 2) get window's geometry. Compare this with set of monitors returned from getAllMonitorsBoundsGlobal
        #    Determine monitor idx into which the window has been displayed (See whichMonitor() example code)
        # 3) get the monitors bounds for indicated monitor (retrieve all monitors and use only the one you want).
        # 4) reset window geometry based on monitor's size
        # 5) reset window positioning mode to WindowPositionFree (as otherwise, it will still stay centered!)

        return 1

    def draw(self, winID, refCon):
        if self.inVR and not xp.windowIsInVR(winID):
            xp.log("moving window to VR")
            xp.setWindowPositioningMode(winID, xp.WindowVR, -1)
        # getWindowGeometry gets the _actual_ window position, which may
        # be different from the position provided with CreateWindowEx()
        # _even before the window is moved by the user_
        # (The difference would be due to the WindowPositioningMode used with CreateWindowEx)
        idx = whichMonitor(winID)

        w, h, x = xp.getFontDimensions(xp.Font_Basic)

        left, top, right, bottom = xp.getWindowGeometry(winID)
        if xp.windowIsPoppedOut(winID):
            # You draw at getWindowGeomtery() locations.
            # The _location_ of the poppedout window is getWindowGeometryOS()
            leftOS, topOS, rightOS, bottomOS = xp.getWindowGeometryOS(winID)
            w = xp.measureString(xp.Font_Basic, "{}".format((rightOS, bottomOS)))
            xp.drawString((1., 1., 1.), left, top - h, "{}".format((leftOS, topOS)), None, xp.Font_Basic)
            xp.drawString((1., 1., 1.), left, int((top + bottom) / 2), "Monitor #{}".format(idx), None, xp.Font_Basic)
            xp.drawString((1., 1., 1.), right - int(w), bottom, "{}".format((rightOS, bottomOS)), None, xp.Font_Basic)
        elif xp.windowIsInVR(winID):
            width, height = xp.getWindowGeometryVR(winID)
            xp.drawString((1., 1., 1.), left, top - h, "{} x {}".format(width, height), None, xp.Font_Basic)
            xp.drawString((1., 1., 1.), left, int((top + bottom) / 2), "VR", None, xp.Font_Basic)
        else:
            w = xp.measureString(xp.Font_Basic, "{}".format((right, bottom)))
            xp.drawString((1., 1., 1.), left, top - h, "{}".format((left, top)), None, xp.Font_Basic)
            xp.drawString((1., 1., 1.), left, int((top + bottom) / 2), "Monitor #{}".format(idx), None, xp.Font_Basic)
            xp.drawString((1., 1., 1.), right - int(w), bottom, "{}".format((right, bottom)), None, xp.Font_Basic)

        # Note: if we _want_ to let the user move the window, we have to set
        # positioning mode to WindowPositionFree. BUT, if we've not update the
        # window's geomtry the window will jump to the position used with CreateWindowEx
        # Therefore, update the internal data using SetWindowGeometry and then change
        # WindowPositioningMode
        if not (xp.windowIsPoppedOut(winID) or xp.windowIsInVR(winID)):
            xp.setWindowGeometry(winID, left, top, right, bottom)
            xp.setWindowPositioningMode(winID, xp.WindowPositionFree, -1)
        return

    @staticmethod
    def click(winID, x, y, mouse, refcon):
        return 1

    @staticmethod
    def key(winId, key, flags, vkey, refcon, losing):
        return

    @staticmethod
    def cursor(windID, x, y, refcon):
        return xp.CursorDefault

    @staticmethod
    def wheel(winId, x, y, wheel, clicks, refcon):
        return 1

    def getMonitorBoundsGlobal(self, idx, left, t, r, b, refcon):
        refcon[idx] = (left, t, r, b)

    def XPluginStop(self):
        pass

    def XPluginDisable(self):
        if self.winID:
            xp.destroyWindow(self.winID)
            self.winID = None

    def XPluginReceiveMessage(self, who, msg, param):
        if msg == xp.MSG_ENTERED_VR:
            xp.log("Entering VR")
            self.inVR = True
        elif msg == xp.MSG_EXITING_VR:
            xp.log("Exiting VR")
            self.inVR = False
        return


def describe(label, left, top, right, bottom):
    """
    Pretty prints rectangular dimensions into the logfile
    """
    lt = str((left, top))
    rt = str((right, top))
    lb = str((left, bottom))
    rb = str((right, bottom))
    xp.log("{}{}{}".format(lt, '-' * 10, rt))
    xp.log("{}|{}|".format(' ' * lt.index(','),
                           ' ' * (len(lt) - lt.index(',') + 9 + rt.index(','))))
    xp.log("{}|{: ^{width}}|".format(' ' * lt.index(','),
                                     label,
                                     width=(len(lt) - lt.index(',') + 9 + rt.index(','))))
    xp.log("{}|{: ^{width}}|".format(' ' * lt.index(','),
                                     "{} x {}".format(right - left, top - bottom),
                                     width=(len(lt) - lt.index(',') + 9 + rt.index(','))))
    xp.log("{}|{}|".format(' ' * lt.index(','),
                           ' ' * (len(lt) - lt.index(',') + 9 + rt.index(','))))
    xp.log("{}{}{}".format(lb, '-' * (10 + len(lt) - len(lb)), rb))
