"""
Position Example

Written by Sandy Barbour - 26/05/2004

Ported to Python by Sandy Barbour - 10/05/2005
Ported to Python3 by Peter Buckner - 08-15-2021

This examples shows how to change the aircraft attitude.
Should be used with the override plugin.
"""

from XPPython3 import xp


class PythonInterface:
    def XPluginStart(self):
        self.Name = "Position1 v1.0"
        self.Sig = "SandyBarbour.Python.Position1"
        self.Desc = "A plug-in that changes the aircraft attitude."

        self.MAX_ITEMS = 11

        # Use lists for the datarefs, makes it easier to add extra datarefs
        self.DataRefString = ["sim/flightmodel/position/local_x", "sim/flightmodel/position/local_y", "sim/flightmodel/position/local_z",
                              "sim/flightmodel/position/lat_ref", "sim/flightmodel/position/lon_ref", "sim/flightmodel/position/theta",
                              "sim/flightmodel/position/phi", "sim/flightmodel/position/psi",
                              "sim/flightmodel/position/latitude", "sim/flightmodel/position/longitude", "sim/flightmodel/position/elevation"]

        self.DataRefDesc = ["Local x", "Local y", "Local z", "Lat Ref", "Lon Ref", "Theta", "Phi", "Psi"]
        self.Description = ["Latitude", "Longitude", "Elevation"]

        # Create our menu
        Item = xp.appendMenuItem(xp.findPluginsMenu(), "Python - Position 1", 0)
        self.PositionMenuHandlerCB = self.PositionMenuHandler
        self.Id = xp.createMenu("Position1", xp.findPluginsMenu(), Item, self.PositionMenuHandlerCB, 0)
        xp.appendMenuItem(self.Id, "Position1", 1)

        # Flag to tell us if the widget is being displayed.
        self.MenuItem1 = 0

        # Get our dataref handles here
        self.PositionDataRef = []
        for Item in range(self.MAX_ITEMS):
            self.PositionDataRef.append(xp.findDataRef(self.DataRefString[Item]))

        return self.Name, self.Sig, self.Desc

    def XPluginStop(self):
        if self.MenuItem1 == 1:
            xp.destroyWidget(self.PositionWidget, 1)
            self.MenuItem1 = 0

        xp.destroyMenu(self.Id)

    def XPluginEnable(self):
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def PositionMenuHandler(self, inMenuRef, inItemRef):
        # If menu selected create our widget dialog
        if inItemRef == 1:
            if self.MenuItem1 == 0:
                self.CreatePosition(300, 600, 300, 550)
                self.MenuItem1 = 1
            else:
                if not xp.isWidgetVisible(self.PositionWidget):
                    xp.showWidget(self.PositionWidget)

    """
    This will create our widget dialog.
    I have made all child widgets relative to the input paramter.
    This makes it easy to position the dialog
    """
    def CreatePosition(self, x, y, w, h):
        FloatValue = []
        for Item in range(self.MAX_ITEMS):
            FloatValue.append(xp.getDataf(self.PositionDataRef[Item]))

        # X, Y, Z, Lat, Lon, Alt
        DoubleValue = [0.0, 0.0, 0.0]
        DoubleValue[0], DoubleValue[1], DoubleValue[2] = xp.localToWorld(FloatValue[0], FloatValue[1], FloatValue[2])
        DoubleValue[2] *= 3.28

        x2 = x + w
        y2 = y - h
        PositionText = []

        # Create the Main Widget window
        self.PositionWidget = xp.createWidget(x, y, x2, y2, 1, "Python - Position Example 1 by Sandy Barbour", 1,
                                              0, xp.WidgetClass_MainWindow)

        # Add Close Box decorations to the Main Widget
        xp.setWidgetProperty(self.PositionWidget, xp.Property_MainWindowHasCloseBoxes, 1)

        # Create the Sub Widget window
        PositionWindow = xp.createWidget(x + 50, y - 50, x2 - 50, y2 + 50, 1, "", 0,
                                         self.PositionWidget, xp.WidgetClass_SubWindow)

        # Set the style to sub window
        xp.setWidgetProperty(PositionWindow, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)

        self.PositionEdit = []
        self.UpArrow = []
        self.DownArrow = []
        self.Position2Edit = []

        for Item in range(self.MAX_ITEMS - 3):

            PositionText.append(xp.createWidget(x + 60, y - (70 + (Item * 30)), x + 115, y - (92 + (Item * 30)),
                                                1,  # Visible
                                                self.DataRefDesc[Item],  # desc
                                                0,  # root
                                                self.PositionWidget,
                                                xp.WidgetClass_Caption))

            buffer = "%f" % (FloatValue[Item])
            self.PositionEdit.append(xp.createWidget(x + 120, y - (70 + (Item * 30)), x + 210, y - (92 + (Item * 30)),
                                                     1, buffer, 0, self.PositionWidget,
                                                     xp.WidgetClass_TextField))

            xp.setWidgetProperty(self.PositionEdit[Item], xp.Property_TextFieldType, xp.TextEntryField)

            self.UpArrow.append(xp.createWidget(x + 212, y - (66 + (Item * 30)), x + 224, y - (81 + (Item * 30)),
                                                1, "", 0, self.PositionWidget,
                                                xp.WidgetClass_Button))

            xp.setWidgetProperty(self.UpArrow[Item], xp.Property_ButtonType, xp.LittleUpArrow)

            self.DownArrow.append(xp.createWidget(x + 212, y - (81 + (Item * 30)), x + 224, y - (96 + (Item * 30)),
                                                  1, "", 0, self.PositionWidget,
                                                  xp.WidgetClass_Button))

            xp.setWidgetProperty(self.DownArrow[Item], xp.Property_ButtonType, xp.LittleDownArrow)

        self.PositionApplyButton = xp.createWidget(x + 50, y - 310, x + 140, y - 332,
                                                   1, "Apply Data", 0, self.PositionWidget,
                                                   xp.WidgetClass_Button)

        xp.setWidgetProperty(self.PositionApplyButton, xp.Property_ButtonType, xp.PushButton)

        self.LatLonRefApplyButton = xp.createWidget(x + 145, y - 310, x + 240, y - 332,
                                                    1, "Apply LatLonRef", 0, self.PositionWidget,
                                                    xp.WidgetClass_Button)

        xp.setWidgetProperty(self.LatLonRefApplyButton, xp.Property_ButtonType, xp.PushButton)

        Position2Text = []
        for Item in range(3):
            Position2Text.append(xp.createWidget(x + 60, y - (350 + (Item * 30)),
                                                 x + 115, y - (372 + (Item * 30)),
                                                 1,  # Visible
                                                 self.Description[Item],  # desc
                                                 0,  # root
                                                 self.PositionWidget,
                                                 xp.WidgetClass_Caption))

            buffer = "%lf" % (DoubleValue[Item])
            self.Position2Edit.append(xp.createWidget(x + 120, y - (350 + (Item * 30)),
                                                      x + 210, y - (372 + (Item * 30)),
                                                      1, buffer, 0, self.PositionWidget,
                                                      xp.WidgetClass_TextField))

            xp.setWidgetProperty(self.PositionEdit[Item], xp.Property_TextFieldType, xp.TextEntryField)

        self.LatLonAltApplyButton = xp.createWidget(x + 70, y - 440, x + 220, y - 462,
                                                    1, "Apply LatLonAlt", 0, self.PositionWidget,
                                                    xp.WidgetClass_Button)

        xp.setWidgetProperty(self.LatLonAltApplyButton, xp.Property_ButtonType, xp.PushButton)

        self.ReloadSceneryButton = xp.createWidget(x + 70, y - 465, x + 220, y - 487,
                                                   1, "Reload Scenery", 0, self.PositionWidget,
                                                   xp.WidgetClass_Button)

        xp.setWidgetProperty(self.ReloadSceneryButton, xp.Property_ButtonType, xp.PushButton)

        # Register our widget handler
        self.PositionHandlerCB = self.PositionHandler
        xp.addWidgetCallback(self.PositionWidget, self.PositionHandlerCB)

    def PositionHandler(self, inMessage, inWidget, inParam1, inParam2):

        FloatValue = []

        for Item in range(self.MAX_ITEMS):
            FloatValue.append(xp.getDataf(self.PositionDataRef[Item]))

        if inMessage == xp.Message_CloseButtonPushed:
            if self.MenuItem1 == 1:
                xp.hideWidget(self.PositionWidget)
            return 1

        if inMessage == xp.Msg_PushButtonPressed:

            if inParam1 == self.PositionApplyButton:
                self.ApplyValues()
                return 1

            if inParam1 == self.LatLonRefApplyButton:
                self.ApplyLatLonRefValues()
                return 1

            if inParam1 == self.LatLonAltApplyButton:
                self.ApplyLatLonAltValues()
                return 1

            if inParam1 == self.ReloadSceneryButton:
                xp.reloadScenery()
                return 1

            for Item in range(self.MAX_ITEMS - 3):
                if inParam1 == self.UpArrow[Item]:
                    FloatValue[Item] += 1.0
                    buffer = "%f" % (FloatValue[Item])
                    xp.setWidgetDescriptor(self.PositionEdit[Item], buffer)
                    xp.setDataf(self.PositionDataRef[Item], FloatValue[Item])
                    return 1

            for Item in range(self.MAX_ITEMS - 3):
                if (inParam1 == self.DownArrow[Item]):
                    FloatValue[Item] -= 1.0
                    buffer = "%f" % (FloatValue[Item])
                    xp.setWidgetDescriptor(self.PositionEdit[Item], buffer)
                    xp.setDataf(self.PositionDataRef[Item], FloatValue[Item])
                    return 1

        return 0

    def ApplyValues(self):
        for Item in range(self.MAX_ITEMS - 3):
            buffer = xp.getWidgetDescriptor(self.PositionEdit[Item])
            xp.setDataf(self.PositionDataRef[Item], float(buffer))

    def ApplyLatLonRefValues(self):
        buffer = xp.getWidgetDescriptor(self.PositionEdit[3])
        FloatValue = float(buffer)
        xp.setDataf(self.PositionDataRef[3], FloatValue)

        buffer = xp.getWidgetDescriptor(self.PositionEdit[4])
        FloatValue = float(buffer)
        xp.setDataf(self.PositionDataRef[4], FloatValue)

    def ApplyLatLonAltValues(self):
        # This gets the lat/lon/alt from the widget text fields
        FloatValue = [0.0, 0.0, 0.0]
        for Item in range(3):
            buffer = xp.getWidgetDescriptor(self.Position2Edit[Item])
            FloatValue[Item] = float(buffer)

        # Lat, Lon, Alt, X, Y, Z
        DoubleValue = [0.0, 0.0, 0.0]
        DoubleValue[0], DoubleValue[1], DoubleValue[2] = xp.worldToLocal(FloatValue[0], FloatValue[1], FloatValue[2] / 3.28)

        for Item in range(3):
            # This writes out the lat/lon/alt from the widget text fields back to the datarefs
            xp.setDataf(self.PositionDataRef[Item + 8], FloatValue[Item])
            # This writes out the x,y,z datarefs after conversion from lat/lon/alt back to the datarefs
            xp.setDataf(self.PositionDataRef[Item], DoubleValue[Item])

        self.ApplyLatLonRefValues()
