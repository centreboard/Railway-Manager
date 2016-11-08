from tkinter import *


class ResizingCanvas(Canvas):
    """From http://stackoverflow.com/a/22837522
    A canvas that rescales everything on it as the window size is altered."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind("<Configure>", self.on_resize)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()
        self.n = 0

    def on_resize(self, event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width) / self.width
        hscale = float(event.height) / self.height
        self.n += 1
        # print("Resize", self.n, event.width == self.width, event.height, self.height, wscale, hscale)
        self.width = event.width
        self.height = event.height
        # resize the canvas
        # self.config(width=self.width, height=self.height)
        # rescale all the objects tagged with the "all" tag
        self.scale("all", 0, 0, wscale, hscale)
