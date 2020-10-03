#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.

import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from . import draw
from .draw import RenderOptions

class PyBootchartWidget(Gtk.DrawingArea):
    # last mouse event state
    last_mx = None
    last_my = None
    last_b = None
    line_x = -1

    def __init__(self, trace, options, xscale):
        Gtk.DrawingArea.__init__(self)

        self.trace = trace
        self.options = options

        self.set_can_focus(True)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.connect("button-press-event", self.on_area_button_press)
        self.connect("button-release-event", self.on_area_button_release)
        self.connect("motion-notify-event", self.on_area_motion_notify)
        self.connect("scroll-event", self.on_area_scroll_event)
        self.connect('key-press-event', self.on_key_press_event)

        self.zoom_ratio = 1.0
        self.xscale = xscale
        self.original_scale = xscale

        self.chart_width, self.chart_height = draw.extents(self.options, self.xscale, self.trace)

        # scrollable properties
        self.hadj = Gtk.Adjustment(0,0,self.chart_width)
        self.vadj = Gtk.Adjustment(0,0,self.chart_height)

    def do_draw(self, cr):
        cr.set_source_rgba(*draw.WHITE)
        cr.scale(self.zoom_ratio, self.zoom_ratio)
        draw.render(cr, self.options, self.xscale, self.trace)
        # draw vertical line
        if self.line_x>=0:
            cr.set_source_rgba(*self.VLINE_MARK_COLOR)
            cr.set_dash([6,2], 0)
            cr.set_line_width(1)
            cr.move_to(self.line_x*self.xscale+draw.off_x, 0)
            cr.line_to(self.line_x*self.xscale+draw.off_x, self.chart_height)
            cr.stroke()

    def do_get_preferred_width(self):
        width = self.chart_width * self.zoom_ratio
        return (width, width)

    def do_get_preferred_height(self):
        height = self.chart_height * self.zoom_ratio
        return (height, height)

    def relativePos(self, adj):
        high = (adj.get_upper() - adj.get_lower());
        if high != 0:
            return (adj.get_value() + adj.get_page_size()/2 - adj.get_lower()) / high
        else:
            return 0

    def setRelativePos(self, adj, x, w):
        adj.set_upper( w )
        adj.set_value( x * (adj.get_upper() - adj.get_lower()) + adj.get_lower() - adj.get_page_size()/2 )

    def zoom_image (self, zoom_ratio, xscale):
        offset_x = self.relativePos(self.hadj)
        offset_y = self.relativePos(self.vadj)
        self.zoom_ratio = zoom_ratio
        self.xscale = xscale
        self.chart_width, self.chart_height = draw.extents(self.options, self.xscale, self.trace)
        self.setRelativePos(self.hadj, offset_x, self.chart_width * self.zoom_ratio)
        self.setRelativePos(self.vadj, offset_y, self.chart_height * self.zoom_ratio)
        self.queue_resize()

    def offset_image(self, dx, dy):
        self.hadj.set_value(self.hadj.get_value()+dx)
        self.vadj.set_value(self.vadj.get_value()+dy)
        self.queue_draw()

    ZOOM_INCREMENT = 1.25
    ZOOM_MOUSE_INCREMENT = 1.0025
    POS_INCREMENT = 100
    SCALE_INCREMENT = 1.5
    VLINE_MARK_COLOR = (0.0, 0.5, 0.0, 1.0)

    def on_expand(self, action):
        self.zoom_image(self.zoom_ratio, self.xscale * self.SCALE_INCREMENT)

    def on_contract(self, action):
        self.zoom_image(self.zoom_ratio, self.xscale / self.SCALE_INCREMENT)

    def on_zoom_in(self, action):
        self.zoom_image(self.zoom_ratio * self.ZOOM_INCREMENT, self.xscale)

    def on_zoom_out(self, action):
        self.zoom_image(self.zoom_ratio / self.ZOOM_INCREMENT, self.xscale)

    def on_zoom_fit(self, action):
        self.xscale=self.original_scale
        self.chart_width, self.chart_height = draw.extents(self.options, self.xscale, self.trace)
        self.zoom_image(float(self.hadj.get_page_size())/self.chart_width, self.xscale)

    def on_zoom_100(self, action):
        self.zoom_image(1.0, self.original_scale)

    def show_toggled(self, button):
        self.options.app_options.show_all = button.get_active()
        self.queue_draw()

    def on_key_press_event(self, widget, event):
        if event.keyval == Gdk.KEY_Left:
            self.offset_image(-self.POS_INCREMENT, 0)
        elif event.keyval == Gdk.KEY_Right:
            self.offset_image(self.POS_INCREMENT, 0)
        elif event.keyval == Gdk.KEY_Up:
            self.offset_image(0, -self.POS_INCREMENT)
        elif event.keyval == Gdk.KEY_Down:
            self.offset_image(0, self.POS_INCREMENT)
        elif event.keyval == Gdk.KEY_equal or event.keyval == Gdk.KEY_plus or event.keyval == Gdk.KEY_KP_Add:
            self.on_zoom_in(None)
        elif event.keyval == Gdk.KEY_underscore or event.keyval == Gdk.KEY_minus or event.keyval == Gdk.KEY_KP_Subtract:
            self.on_zoom_out(None)
        else:
            return False
        return True

    def on_area_button_press(self, area, event):
        if self.last_b == None:
            self.last_b = event.button
            self.last_mx = event.x_root
            self.last_my = event.y_root
            if self.last_b == 2:
                # set vertical line
                if self.zoom_ratio!=0 and self.xscale!=0:
                    self.line_x = (event.x/self.zoom_ratio-draw.off_x)/self.xscale
                else:
                    self.line_x = -1
                self.queue_draw()
            if self.last_b==3:
                area.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.SB_H_DOUBLE_ARROW))
            else:
                area.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.FLEUR))
            self.grab_focus() # select the component on a mouse button press
            self.queue_draw()
        return False

    def on_area_button_release(self, area, event):
        if self.last_b != None:
            if event.button == self.last_b:
                if self.last_b == 2:
                    # set vertical line
                    if self.zoom_ratio!=0 and self.xscale!=0:
                        self.line_x = (event.x/self.zoom_ratio-draw.off_x)/self.xscale
                    else:
                        self.line_x = -1
                    self.queue_draw()
                elif self.last_b==3:
                    # zoom the image
                    self.zoom_image(self.zoom_ratio*math.pow(self.ZOOM_MOUSE_INCREMENT, event.x_root - self.last_mx), self.xscale)
                else:
                    # pan the image
                    self.offset_image(self.last_mx - event.x_root, self.last_my - event.y_root)
                area.get_window().set_cursor(None)
                self.last_b=None
                self.last_mx=None
                self.last_my=None
        return False

    def on_area_scroll_event(self, area, event):
        if (event.state & Gdk.ModifierType.CONTROL_MASK) != 0:
            if event.direction == Gdk.ScrollDirection.UP:
                self.zoom_image(self.zoom_ratio * self.ZOOM_INCREMENT)
                return True
            if event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_image(self.zoom_ratio / self.ZOOM_INCREMENT)
                return True
            return False

    def on_area_motion_notify(self, area, event):
        if self.last_b != None:
            if self.last_b == 2:
                # set vertical line
                if self.zoom_ratio!=0 and self.xscale!=0:
                    self.line_x = (event.x/self.zoom_ratio-draw.off_x)/self.xscale
                else:
                    self.line_x = -1
                self.queue_draw()
            elif self.last_b == 3:
                # zoom the image
                self.zoom_image(self.zoom_ratio*math.pow(self.ZOOM_MOUSE_INCREMENT, event.x_root - self.last_mx), self.xscale)
            else:
                # pan the image
                self.offset_image(self.last_mx - event.x_root, self.last_my - event.y_root)
            self.last_mx = event.x_root
            self.last_my = event.y_root
        return False


