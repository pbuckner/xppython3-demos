"""
Override Example

Written by Sandy Barbour - 26/05/2004

Ported to Python by Sandy Barbour - 11/05/2005
Ported to Python3 by Peter Buckner - 8/17/2021

Sandy Barbour - 26/05/2013
Removed "sim/operation/override/override_pfc_autopilot_lites" dataref.
Changed :-
State = XPGetWidgetProperty(self.OverrideCheckBox[Item], xpProperty_ButtonState, 0)
to
State = XPGetWidgetProperty(self.OverrideCheckBox[Item], xpProperty_ButtonState, None)

This examples shows how to apply various overrides.
"""

from XPPython3 import xp


class PythonInterface:
    def XPluginStart(self):
        self.Name = "Override"
        self.Sig = "SandyBarbour.Python.Override"
        self.Desc = "A plug-in that Overrides Xplane."

        self.NumberOfOverrides = 19
        self.MenuItem1 = 0

        self.DataRefGroup = "sim/operation/override/"
        self.DataRefDesc = ["override_planepath", "override_joystick", "override_artstab",
                            "override_flightcontrol", "override_gearbrake", "override_navneedles",
                            "override_adf", "override_dme", "override_gps", "override_flightdir", "override_annunciators",
                            "override_autopilot", "override_joystick_heading", "override_joystick_pitch",
                            "override_joystick_roll", "override_throttles",
                            "override_groundplane", "disable_cockpit_object", "disable_twosided_fuselage"]

        # Create our menu
        Item = xp.appendMenuItem(xp.findPluginsMenu(), "Python - Override Xplane 1", 0)
        self.OverrideMenuHandlerCB = self.OverrideMenuHandler
        self.Id = xp.createMenu("Override", xp.findPluginsMenu(), Item, self.OverrideMenuHandlerCB, 0)
        xp.appendMenuItem(self.Id, "Enable/Disable Override", 1)

        # Flag to tell us if the widget is being displayed.
        self.MenuItem1 = 0

        return self.Name, self.Sig, self.Desc

    def XPluginStop(self):
        if (self.MenuItem1 == 1):
            xp.destroyWidget(self.OverrideWidget, 1)
            self.MenuItem1 = 0

        xp.destroyMenu(self.Id)

    def XPluginEnable(self):
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def OverrideMenuHandler(self, inMenuRef, inItemRef):
        # If menu selected create our widget dialog
        if (inItemRef == 1):
            if (self.MenuItem1 == 0):
                self.OverrideScreenNumber = 0
                self.CreateOverride(300, 550, 350, 380)
                self.MenuItem1 = 1
            else:
                if(not xp.isWidgetVisible(self.OverrideWidget)):
                    xp.showWidget(self.OverrideWidget)

        """
        This will create our widget dialog.
        I have made all child widgets relative to the input paramter.
        This makes it easy to position the dialog
        """
    def CreateOverride(self, x, y, w, h):
        x2 = x + w
        y2 = y - h
        WindowCentre = int(x + w / 2)

        self.GetDataRefIds()

        self.OverrideWidget = xp.createWidget(x, y, x2, y2,
                                              1, "Python - Xplane Override 1", 1, 0,
                                              xp.WidgetClass_MainWindow)

        xp.setWidgetProperty(self.OverrideWidget, xp.Property_MainWindowHasCloseBoxes, 1)

        self.OverridePanel = xp.createWidget(x + 50, y - 50, x2 - 50, y2 + 50,
                                             1, "", 0, self.OverrideWidget,
                                             xp.WidgetClass_SubWindow)

        xp.setWidgetProperty(self.OverridePanel, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)

        self.OverridePreviousButton = xp.createWidget(WindowCentre - 80, y2 + 24, WindowCentre - 10, y2 + 2,
                                                      1, "Previous", 0, self.OverrideWidget,
                                                      xp.WidgetClass_Button)

        xp.setWidgetProperty(self.OverridePreviousButton, xp.Property_ButtonType, xp.PushButton)

        self.OverrideNextButton = xp.createWidget(WindowCentre + 10, y2 + 24, WindowCentre + 80, y2 + 2,
                                                  1, "Next", 0, self.OverrideWidget,
                                                  xp.WidgetClass_Button)

        xp.setWidgetProperty(self.OverrideNextButton, xp.Property_ButtonType, xp.PushButton)

        self.OverrideEdit = []
        for Item in range(8):
            yOffset = 45 + 28 + (Item * 30)
            self.OverrideEdit.append(xp.createWidget(x + 60, y - yOffset, x + 60 + 200, y - yOffset - 20,
                                                     1, "", 0, self.OverrideWidget,
                                                     xp.WidgetClass_TextField))
            xp.setWidgetProperty(self.OverrideEdit[Item], xp.Property_TextFieldType, xp.TextEntryField)

        self.OverrideCheckBox = []
        for Item in range(8):
            yOffset = 45 + 28 + (Item * 30)
            self.OverrideCheckBox.append(xp.createWidget(x + 260, y - yOffset, x + 260 + 22, y - yOffset - 20,
                                                         1, "", 0, self.OverrideWidget,
                                                         xp.WidgetClass_Button))

            xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonType, xp.RadioButton)
            xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonBehavior, xp.ButtonBehaviorCheckBox)
            xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonState, 1)

        self.RefreshOverride()

        self.OverrideHandlerCB = self.OverrideHandler
        xp.addWidgetCallback(self.OverrideWidget, self.OverrideHandlerCB)

    def OverrideHandler(self, inMessage, inWidget, inParam1, inParam2):
        if inMessage == xp.Message_CloseButtonPushed:
            if (self.MenuItem1 == 1):
                xp.hideWidget(self.OverrideWidget)
            return 1

        if inMessage == xp.Msg_PushButtonPressed:

            if inParam1 == self.OverridePreviousButton:
                self.OverrideScreenNumber -= 1
                if self.OverrideScreenNumber < 0:
                    self.OverrideScreenNumber = 0
                self.RefreshOverride()
                return 1

            if inParam1 == self.OverrideNextButton:
                self.OverrideScreenNumber += 1
                if self.OverrideScreenNumber > self.MaxScreenNumber:
                    self.OverrideScreenNumber = self.MaxScreenNumber
                self.RefreshOverride()
                return 1

        if inMessage == xp.Msg_ButtonStateChanged:
            for Item in range(8):
                if Item + (self.OverrideScreenNumber * 8) < self.NumberOfOverrides:
                    if self.DataRefID[Item + (self.OverrideScreenNumber * 8)]:
                        State = xp.getWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonState, None)
                        self.SetDataRefState(self.DataRefID[Item + (self.OverrideScreenNumber * 8)], State)
            return 1

        return 0

    def RefreshOverride(self):

        for Item in range(8):
            if Item + (self.OverrideScreenNumber * 8) < self.NumberOfOverrides:
                if self.DataRefID[Item + (self.OverrideScreenNumber * 8)]:
                    xp.setWidgetDescriptor(self.OverrideEdit[Item], self.DataRefDesc[Item + (self.OverrideScreenNumber * 8)])
                    if self.GetDataRefState(self.DataRefID[Item + (self.OverrideScreenNumber * 8)]):
                        xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonState, 1)
                    else:
                        xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonState, 0)
                    xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_Enabled, 1)
            else:
                xp.setWidgetDescriptor(self.OverrideEdit[Item], "")
                xp.setWidgetProperty(self.OverrideCheckBox[Item], xp.Property_ButtonState, 0)

        if self.OverrideScreenNumber == 0:
            xp.setWidgetProperty(self.OverridePreviousButton, xp.Property_Enabled, 0)
        else:
            xp.setWidgetProperty(self.OverridePreviousButton, xp.Property_Enabled, 1)
            xp.setWidgetDescriptor(self.OverridePreviousButton, "Previous")

        if self.OverrideScreenNumber == self.MaxScreenNumber:
            xp.setWidgetProperty(self.OverrideNextButton, xp.Property_Enabled, 0)
        else:
            xp.setWidgetProperty(self.OverrideNextButton, xp.Property_Enabled, 1)
            xp.setWidgetDescriptor(self.OverrideNextButton, "Next")

    def GetDataRefIds(self):
        self.DataRefID = []
        for Item in range(self.NumberOfOverrides):
            TempDataRefID = xp.findDataRef(self.DataRefGroup + str(self.DataRefDesc[Item]))
            if Item == 0:
                self.SpecialDataRef = TempDataRefID
            self.DataRefID.append(TempDataRefID)

        self.MaxScreenNumber = (self.NumberOfOverrides - 1) // 8

    def GetDataRefState(self, DataRefID):
        if (DataRefID == self.SpecialDataRef):
            self.IntVals = []
            xp.getDatavi(DataRefID, self.IntVals, 0, 8)
            DataRefi = self.IntVals[0]
        else:
            DataRefi = xp.getDatai(DataRefID)

        return DataRefi

    def SetDataRefState(self, DataRefID, State):
        if (DataRefID == self.SpecialDataRef):
            IntVals = [State, 0, 0, 0, 0, 0, 0, 0]
            xp.setDatavi(DataRefID, IntVals, 0, 8)
        else:
            xp.setDatai(DataRefID, State)
