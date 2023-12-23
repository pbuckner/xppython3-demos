"""
Input / Output example
Written by Sandy Barbour - 29/02/2004
Ported to Python by Sandy Barbour - 01/05/2005

This examples shows how to get input data from Xplane.
It also shows how to control Xplane by sending output data to it.

In this case it controls N1 depending on the throttle value.

It also shows the use of Menus and Widgets.
"""

from XPPython3 import xp


class PythonInterface:
    def XPluginStart(self):
        self.Name = "InputOutput1 v1.01"
        self.Sig = "SandyBarbour.Python.InputOutput1"
        self.Desc = "A plug-in that handles data Input/Output."

        self.MAX_NUMBER_ENGINES = 8
        self.MAX_INPUT_DATA_ITEMS = 2
        self.MAX_OUTPUT_DATA_ITEMS = 1

        # Use lists for the datarefs, makes it easier to add extra datarefs
        InputDataRefDescriptions = ["sim/flightmodel/engine/ENGN_thro", "sim/aircraft/engine/acf_num_engines"]
        OutputDataRefDescriptions = ["sim/flightmodel/engine/ENGN_N1_"]
        self.DataRefDesc = ["1", "2", "3", "4", "5", "6", "7", "8"]

        # Create our menu
        Item = xp.appendMenuItem(xp.findPluginsMenu(), "Python - Input/Output 1", 0)
        self.InputOutputMenuHandlerCB = self.InputOutputMenuHandler
        self.Id = xp.createMenu("Input/Output 1", xp.findPluginsMenu(), Item, self.InputOutputMenuHandlerCB, 0)
        xp.appendMenuItem(self.Id, "Data", 1)

        # Flag to tell us if the widget is being displayed.
        self.MenuItem1 = 0

        # Get our dataref handles here
        self.InputDataRef = []
        for Item in range(self.MAX_INPUT_DATA_ITEMS):
            self.InputDataRef.append(xp.findDataRef(InputDataRefDescriptions[Item]))

        self.OutputDataRef = []
        for Item in range(self.MAX_OUTPUT_DATA_ITEMS):
            self.OutputDataRef.append(xp.findDataRef(OutputDataRefDescriptions[Item]))

        # Register our FL callbadk with initial callback freq of 1 second
        self.InputOutputLoopCB = self.InputOutputLoopCallback
        xp.registerFlightLoopCallback(self.InputOutputLoopCB, 1.0, 0)

        return self.Name, self.Sig, self.Desc

    def XPluginStop(self):
        # Unregister the callback
        xp.unregisterFlightLoopCallback(self.InputOutputLoopCB, 0)

        if self.MenuItem1 == 1:
            xp.destroyWidget(self.InputOutputWidget, 1)
            self.MenuItem1 = 0

        xp.destroyMenu(self.Id)

    def XPluginEnable(self):
        return 1

    def XPluginDisable(self):
        pass

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def InputOutputLoopCallback(self, elapsedMe, elapsedSim, counter, refcon):
        if self.MenuItem1 == 0:  # Don't process if widget not visible
            return 1.0

        # Only deal with the actual engines that we have
        self.NumberOfEngines = xp.getDatai(self.InputDataRef[1])

        # Get our throttle positions for each engine
        self.Throttle:list[float] = []
        count = xp.getDatavf(self.InputDataRef[0], self.Throttle, 0, self.NumberOfEngines)

        # Get our current N1 for each engine
        self.CurrentN1:list[float] = []
        count = xp.getDatavf(self.OutputDataRef[0], self.CurrentN1, 0, self.NumberOfEngines)

        for Item in range(self.MAX_NUMBER_ENGINES):
            xp.setWidgetDescriptor(self.InputEdit[Item], "")
            xp.setWidgetDescriptor(self.OutputEdit[Item], "")

        # Process each engine
        self.NewN1 = []
        for Item in range(self.NumberOfEngines):
            # Default to New = Current
            self.NewN1.append(self.CurrentN1[Item])

            """
            Special processing can go here depending on input value
            For this example just limit N1 to 80% if throttle > 50%
            """
            if self.Throttle[Item] > 0.5:
                if self.CurrentN1[Item] > 80.0:
                    self.NewN1[Item] = 80.0

            # This updates the first widget column with the throttle values
            xp.setWidgetDescriptor(self.InputEdit[Item], str(self.Throttle[Item]))

            # This updates the second widget column with the N1 values
            xp.setWidgetDescriptor(self.OutputEdit[Item], str(self.NewN1[Item]))

        # Set the new N1 values for each engine
        xp.setDatavf(self.OutputDataRef[0], self.NewN1, 0, self.NumberOfEngines)

        # This means call us ever 10ms.
        return 0.01

    def InputOutputMenuHandler(self, inMenuRef, inItemRef):
        # If menu selected create our widget dialog
        if inItemRef == 1:
            if self.MenuItem1 == 0:
                self.CreateInputOutputWidget(300, 550, 350, 350)
                self.MenuItem1 = 1
            else:
                if not xp.isWidgetVisible(self.InputOutputWidget):
                    xp.showWidget(self.InputOutputWidget)

    """
    This will create our widget dialog.
    I have made all child widgets relative to the input paramter.
    This makes it easy to position the dialog
    """
    def CreateInputOutputWidget(self, x, y, w, h):
        x2 = x + w
        y2 = y - h

        # Create the Main Widget window
        self.InputOutputWidget = xp.createWidget(x, y, x2, y2, 1, "Python - Input/Output Example 1 by Sandy Barbour",
                                                 1, 0, xp.WidgetClass_MainWindow)

        # Add Close Box decorations to the Main Widget
        xp.setWidgetProperty(self.InputOutputWidget, xp.Property_MainWindowHasCloseBoxes, 1)

        # Create the Sub Widget window
        InputOutputWindow = xp.createWidget(x + 50, y - 50, x2 - 50, y2 + 50, 1, "",
                                            0, self.InputOutputWidget, xp.WidgetClass_SubWindow)

        # Set the style to sub window
        xp.setWidgetProperty(InputOutputWindow, xp.Property_SubWindowType, xp.SubWindowStyle_SubWindow)

        # For each engine
        InputText = []
        self.InputEdit = []
        self.OutputEdit = []
        for Item in range(self.MAX_NUMBER_ENGINES):
            # Create a text widget
            InputText.append(xp.createWidget(x + 60, y - (60 + (Item * 30)), x + 90, y - (82 + (Item * 30)), 1,
                                             self.DataRefDesc[Item], 0, self.InputOutputWidget, xp.WidgetClass_Caption))

            # Create an edit widget for the throttle value
            self.InputEdit.append(xp.createWidget(x + 100, y - (60 + (Item * 30)), x + 180, y - (82 + (Item * 30)), 1,
                                                  "", 0, self.InputOutputWidget, xp.WidgetClass_TextField))

            # Set it to be text entry
            xp.setWidgetProperty(self.InputEdit[Item], xp.Property_TextFieldType, xp.TextEntryField)

            # Create an edit widget for the N1 value
            self.OutputEdit.append(xp.createWidget(x + 190, y - (60 + (Item * 30)), x + 270, y - (82 + (Item * 30)), 1,
                                                   "", 0, self.InputOutputWidget, xp.WidgetClass_TextField))

            # Set it to be text entry
            xp.setWidgetProperty(self.OutputEdit[Item], xp.Property_TextFieldType, xp.TextEntryField)

        # Register our widget handler
        self.InputOutputHandlerCB = self.InputOutputHandler
        xp.addWidgetCallback(self.InputOutputWidget, self.InputOutputHandlerCB)

    def InputOutputHandler(self, inMessage, inWidget, inParam1, inParam2):
        if inMessage == xp.Message_CloseButtonPushed:
            if self.MenuItem1 == 1:
                xp.hideWidget(self.InputOutputWidget)
            return 1

        return 0