class PyBootchartShell(Gtk.VBox):
    ui = '''
    <ui>
            <toolbar name="ToolBar">
                    <toolitem action="Expand"/>
                    <toolitem action="Contract"/>
                    <separator/>
                    <toolitem action="ZoomIn"/>
                    <toolitem action="ZoomOut"/>
                    <toolitem action="ZoomFit"/>
                    <toolitem action="Zoom100"/>
                    <separator/>
                    <toolitem action="Help"/>
            </toolbar>
    </ui>
    '''

    def __init__(self, window, trace, options, xscale):
        Gtk.VBox.__init__(self)

        # image drawing widget
        self.widget = PyBootchartWidget(trace, options, xscale)

        self.widget.set_tooltip_markup('<b>Keypad</b> to move\n'
                                       +'<b>+</b> to zoom in\n'
                                       +'<b>-</b> to zoom out\n'
                                       +'<b>Ctrl+Wheel</b> to zoom\n'
                                       +'Horizontal drag with <b>Right button</b> to zoom\n'
                                       +'<b>Middle click</b> to set mark\n'
                                       +'Drag with <b>Left button</b> to move')
        self.widget.set_has_tooltip(False)

        # Create a UIManager instance
        uimanager = self.uimanager = Gtk.UIManager()

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        window.add_accel_group(accelgroup)

        # Create an ActionGroup
        actiongroup = Gtk.ActionGroup('Actions')
        self.actiongroup = actiongroup

        # Create actions
        actiongroup.add_actions((
                ('Expand', Gtk.STOCK_ADD, None, None, 'Expand time axis', self.widget.on_expand),
                ('Contract', Gtk.STOCK_REMOVE, None, None, 'Contract time axis', self.widget.on_contract),
                ('ZoomIn', Gtk.STOCK_ZOOM_IN, None, None, 'Zoom in', self.widget.on_zoom_in),
                ('ZoomOut', Gtk.STOCK_ZOOM_OUT, None, None, 'Zoom out', self.widget.on_zoom_out),
                ('ZoomFit', Gtk.STOCK_ZOOM_FIT, None, None, 'Fit width', self.widget.on_zoom_fit),
                ('Zoom100', Gtk.STOCK_ZOOM_100, None, None, 'Zoom 100%', self.widget.on_zoom_100),
        ))
        actiongroup.add_toggle_actions((
                ('Help', Gtk.STOCK_HELP, None, None, 'Toggle tooltip with hotkeys', self.show_help, False),
        ))

        # Add the actiongroup to the uimanager
        uimanager.insert_action_group(actiongroup, 0)

        # Add a UI description
        uimanager.add_ui_from_string(self.ui)

        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        # append image to scrolled
        scrolled.add(self.widget) # or add_with_viewport?
        scrolled.set_hadjustment(self.widget.hadj) # possible leak?
        scrolled.set_vadjustment(self.widget.vadj) # possible leak?

        # toolbar / h-box
        hbox = Gtk.HBox(False, 8)

        # Create a Toolbar
        toolbar = uimanager.get_widget('/ToolBar')
        hbox.pack_start(toolbar, True, True, 8)

        if not options.kernel_only:
            # Misc. options
            button = Gtk.CheckButton("Show more")
            button.connect ('toggled', self.widget.show_toggled)
            hbox.pack_start (button, False, True, 8)

        self.pack_start(hbox, False, False, 8)
        self.pack_start(scrolled, True, True, 8)
        # select the scrolled component first, then panel's buttons
        self.set_focus_chain((scrolled, hbox))
        self.show_all()

    def show_help(self, act):
        self.widget.set_has_tooltip(act.get_active())

class PyBootchartWindow(Gtk.Window):

    def __init__(self, trace, app_options):
        Gtk.Window.__init__(self)

        window = self
        window.set_title("Bootchart %s" % trace.filename)
        window.set_default_size(750, 550)

        tab_page = Gtk.Notebook()
        tab_page.show()
        window.add(tab_page)

        full_opts = RenderOptions(app_options)
        full_tree = PyBootchartShell(window, trace, full_opts, 1.0)
        tab_page.append_page (full_tree, Gtk.Label("Full tree"))

        if trace.kernel is not None and len (trace.kernel) > 2:
            kernel_opts = RenderOptions(app_options)
            kernel_opts.cumulative = False
            kernel_opts.charts = False
            kernel_opts.kernel_only = True
            kernel_tree = PyBootchartShell(window, trace, kernel_opts, 5.0)
            tab_page.append_page (kernel_tree, Gtk.Label("Kernel boot"))

        full_tree.widget.grab_focus() # select the DrawingArea initially
        self.show()


def show(trace, options):
    win = PyBootchartWindow(trace, options)
    win.connect('destroy', Gtk.main_quit)
    Gtk.main()
