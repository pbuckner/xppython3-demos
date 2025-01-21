from typing import Self, Any
from dataclasses import dataclass
import random
import datetime
from XPPython3 import xp
from XPPython3.utils import commands
from XPPython3.utils.easy_python import EasyPython
from XPPython3 import xpgl
from XPPython3.xp_typing import XPLMAvionicsID, XPLMCursorStatus
from XPPython3.xpgl import Colors
from OpenGL import GL


# Plug demonstrates Custom Avionics draw routines, including
# "screensaver"-type XPPython3 logo bouncing around
# It differs from PI_Avionics1_Draw.py by setting a different
# custom_device id ("avnwx.avionics.device2") and being configured
# using EasyPython
# having a grey bezel
# Draw using maskContext() and graphicsContext()


@dataclass
class Size:
    width: float
    height: float


class PythonInterface(EasyPython):
    def __init__(self: Self) -> None:
        self.duration = 0.0
        self.customAvionicsId: XPLMAvionicsID = None
        self.trackLoop = None
        self.Textures: dict = {}
        self.Fonts: dict = {}
        self.panel: dict = {'screen': Size(500, 500),
                            'bezel': Size(530, 530),
                            'offset': (15, 15)}
        self.logo_x = 0.
        self.logo_y = 0.
        self.logo_x_speed = .5
        self.logo_y_speed = .5
        self.report = 0
        super().__init__()

    def onStart(self: Self) -> None:
        self.duration = 0.0
        try:
            self.Textures['logo'] = xpgl.loadImage('Resources/plugins/XPPython3/xppython3.png')
        except Exception as e:  # pylint: disable=broad-exception-caught
            xp.log(f"Failed to load xppython3.png image: {e}")
        try:
            self.Textures['star'] = xpgl.loadImage('Resources/plugins/PythonPlugins/redStar.png')
        except Exception as e:  # pylint: disable=broad-exception-caught
            xp.log(f"Failed to load redStar.png image: {e}")

        self.create()

    def do_draw(self: Self, i: int, f: float) -> None:
        xp.log(f"do_draw ({i=}, {f=})")
        self.duration = f
        xp.avionicsNeedsDrawing(self.customAvionicsId)

    def onEnable(self: Self) -> int:
        font = "/System/Library/Fonts/Helvetica.ttc"
        self.Fonts['Helvetica'] = xpgl.loadFont(font, 18)
        self.Fonts['GLUT_Helvetica'] = xpgl.loadFont("HELVETICA", 18)
        self.Fonts['XP_Prop'] = xpgl.loadFont(xp.Font_Proportional, 18)

        commands.create_command('mycommand', 'test command', self.do_draw)

        xp.setAvionicsPopupVisible(self.customAvionicsId)
        # timers.run_at_interval(self.timer, 5)
        return 1

    def onStop(self: Self) -> None:
        # xp.log(f"Av2 {xpgl.Pattern=}, Texutres are: {xpgl.Textures}, {xpgl.XPGL_Texture_ID=}, {xpgl.Smooth_Lines=}")
        if self.customAvionicsId:
            xp.destroyAvionics(self.customAvionicsId)
            self.customAvionicsId = None

        if self.trackLoop:
            xp.destroyFlightLoop(self.trackLoop)
            self.trackLoop = None

    def create(self: Self) -> None:
        # createAvionicsEx (i.e., "custom" avionics) use a string deviceID
        # registerAvionicsCallbacksEx(i.e., "builtin" avionics use a predefined enum (int) deviceID
        # In this example, we're creating custom avionics & therefore use createAvionicsEx() and a string ID.
        self.customAvionicsId = xp.createAvionicsEx(screenWidth=self.panel['screen'].width,
                                                    screenHeight=self.panel['screen'].height,
                                                    bezelWidth=self.panel['bezel'].width,
                                                    bezelHeight=self.panel['bezel'].height,
                                                    screenOffsetX=self.panel['offset'][0],
                                                    screenOffsetY=self.panel['offset'][1],
                                                    drawOnDemand=0,
                                                    screenDraw=self.draw,
                                                    bezelDraw=self.bezelDraw,
                                                    screenTouch=self.screenTouch,
                                                    screenRightTouch=self.screenRightTouch,
                                                    screenScroll=self.screenScroll,
                                                    screenCursor=self.screenCursor,
                                                    bezelCursor=self.bezelCursor,
                                                    bezelScroll=self.bezelScroll,
                                                    bezelClick=self.bezelClick,
                                                    bezelRightClick=self.bezelRightClick,
                                                    keyboard=self.keyboard,
                                                    brightness=self.brightness,
                                                    refCon=self.panel,
                                                    deviceID="avnwx.avionics.device2",
                                                    deviceName="My Fine Device"
                                                )

    def brightness(self: Self, rheo: float, ambient: float, _bus: float, _refCon: float) -> float:
        # xp.log(f"{rheo=} {ambient=}, {bus=}, {ambient * rheo}")
        return ambient * rheo

    def bezelDraw(self: Self, _r: float, _g: float, _b: float, refcon: Any) -> None:
        xp.setGraphicsState(depthWriting=1, alphaBlending=1)
        b = refcon['bezel']
        s = refcon['screen']
        o = refcon['offset']
        xpgl.drawPolygon([(0, 0), (0, b.height), (b.width, b.height), (b.width, 0),],
                         thickness=3, isFilled=True,
                         color=Colors['gray20'])
        # draw background of _screen_ to be all black
        xpgl.drawPolygon([(o[0], o[1]),
                          (o[0], o[1] + s.height),
                          (o[0] + s.width, o[1] + s.height),
                          (o[0] + s.width, o[1]),], isFilled=True, color=Colors['black'])

        self.Fonts['XP_Prop'].draw_text(10, 0,
                                        f"1) {str(datetime.datetime.now())} {xp.getCycleNumber()=} {self.duration or 0.=:.3f}")

    def draw(self: Self, refcon: Any) -> None:

        screen = refcon['screen']

        xpgl.clear()
        self.Fonts['XP_Prop'].draw_text(10, 10,
                                        f"1) {str(datetime.datetime.now())} {xp.getCycleNumber()=} {self.duration or 0.=:.3f}")

        size_w = 140
        size_y = 88

        xpgl.drawText(self.Fonts['XP_Prop'], 240, 200, 'Prop Right', alignment='r', color=Colors['orange'])
        # self.Fonts['XP_Prop'].draw_text(       240, 200, "Prop Right", alignment='r', color=Colors['orange'])
        xpgl.drawText(self.Fonts['XP_Prop'], 240, 220, "Prop Center", alignment='c', color=Colors['orange'])
        xpgl.drawText(self.Fonts['Helvetica'], 125, 180, "TTC Left", color=Colors['green'])
        xpgl.drawText(self.Fonts['Helvetica'], 125, 200, "TTC Right", alignment='r', color=Colors['green'])
        xpgl.drawText(self.Fonts['Helvetica'], 125, 220, "TTC Center", alignment='C', color=Colors['green'])
        xpgl.drawText(self.Fonts['GLUT_Helvetica'], 400, 220, "GLUT Center", alignment='C', color=Colors['red'])
        xpgl.drawText(self.Fonts['GLUT_Helvetica'], 400, 200, "GLUT Right", alignment='r', color=Colors['red'])
        xpgl.drawText(self.Fonts['GLUT_Helvetica'], 400, 180, "GLUT Left", alignment='l', color=Colors['red'])

        self.logo_x += self.logo_x_speed
        self.logo_y += self.logo_y_speed
        while (self.logo_x >= screen.width - (size_w + 1)
               or self.logo_x <= 0
               or self.logo_y >= screen.height - (size_y + 1)
               or self.logo_y <= 0):
            self.logo_x_speed = (-1 if self.logo_x_speed > 0 else 1) * random.gauss(.5, .2)
            self.logo_y_speed = (-1 if self.logo_y_speed > 0 else 1) * random.gauss(.5, .2)
            self.logo_x += self.logo_x_speed
            self.logo_y += self.logo_y_speed

        xpgl.setLinePattern(0x5555)
        xpgl.drawLine(0, 0, screen.width, screen.height, color=Colors['pink'], thickness=5)
        xpgl.setLinePattern(0xffff)
        if 'logo' in self.Textures:
            xpgl.drawTexture(self.Textures['logo'], self.logo_x, self.logo_y, size_w, size_y, color=Colors['white'])
        self.Fonts['XP_Prop'].draw_text(240, 180, "Prop Left", color=Colors['orange'])

        with xpgl.maskContext():
            # draw shape of stencil vvvvvvvvv
            with xpgl.graphicsContext():
                xpgl.setRotateTransform(xp.getCycleNumber() % 360, screen.width / 2, 190)
                xpgl.drawTriangle(180, 165,
                                  screen.width / 2, screen.height - 220,
                                  screen.width - 180, 165, Colors['green'])
            # ^^^^^^^

            xpgl.drawUnderMask(stencil=False)
            # # end definition of stencil vvvvvvvvvv

            xpgl.drawTriangle(100, 100, screen.width / 2, screen.height - 100, screen.width - 100, 100, Colors['green'])

        with xpgl.graphicsContext():
            xpgl.setRotateTransform(90, screen.width / 2, screen.height / 2)
            xpgl.drawArc(screen.width / 2, screen.height / 2,
                         radius_inner=10, radius_outer=20,
                         start_angle=0, arc_angle=180, color=Colors['red'])

        if 'star' in self.Textures:
            xpgl.drawTexture(self.Textures['star'], 50, 50, 80, 80)

        GL.glFlush()

    def screenScroll(self: Self, x: int, y: int, wheel: int, clicks: int, refcon: Any) -> int:
        xp.log(f"screenScroll {(x, y)=} {wheel=} {clicks=} {refcon=}")
        return 0

    def bezelScroll(self: Self, x: int, y: int, wheel: int, clicks: int, refcon: Any) -> int:
        xp.log(f"bezelScroll {(x, y)=} {wheel=} {clicks=} {refcon=}")
        return 0

    def screenTouch(self: Self, x: int, y: int, mouse: int, refcon: Any) -> int:
        xp.log(f"screenTouch {(x, y)=} {mouse=} {refcon=}")
        return 0

    def screenRightTouch(self: Self, x: int, y: int, mouse: int, refcon: Any) -> int:
        xp.log(f"screenRightTouch {(x, y)=} {mouse=} {refcon=}")
        return 0

    def bezelClick(self: Self, x: int, y: int, mouse: int, refcon: Any) -> int:
        xp.log(f"bezelClick {(x, y)=} {mouse=} {refcon=}")
        return 0

    def bezelRightClick(self: Self, x: int, y: int, mouse: int, refcon: Any) -> int:
        xp.log(f"bezelRightClick {(x, y)=} {mouse=} {refcon=}")
        return 0

    def screenCursor(self: Self, x: int, y: int, _refcon: Any) -> XPLMCursorStatus:
        return xp.CursorHidden if x > y else xp.CursorArrow

    def bezelCursor(self: Self, x: int, y: int, _refcon: Any) -> XPLMCursorStatus:
        return xp.CursorHidden if x > y else xp.CursorArrow

    def keyboard(self: Self, inKey: int, inFlags: int, inVirtualKey: int, refcon: Any, losingFocus: int) -> int:
        xp.log(f"keyboard {inKey=}, {inFlags=} {inVirtualKey=}, {refcon=}, {losingFocus=}")
        if inVirtualKey == xp.VK_A:
            return 1  # if 'a' then ignore it!
        return 0
