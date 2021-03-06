"""From http://www.voidspace.org.uk/python/weblog/arch_d7_2006_07_01.shtml"""
from tkinter import *


class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.text = ""

    def showtip(self, text):
        """Display text in tooltip window"""
        self.text = text
        if self.tipwindow or not self.text:
            return
        # x, y, cx, cy = self.widget.bbox(INSERT)
        # x = x + self.widget.winfo_rootx() + 27
        # y = y + cy + self.widget.winfo_rooty() + 27
        x = self.widget.winfo_pointerx() + 12
        y = self.widget.winfo_pointery() + 20
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            # noinspection PyProtectedMember
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def create_tool_tip(widget, image_id, text):
    tool_tip = ToolTip(widget)

    # noinspection PyUnusedLocal
    def enter(event):
        tool_tip.showtip(text)

    # noinspection PyUnusedLocal
    def leave(event):
        tool_tip.hidetip()

    widget.tag_bind(image_id, '<Enter>', enter)
    widget.tag_bind(image_id, '<Leave>', leave)
