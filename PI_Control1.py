"""
Control Example

Written by Sandy Barbour - 26/05/2004

Ported to Python by Sandy Barbour - 10/05/2005
Ported to Python3 by Peter Buckner - 8/17/2021

This examples shows how to move the aircraft control surfaces.
Should be used with the override plugin.
"""

from XPPython3 import xp


class PythonInterface:
    def XPluginStart(self):
        self.Name = "Control1"
        self.Sig = "SandyBarbour.Python.Control1"
        self.Desc = "A plug-in that move the control surfaces."
        self.MAX_ITEMS = 12
        # Use lists for the datarefs, makes it easier to add extra datarefs
        DataRefString = ["sim/joystick/yolk_pitch_ratio", "sim/joystick/yolk_roll_ratio", "sim/joystick/yolk_heading_ratio",
                         "sim/joystick/artstab_pitch_ratio", "sim/joystick/artstab_roll_ratio", "sim/joystick/artstab_heading_ratio",
                         "sim/joystick/FC_ptch", "sim/joystick/FC_roll", "sim/joystick/FC_hdng",
                         "sim/flightmodel/weight/m_fuel1", "sim/flightmodel/weight/m_fuel2", "sim/flightmodel/weight/m_fuel3"]

        self.DataRefDesc = ["Yolk Pitch", "Yolk Roll", "Yolk Heading", "AS Pitch", "AS Roll", "AS Heading", "FC Pitch",
                            "FC Roll", "FC Heading", "Fuel 1", "Fuel 2", "Fuel 3"]

        self.IncrementValue = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 10.0, 10.0, 10.0]

        # Create our menu
        Item = xp.appendMenuItem(xp.findPluginsMenu(), "Python - Control 1", 0)
        self.ControMenuHandlerCB = self.ControMenuHandler
        self.Id = xp.createMenu("Control1", xp.findPluginsMenu(), Item, self.ControMenuHandlerCB, 0)
        xp.appendMenuItem(self.Id, "Control1", 1)

        # Flag to tell us if the widget is being displayed.
        self.MenuItem1 = 0

        # Get our dataref handles here
        self.ControlDataRef = []
        for self.Item in range(self.MAX_ITEMS):
            self.ControlDataRef.append(xp.findDataRef(DataRefString[self.Item]))

        return self.Name, self.Sig, self.Desc

    def XPluginStop(self):
        if self.MenuItem1 == 1:
            xp.destroyWidget(self.ControlWidget, 1)
            self.MenuItem1 = 0

        xp.destroyMenu(self.Id)

    def XPluginEnable(self):
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def ControMenuHandler(self, inMenuRef, inItemRef):
        # If menu selected create our widget dialog
        if inItemRef == 1:
            if self.MenuItem1 == 0:
                self.CreateControl(300, 550, 350, 530)
                self.MenuItem1 = 1
            else:
                if not xp.isWidgetVisible(self.ControlWidget):
                    xp.showWidget(self.ControlWidget)

    """
    This will create our widget dialog.
    I have made all child widgets relative to the input paramter.
    This makes it easy to position the dialog
    """
    def CreateControl(self, x, y, w, h):

        FloatValue = []
        for self.Item in range(self.MAX_ITEMS):
            FloatValue.append(xp.getDataf(self.ControlDataRef[self.Item]))

        x2 = x + w
        y2 = y - h

        # Create the Main Widget window
        self.ControlWidget = xp.createWidget(x, y, x2, y2, 1, "Python - Control 1 Example by Sandy Barbour",
                                             1, 0, xp.WidgetClass_MainWindow)

        # Add Close Box decorations to the Main Widget
        xp.setWidgetProperty(self.ControlWidget, xp.Property_MainWindowHasCloseBoxes, 1)

        # Create the Sub Widget window
        ControlWindow = xp.createWidget(x + 50, y - 50, x2 - 50, y2 + 50, 1,
                                        "", 0, self.ControlWidget, xp.WidgetClass_SubWindow)

        # Set the style to sub window
        xp.setWidgetProperty(ControlWindow, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)

        ControlText = []
        self.ControlEdit = []
        self.UpArrow = []
        self.DownArrow = []

        for Item in range(self.MAX_ITEMS):

            ControlText.append(xp.createWidget(x + 60, y - (70 + (Item * 30)), x + 115, y - (92 + (Item * 30)),
                                               1,  # Visible
                                               self.DataRefDesc[Item],  # desc
                                               0,  # root
                                               self.ControlWidget,
                                               xp.WidgetClass_Caption))

            buffer = "%f" % (FloatValue[Item])
            self.ControlEdit.append(xp.createWidget(x + 160, y - (70 + (Item * 30)), x + 250, y - (92 + (Item * 30)),
                                                    1, buffer, 0, self.ControlWidget,
                                                    xp.WidgetClass_TextField))

            xp.setWidgetProperty(self.ControlEdit[Item], xp.Property_TextFieldType, xp.TextEntryField)

            self.UpArrow.append(xp.createWidget(x + 252, y - (66 + (Item * 30)), x + 264, y - (81 + (Item * 30)),
                                                1, "", 0, self.ControlWidget,
                                                xp.WidgetClass_Button))

            xp.setWidgetProperty(self.UpArrow[Item], xp.Property_ButtonType, xp.LittleUpArrow)

            self.DownArrow.append(xp.createWidget(x + 252, y - (81 + (Item * 30)), x + 264, y - (96 + (Item * 30)),
                                                  1, "", 0, self.ControlWidget,
                                                  xp.WidgetClass_Button))

            xp.setWidgetProperty(self.DownArrow[Item], xp.Property_ButtonType, xp.LittleDownArrow)

        self.ControlApplyButton = xp.createWidget(x + 120, y - 440, x + 210, y - 462,
                                                  1, "Apply Data", 0, self.ControlWidget,
                                                  xp.WidgetClass_Button)

        xp.setWidgetProperty(self.ControlApplyButton, xp.Property_ButtonType, xp.PushButton)

        # Register our widget handler
        self.ControlHandlerCB = self.ControlHandler
        xp.addWidgetCallback(self.ControlWidget, self.ControlHandlerCB)

    def ControlHandler(self, inMessage, inWidget, inParam1, inParam2):

        FloatValue = []

        for Item in range(self.MAX_ITEMS):
            FloatValue.append(xp.getDataf(self.ControlDataRef[Item]))

        if inMessage == xp.Message_CloseButtonPushed:
            if self.MenuItem1 == 1:
                xp.hideWidget(self.ControlWidget)
            return 1

        if inMessage == xp.Msg_PushButtonPressed:

            if inParam1 == self.ControlApplyButton:
                self.ApplyValues()
                return 1

            for Item in range(self.MAX_ITEMS):
                if inParam1 == self.UpArrow[Item]:
                    FloatValue[Item] += self.IncrementValue[Item]
                    buffer = "%f" % (FloatValue[Item])
                    xp.setWidgetDescriptor(self.ControlEdit[Item], buffer)
                    xp.setDataf(self.ControlDataRef[Item], FloatValue[Item])
                    return 1

            for Item in range(self.MAX_ITEMS):
                if inParam1 == self.DownArrow[Item]:
                    FloatValue[Item] -= self.IncrementValue[Item]
                    buffer = "%f" % (FloatValue[Item])
                    xp.setWidgetDescriptor(self.ControlEdit[Item], buffer)
                    xp.setDataf(self.ControlDataRef[Item], FloatValue[Item])
                    return 1

        return 0

    def ApplyValues(self):
        for Item in range(self.MAX_ITEMS):
            buffer = xp.getWidgetDescriptor(self.ControlEdit[Item])
            xp.setDataf(self.ControlDataRef[Item], float(buffer))
