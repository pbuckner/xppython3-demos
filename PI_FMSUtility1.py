"""
FMSUtility example

Written by Sandy Barbour - 21/01/2005
Ported to Python by Sandy Barbour - 04/05/2005
Ported to Python3 by Peter Buckner - 09/10/2021

This examples shows how to access the FMS.
"""

from XPPython3 import xp


class PythonInterface:
    def XPluginStart(self):
        self.Name = "FMSUtility1 v1.0"
        self.Sig = "SandyBarbour.Python.FMSUtility1"
        self.Desc = "A plug-in that accesses the FMS."

        self.MAX_NAV_TYPES = 13
        self.MenuItem1 = 0
        self.NavTypeLinePosition = 0

        self.NavTypeLookup = [["Unknown", xp.Nav_Unknown],
                              ["Airport", xp.Nav_Airport],
                              ["NDB", xp.Nav_NDB],
                              ["VOR", xp.Nav_VOR],
                              ["ILS", xp.Nav_ILS],
                              ["Localizer", xp.Nav_Localizer],
                              ["Glide Slope", xp.Nav_GlideSlope],
                              ["Outer Marker", xp.Nav_OuterMarker],
                              ["Middle Marker", xp.Nav_MiddleMarker],
                              ["Inner Marker", xp.Nav_InnerMarker],
                              ["Fix", xp.Nav_Fix],
                              ["DME", xp.Nav_DME],
                              ["Lat/Lon", xp.Nav_LatLon]]

        # Create our menu
        Item = xp.appendMenuItem(xp.findPluginsMenu(), "Python - FMSUtility 1", 0)
        self.FMSUtilityMenuHandlerCB = self.FMSUtilityMenuHandler
        self.Id = xp.createMenu("FMSUtility 1", xp.findPluginsMenu(), Item, self.FMSUtilityMenuHandlerCB, 0)
        xp.appendMenuItem(self.Id, "Utility Panel", 1)

        return self.Name, self.Sig, self.Desc

    def XPluginStop(self):
        if (self.MenuItem1 == 1):
            xp.destroyWidget(self.FMSUtilityWidget, 1)
            self.MenuItem1 = 0

        xp.destroyMenu(self.Id)
        pass

    def XPluginEnable(self):
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def FMSUtilityMenuHandler(self, inMenuRef, inItemRef):
        # If menu selected create our widget dialog
        if (inItemRef == 1):
            if (self.MenuItem1 == 0):
                self.CreateFMSUtilityWidget(221, 640, 420, 290)
                self.MenuItem1 = 1
            else:
                if(not xp.isWidgetVisible(self.FMSUtilityWidget)):
                    xp.showWidget(self.FMSUtilityWidget)

    """
    This will create our widget dialog.
    I have made all child widgets relative to the input paramter.
    This makes it easy to position the dialog
    """
    def CreateFMSUtilityWidget(self, x, y, w, h):
        x2 = x + w
        y2 = y - h
        Buffer = "Python - FMS Example 1 by Sandy Barbour - 2005"

        # Create the Main Widget window
        self.FMSUtilityWidget = xp.createWidget(x, y, x2, y2, 1, Buffer, 1, 0, xp.WidgetClass_MainWindow)

        # Add Close Box decorations to the Main Widget
        xp.setWidgetProperty(self.FMSUtilityWidget, xp.Property_MainWindowHasCloseBoxes, 1)

        # Create the Sub Widget1 window
        FMSUtilityWindow1 = xp.createWidget(x + 10, y - 30, x + 160, y2 + 10,
                                            1,  # Visible
                                            "",  # desc
                                            0,  # root
                                            self.FMSUtilityWidget,
                                            xp.WidgetClass_SubWindow)

        # Set the style to sub window
        xp.setWidgetProperty(FMSUtilityWindow1, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)

        # Create the Sub Widget2 window
        FMSUtilityWindow2 = xp.createWidget(x + 170, y - 30, x2 - 10, y2 + 10,
                                            1,  # Visible
                                            "",  # desc
                                            0,  # root
                                            self.FMSUtilityWidget,
                                            xp.WidgetClass_SubWindow)

        # Set the style to sub window
        xp.setWidgetProperty(FMSUtilityWindow2, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)

        # Entry Index
        self.GetEntryIndexButton = xp.createWidget(x + 20, y - 40, x + 110, y - 62,
                                                   1, " Get Entry Index", 0, self.FMSUtilityWidget,
                                                   xp.WidgetClass_Button)

        xp.setWidgetProperty(self.GetEntryIndexButton, xp.Property_ButtonType, xp.PushButton)

        self.EntryIndexEdit = xp.createWidget(x + 120, y - 40, x + 150, y - 62,
                                              1, "0", 0, self.FMSUtilityWidget,
                                              xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.EntryIndexEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.EntryIndexEdit, xp.Property_Enabled, 1)

        self.SetEntryIndexButton = xp.createWidget(x + 20, y - 70, x + 110, y - 92,
                                                   1, " Set Entry Index", 0, self.FMSUtilityWidget,
                                                   xp.WidgetClass_Button)

        xp.setWidgetProperty(self.SetEntryIndexButton, xp.Property_ButtonType, xp.PushButton)

        # Destination Index
        self.GetDestinationEntryButton = xp.createWidget(x + 20, y - 100, x + 110, y - 122,
                                                         1, " Get Dest Index", 0, self.FMSUtilityWidget,
                                                         xp.WidgetClass_Button)

        xp.setWidgetProperty(self.GetDestinationEntryButton, xp.Property_ButtonType, xp.PushButton)

        self.DestinationEntryIndexEdit = xp.createWidget(x + 120, y - 100, x + 150, y - 122,
                                                         1, "0", 0, self.FMSUtilityWidget,
                                                         xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.DestinationEntryIndexEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.DestinationEntryIndexEdit, xp.Property_Enabled, 1)

        self.SetDestinationEntryButton = xp.createWidget(x + 20, y - 130, x + 110, y - 152,
                                                         1, " Set Dest Index", 0, self.FMSUtilityWidget,
                                                         xp.WidgetClass_Button)

        xp.setWidgetProperty(self.SetDestinationEntryButton, xp.Property_ButtonType, xp.PushButton)

        # Number of Entries
        self.GetNumberOfEntriesButton = xp.createWidget(x + 20, y - 160, x + 110, y - 182,
                                                        1, " Get No. Entries", 0, self.FMSUtilityWidget,
                                                        xp.WidgetClass_Button)

        xp.setWidgetProperty(self.GetNumberOfEntriesButton, xp.Property_ButtonType, xp.PushButton)

        self.GetNumberOfEntriesText = xp.createWidget(x + 120, y - 160, x + 150, y - 182,
                                                      1, "", 0, self.FMSUtilityWidget,
                                                      xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.GetNumberOfEntriesText, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.GetNumberOfEntriesText, xp.Property_Enabled, 0)

        # Clear Entry
        self.ClearEntryButton = xp.createWidget(x + 20, y - 190, x + 110, y - 212,
                                                1, " Clear Entry", 0, self.FMSUtilityWidget,
                                                xp.WidgetClass_Button)

        xp.setWidgetProperty(self.ClearEntryButton, xp.Property_ButtonType, xp.PushButton)

        # Index (Segment - 1)
        IndexCaption = xp.createWidget(x + 180, y - 40, x + 230, y - 62,
                                       1, "Index", 0, self.FMSUtilityWidget,
                                       xp.WidgetClass_Caption)

        self.IndexEdit = xp.createWidget(x + 240, y - 40, x + 290, y - 62,
                                         1, "", 0, self.FMSUtilityWidget,
                                         xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.IndexEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.IndexEdit, xp.Property_Enabled, 1)

        SegmentCaption = xp.createWidget(x + 300, y - 40, x + 350, y - 62,
                                         1, "Segment", 0, self.FMSUtilityWidget,
                                         xp.WidgetClass_Caption)

        self.SegmentCaption2 = xp.createWidget(x + 360, y - 40, x + 410, y - 62,
                                               1, "", 0, self.FMSUtilityWidget,
                                               xp.WidgetClass_Caption)

        # Airport ID
        AirportIDCaption = xp.createWidget(x + 180, y - 70, x + 230, y - 92,
                                           1, "Airport ID", 0, self.FMSUtilityWidget,
                                           xp.WidgetClass_Caption)

        self.AirportIDEdit = xp.createWidget(x + 240, y - 70, x + 290, y - 92,
                                             1, "----", 0, self.FMSUtilityWidget,
                                             xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.AirportIDEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.AirportIDEdit, xp.Property_Enabled, 1)

        # Altitude
        AltitudeCaption = xp.createWidget(x + 180, y - 100, x + 230, y - 122,
                                          1, "Altitude", 0, self.FMSUtilityWidget,
                                          xp.WidgetClass_Caption)

        self.AltitudeEdit = xp.createWidget(x + 240, y - 100, x + 290, y - 122,
                                            1, "0", 0, self.FMSUtilityWidget,
                                            xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.AltitudeEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.AltitudeEdit, xp.Property_Enabled, 1)

        # Nav Type
        NavTypeCaption = xp.createWidget(x + 180, y - 130, x + 230, y - 152,
                                         1, "Nav Type", 0, self.FMSUtilityWidget,
                                         xp.WidgetClass_Caption)

        Buffer = "%s" % (self.NavTypeLookup[0][0])
        self.NavTypeEdit = xp.createWidget(x + 240, y - 130, x + 340, y - 152,
                                           1, Buffer, 0, self.FMSUtilityWidget,
                                           xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.NavTypeEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.NavTypeEdit, xp.Property_Enabled, 0)

        # Used for selecting Nav Type
        self.UpArrow = xp.createWidget(x + 340, y - 130, x + 362, y - 141,
                                       1, "", 0, self.FMSUtilityWidget,
                                       xp.WidgetClass_Button)

        xp.setWidgetProperty(self.UpArrow, xp.Property_ButtonType, xp.LittleUpArrow)

        # Used for selecting Nav Type
        self.DownArrow = xp.createWidget(x + 340, y - 141, x + 362, y - 152,
                                         1, "", 0, self.FMSUtilityWidget,
                                         xp.WidgetClass_Button)

        xp.setWidgetProperty(self.DownArrow, xp.Property_ButtonType, xp.LittleDownArrow)

        self.NavTypeText = xp.createWidget(x + 362, y - 130, x + 400, y - 152,
                                           1, "0", 0, self.FMSUtilityWidget,
                                           xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.NavTypeText, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.NavTypeText, xp.Property_Enabled, 0)

        # Get FMS Entry Info
        self.GetFMSEntryButton = xp.createWidget(x + 180, y - 160, x + 270, y - 182,
                                                 1, " Get FMS Entry", 0, self.FMSUtilityWidget,
                                                 xp.WidgetClass_Button)

        xp.setWidgetProperty(self.GetFMSEntryButton, xp.Property_ButtonType, xp.PushButton)

        # Set FMS Entry Info
        self.SetFMSEntryButton = xp.createWidget(x + 280, y - 160, x + 370, y - 182,
                                                 1, " Set FMS Entry", 0, self.FMSUtilityWidget,
                                                 xp.WidgetClass_Button)

        xp.setWidgetProperty(self.SetFMSEntryButton, xp.Property_ButtonType, xp.PushButton)

        # Lat / Lon
        LatCaption = xp.createWidget(x + 180, y - 190, x + 230, y - 212,
                                     1, "Latitude", 0, self.FMSUtilityWidget,
                                     xp.WidgetClass_Caption)

        self.LatEdit = xp.createWidget(x + 240, y - 190, x + 310, y - 212,
                                       1, "0", 0, self.FMSUtilityWidget,
                                       xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.LatEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.LatEdit, xp.Property_Enabled, 1)

        LonCaption = xp.createWidget(x + 180, y - 220, x + 230, y - 242,
                                     1, "Longitude", 0, self.FMSUtilityWidget,
                                     xp.WidgetClass_Caption)

        self.LonEdit = xp.createWidget(x + 240, y - 220, x + 310, y - 242,
                                       1, "0", 0, self.FMSUtilityWidget,
                                       xp.WidgetClass_TextField)

        xp.setWidgetProperty(self.LonEdit, xp.Property_TextFieldType, xp.TextEntryField)
        xp.setWidgetProperty(self.LonEdit, xp.Property_Enabled, 1)

        self.SetLatLonButton = xp.createWidget(x + 180, y - 250, x + 270, y - 272,
                                               1, " Set Lat/Lon", 0, self.FMSUtilityWidget,
                                               xp.WidgetClass_Button)

        xp.setWidgetProperty(self.SetLatLonButton, xp.Property_ButtonType, xp.PushButton)

        # Register our widget handler
        self.FMSUtilityHandlerCB = self.FMSUtilityHandler
        xp.addWidgetCallback(self.FMSUtilityWidget, self.FMSUtilityHandlerCB)

    def FMSUtilityHandler(self, inMessage, inWidget, inParam1, inParam2):
        if (inMessage == xp.Message_CloseButtonPushed):
            if (self.MenuItem1 == 1):
                xp.hideWidget(self.FMSUtilityWidget)
            return 1

        # Handle any button pushes
        if (inMessage == xp.Msg_PushButtonPressed):
            # Most of these handlers get a value.
            # It then has to be converted to a string.
            # This is because "xp.setWidgetDescriptor" expects a string as its second parameter.
            if (inParam1 == self.ClearEntryButton):  # "Clear Entry -- removes line from FMS -- the line indicated by "Get Entry Index"
                xp.clearFMSEntry(xp.getDisplayedFMSEntry())
                return 1

            if (inParam1 == self.GetEntryIndexButton):
                # (Note in XP 11.55, this appears to always be zero)
                Index = xp.getDisplayedFMSEntry()
                xp.setWidgetDescriptor(self.EntryIndexEdit, str(Index))
                return 1

            if (inParam1 == self.SetEntryIndexButton):
                Buffer = xp.getWidgetDescriptor(self.EntryIndexEdit)
                Index = int(Buffer)
                xp.setDisplayedFMSEntry(Index)
                # (Note in XP 11.55, this does not appear to do anything)
                return 1

            if (inParam1 == self.GetDestinationEntryButton):
                Index = xp.getDestinationFMSEntry()
                xp.setWidgetDescriptor(self.DestinationEntryIndexEdit, str(Index))
                return 1

            if (inParam1 == self.SetDestinationEntryButton):
                Buffer = xp.getWidgetDescriptor(self.DestinationEntryIndexEdit)
                Index = int(Buffer)
                xp.setDestinationFMSEntry(Index)
                return 1

            if (inParam1 == self.GetNumberOfEntriesButton):
                Count = xp.countFMSEntries()
                xp.setWidgetDescriptor(self.GetNumberOfEntriesText, str(Count))
                return 1

            if (inParam1 == self.GetFMSEntryButton):

                # Instead of using getDisplayedFMSEntry(), as that appears to always
                # return 0 and doesn't appear to be changeable by setDisplayedFMSEntry()
                # We'll use the value displayed in IndexEdit, as that's changeable by the user
                #
                # Index = xp.getDisplayedFMSEntry()
                #
                Index = int(xp.getWidgetDescriptor(self.IndexEdit))

                fmsEntryInfo = xp.getFMSEntryInfo(Index)
                xp.setWidgetDescriptor(self.IndexEdit, str(Index))
                xp.setWidgetDescriptor(self.SegmentCaption2, str(Index + 1))

                if fmsEntryInfo.type == xp.Nav_LatLon:
                    xp.setWidgetDescriptor(self.AirportIDEdit, "----")
                else:
                    xp.setWidgetDescriptor(self.AirportIDEdit, str(fmsEntryInfo.navAidID))

                xp.setWidgetDescriptor(self.AltitudeEdit, str(fmsEntryInfo.altitude))
                xp.setWidgetDescriptor(self.NavTypeEdit, self.NavTypeLookup[self.GetCBIndex(fmsEntryInfo.type)][0])
                Buffer = "%d" % (self.NavTypeLookup[self.GetCBIndex(fmsEntryInfo.type)][1])
                xp.setWidgetDescriptor(self.NavTypeText, Buffer)
                xp.setWidgetDescriptor(self.LatEdit, str(fmsEntryInfo.lat))
                xp.setWidgetDescriptor(self.LonEdit, str(fmsEntryInfo.lon))
                return 1

            if (inParam1 == self.SetFMSEntryButton):
                Buffer = xp.getWidgetDescriptor(self.IndexEdit)
                Index = int(Buffer)
                xp.setWidgetDescriptor(self.SegmentCaption2, str(Index + 1))
                Buffer = xp.getWidgetDescriptor(self.AltitudeEdit)
                Altitude = int(Buffer)
                Buffer = xp.getWidgetDescriptor(self.NavTypeText)
                NavType = int(Buffer)
                Buffer = xp.getWidgetDescriptor(self.AirportIDEdit)
                IDFragment = Buffer
                xp.setFMSEntryInfo(Index, xp.findNavAid(None, IDFragment, None, None, None, NavType), Altitude)
                return 1

            if (inParam1 == self.SetLatLonButton):
                Buffer = xp.getWidgetDescriptor(self.IndexEdit)
                Index = int(Buffer)
                xp.setWidgetDescriptor(self.SegmentCaption2, str(Index + 1))
                Buffer = xp.getWidgetDescriptor(self.AltitudeEdit)
                Altitude = int(Buffer)
                Buffer = xp.getWidgetDescriptor(self.LatEdit)
                Lat = float(Buffer)
                Buffer = xp.getWidgetDescriptor(self.LonEdit)
                Lon = float(Buffer)
                xp.setFMSEntryLatLon(Index, Lat, Lon, Altitude)
                return 1

            # Up Arrow is used to modify the NavTypeLookup Array Index
            if (inParam1 == self.UpArrow):
                self.NavTypeLinePosition -= 1
                if (self.NavTypeLinePosition < 0):
                    self.NavTypeLinePosition = self.MAX_NAV_TYPES - 1
                xp.setWidgetDescriptor(self.NavTypeEdit, self.NavTypeLookup[self.NavTypeLinePosition][0])
                xp.setWidgetDescriptor(self.NavTypeText, str(self.NavTypeLookup[self.NavTypeLinePosition][1]))
                return 1

            # Down Arrow is used to modify the NavTypeLookup Array Index
            if (inParam1 == self.DownArrow):
                self.NavTypeLinePosition += 1
                if (self.NavTypeLinePosition > self.MAX_NAV_TYPES - 1):
                    self.NavTypeLinePosition = 0
                xp.setWidgetDescriptor(self.NavTypeEdit, self.NavTypeLookup[self.NavTypeLinePosition][0])
                xp.setWidgetDescriptor(self.NavTypeText, str(self.NavTypeLookup[self.NavTypeLinePosition][1]))
                return 1

        return 0

    # This function takes an xp.NavType and
    # returns the index into the NavTypeLookup array.
    # We can then use that index to access the description or enum.
    def GetCBIndex(self, Type):
        CBIndex = 0
        Index = 0

        while Index < self.MAX_NAV_TYPES:
            if (self.NavTypeLookup[Index][1] == Type):
                CBIndex = Index
                break

            Index += 1

        return CBIndex
