from XPPython3 import xp

# ORIGINAL IN C:
#   https://developer.x-plane.com/code-sample/coachmarks/
# This example plugin demonstrates how to use a 2-d drawing callback to draw
# to the screen in a way that matches the 3-d coordinate system.  Add-ons that
# need to add 3-d labels, coach marks, or other non-3d graphics that "match"
# the real world can use this technique to draw on with Metal and Vulkan.

# Datarefs for the aircraft position.
s_pos_x = None
s_pos_y = None
s_pos_z = None

# Transform matrices - we will use these to figure out where we shuold should have drawn.
s_matrix_wrl = None
s_matrix_proj = None
s_screen_width = None
s_screen_height = None


# 4x4 matrix transform of an XYZW coordinate - this matches OpenGL matrix conventions.
def mult_matrix_vec(dst, m, v):
    dst[0] = v[0] * m[0] + v[1] * m[4] + v[2] * m[8] + v[3] * m[12]
    dst[1] = v[0] * m[1] + v[1] * m[5] + v[2] * m[9] + v[3] * m[13]
    dst[2] = v[0] * m[2] + v[1] * m[6] + v[2] * m[10] + v[3] * m[14]
    dst[3] = v[0] * m[3] + v[1] * m[7] + v[2] * m[11] + v[3] * m[15]


# This drawing callback will draw a label to the screen where the

def DrawCallback1(inPhase, inIsBefore, inRefcon):
    # Read the ACF's OpengL coordinates
    acf_wrl = [xp.getDataf(s_pos_x),
               xp.getDataf(s_pos_y),
               xp.getDataf(s_pos_z),
               1.0]

    mv:list[float] = []
    proj:list[float] = []

    # Read the model view and projection matrices from this frame
    xp.getDatavf(s_matrix_wrl, mv, 0, 16)
    xp.getDatavf(s_matrix_proj, proj, 0, 16)

    acf_eye = [0.0, ] * 4
    acf_ndc = [0.0, ] * 4

    # Simulate the OpenGL transformation to get screen coordinates.
    mult_matrix_vec(acf_eye, mv, acf_wrl)
    mult_matrix_vec(acf_ndc, proj, acf_eye)

    acf_ndc[3] = 1.0 / acf_ndc[3]
    acf_ndc[0] *= acf_ndc[3]
    acf_ndc[1] *= acf_ndc[3]
    acf_ndc[2] *= acf_ndc[3]

    screen_w = xp.getDatai(s_screen_width)
    screen_h = xp.getDatai(s_screen_height)

    final_x = int(screen_w * (acf_ndc[0] * 0.5 + 0.5))
    final_y = int(screen_h * (acf_ndc[1] * 0.5 + 0.5))

    # Now we have something in screen coordinates, which we can then draw a label on.

    xp.drawTranslucentDarkBox(final_x - 5, final_y + 10, final_x + 100, final_y - 10)

    colWHT = [1.0, ] * 3
    xp.drawString(colWHT, final_x, final_y, "TEST STRING 1", None, xp.Font_Basic)

    return 1


class PythonInterface:
    def XPluginStart(self):

        global s_pos_x, s_pos_y, s_pos_z, s_matrix_wrl, s_matrix_proj, s_screen_width, s_screen_height
        xp.registerDrawCallback(DrawCallback1, xp.Phase_Window, 0, None)

        s_pos_x = xp.findDataRef("sim/flightmodel/position/local_x")
        s_pos_y = xp.findDataRef("sim/flightmodel/position/local_y")
        s_pos_z = xp.findDataRef("sim/flightmodel/position/local_z")

        # These datarefs are valid to read from a 2-d drawing callback and describe the state
        # of the underlying 3-d drawing environment the 2-d drawing is layered on top of.
        s_matrix_wrl = xp.findDataRef("sim/graphics/view/world_matrix")
        s_matrix_proj = xp.findDataRef("sim/graphics/view/projection_matrix_3d")

        # This describes the size of the current monitor at the time we draw.
        s_screen_width = xp.findDataRef("sim/graphics/view/window_width")
        s_screen_height = xp.findDataRef("sim/graphics/view/window_height")

        outName = "Example label drawing v1.0"
        outSig = "com.laminar.example_label_drawing"
        outDesc = "A plugin that shows how to draw a 3-d-referenced label in 2-d"
        return outName, outSig, outDesc

    def XPluginEnable(self):
        return 1

    def XPluginStop(self):
        return

    def XPluginDisable(self):
        return

    def XPluginReceiveMessage(self, *args, **kwargs):
        return
