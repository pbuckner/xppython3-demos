from typing import Any
from XPPython3 import xp


class PythonInterface:
    def __init__(self):
        self.Name = "TabbedWidget v1.0"
        self.Sig = "TabbedWidget.demos.xppython3"
        self.Desc = "A test plugin for Tabbed panels using XPPython3."
        self.myWidgetWindow = None
        self.activeTab = None

    def XPluginStart(self):
        return self.Name, self.Sig, self.Desc

    def XPluginEnable(self):
        self.myWidgetWindow = self.createWidgetWindow()
        return 1

    def XPluginDisable(self):
        if self.myWidgetWindow:
            xp.destroyWidget(self.myWidgetWindow['widgetID'], 1)
            self.myWidgetWindow = None

    def createWidgetWindow(self):
        widgetWindow:dict[str, Any] = {'widgetID': None,  # the ID of the main window containing all other widgets
                                       'widgets': {}  # hash of all child widgets we care about
        }
        left = 100
        top = 200
        right = 600
        bottom = 50
        widgetWindow['widgetID'] = xp.createWidget(left, top, right, bottom, 1, "Tabbed, Widget Window Test",
                                                   1, 0, xp.WidgetClass_MainWindow)
        xp.addWidgetCallback(widgetWindow['widgetID'], self.mainWindowCallback)

        left_margin = 100 + 5
        top_margin = 200 - 25
        bottom_margin = 50 + 5
        right_margin = 600 - 5
        tab_width = 50
        tab_height = 15
        # Tab1 starts visible, Tab2 is not
        w = widgetWindow['widgets']
        w['tab1-button'] = xp.createWidget(left_margin, top_margin, left_margin + tab_width, top_margin - tab_height,
                                           1, "Tab1", 0, widgetWindow['widgetID'], xp.WidgetClass_Button)

        self.activeTab = w['tab1-button']
        xp.setWidgetProperty(self.activeTab, xp.Property_Hilited, 1)
        w['tabContents1'] = xp.createWidget(left_margin, top_margin - (tab_height + 5), right_margin, bottom_margin,
                                            1, "TabContents1", 0, widgetWindow['widgetID'], xp.WidgetClass_SubWindow)


        w['tab2-button'] = xp.createWidget(left_margin + tab_width, top_margin, left_margin + 2 * tab_width, top_margin - tab_height,
                                           1, "Tab2", 0, widgetWindow['widgetID'], xp.WidgetClass_Button)


        w['tabContents2'] = xp.createWidget(left_margin, top_margin - (tab_height + 5), right_margin, bottom_margin,
                                            0, "TabContents2", 0, widgetWindow['widgetID'], xp.WidgetClass_SubWindow)

        xp.addWidgetCallback(w['tabContents1'], xp.fixedLayout)
        xp.addWidgetCallback(w['tabContents2'], xp.fixedLayout)


        # Add five label / editable text fields, to each of two tabs.
        # We determine placement based on the size of the font.
        # We'll store the IDs the text fields so we can interact with them (we don't in this example)
        fontID = xp.Font_Proportional
        _w, strHeight, _ignore = xp.getFontDimensions(fontID)
        for tab in (1, 2):
            for i in range(5):
                s = f'item {tab}-{i}'
                strWidth = xp.measureString(fontID, s)
                left = 100 + 10
                top = int(top_margin - tab_height - 20 - ((strHeight + 4) * i))
                right = int(left + strWidth)
                bottom = int(top - strHeight)
                xp.createWidget(left, top, right, bottom,
                                1, s, 0, w[f'tabContents{tab}'], xp.WidgetClass_Caption)
                widget = xp.createWidget(right + 10, top, right + 100, bottom, 1, f'val {i}', 0,
                                         w[f'tabContents{tab}'],
                                         xp.WidgetClass_TextField)
            widgetWindow['widgets'][f'textfield-{tab}-{i}'] = widget

        return widgetWindow

    def mainWindowCallback(self, inMessage, inWidget, inParam1, inParam2):
        if inMessage == xp.Msg_PushButtonPressed and inParam1 in (self.myWidgetWindow['widgets']['tab1-button'],
                                                                  self.myWidgetWindow['widgets']['tab2-button']):
            xp.log(f"button pressed {inWidget}, {inParam1}, {inParam2}")
            self.activeTab = inParam1
            # Set show/hide for the proper panel
            w = self.myWidgetWindow['widgets']
            for tab in (1, 2):
                if w[f'tab{tab}-button'] == self.activeTab:
                    xp.showWidget(w[f'tabContents{tab}'])
                else:
                    xp.hideWidget(w[f'tabContents{tab}'])
            # One would think you could set Property_Hilited here, but you shouldn't:
            # a pushed button is highlighted _by_the_press_ and unhighighted when the press is complete.
            # Instead, we'll set the proper highlight during CursorAdjust below.
            return 0
        if inMessage == xp.Msg_Paint:
            return 0  # so 'draw' is called
        if inMessage == xp.Msg_CursorAdjust:
            for tab in (1, 2):
                button = self.myWidgetWindow['widgets'][f'tab{tab}-button']
                xp.setWidgetProperty(button, xp.Property_Hilited, button == self.activeTab)
            inParam2 = xp.CursorDefault
            return 1
        return 0  # forward message to "next"
