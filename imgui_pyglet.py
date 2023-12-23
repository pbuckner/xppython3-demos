# -*- coding: utf-8 -*-
from __future__ import absolute_import

import pyglet  # type:ignore
from pyglet import gl
from pyimgui_demowindow import show_demo_window

import imgui
# Note that we could explicitly choose to use PygletFixedPipelineRenderer
# or PygletProgrammablePipelineRenderer, but create_renderer handles the
# version checking for us.
from imgui.integrations.pyglet import create_renderer

def update(dt):
    imgui.new_frame()
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File", True):

            clicked_quit, selected_quit = imgui.menu_item(
                "Quit", 'Cmd+Q', False, True
            )

            if clicked_quit:
                exit(1)

            imgui.end_menu()
        imgui.end_main_menu_bar()

    #########################
    # Here are three sets of things to draw -- comment in/out as desired
    # 1) Simple little window
    #
    # imgui.begin("Custom window", True)
    # imgui.text("Bar")
    # imgui.text_colored("Eggs", 0.2, 1., 0.)
    # imgui.text_ansi("B\033[31marA\033[mnsi ")
    # imgui.text_ansi_colored("Eg\033[31mgAn\033[msi ", 0.2, 1., 0.)
    # imgui.end()

    # 2) c++ version of show_test_window()
    #    which demonstrates what imgui _can_ do (imgui.show_demo_window() is python code
    #    which simply calls the C++ coded show_demo_window)
    #
    # imgui.show_demo_window()

    # 3) python version of show_demo_window()
    #    which is work-in-progress, trying to replicate the C++ behaviour by
    #    writing the python equivalent (show_demo_window() is python code, calling
    #    lower-level pyimgui python code which in turn calls the C++ code)
    #
    #    This interface shows what low-level calls have been implemented in python
    #    and therefore _should_ be available with X-Plane.
    show_demo_window()


def draw_one(dt, window_info):
    imgui.set_current_context(window_info['context'])
    io = imgui.get_io()
    io.display_size = window_info['window'].get_size()
    update(dt)
    window_info['window'].clear()
    imgui.render()
    window_info['impl'].render(imgui.get_draw_data())


if __name__ == "__main__":
    window = pyglet.window.Window(width=1280, height=720, resizable=True)
    gl.glClearColor(1, 1, 1, 1)
    context = imgui.create_context()
    imgui.set_current_context(context)
    impl = create_renderer(window)
    window_info = {'context': context,
                   'impl': impl,
                   'window': window}

    pyglet.clock.schedule_interval(lambda dt: draw_one(dt, window_info), 1/120.)
    pyglet.app.run()
    impl.shutdown()
