"""Contains model classes"""
from collections import namedtuple

from CreateToolTip import create_tool_tip


class Track(object):
    """A piece of Track will have a start and end.
    Direction indicates normal running direction (from start to end), which must be either clockwise(1) or 
    anti-clockwise(-1). Sidings direction is defined as the direction of the loop it comes off for facing points or 
    joins onto for trailing points.
    """

    def __init__(self, canvas, branch, direction, start, end, groups=None, label=""):
        self.conflict = False
        self.branch = branch
        self.start = start
        self.end = end
        self.canvas = canvas
        self.direction = direction
        self.groups = groups if groups is not None else []
        self.label = label
        self.image_ids = self.create()
        for image_id in self.image_ids:
            create_tool_tip(self.canvas, image_id, str(self))

    @property
    def coordinates(self):
        """Returns all the coordinates of endpoints"""
        return self.start, self.end

    def next(self, reverse):
        """Called when TrackManager iterates through by direction"""
        return self.start if reverse else self.end

    def create(self):
        """Create and Return an iterable of ids of line segments that make up the image on the canvas"""
        raise NotImplementedError

    def on_click(self, event):
        """Hook for subclasses"""
        pass

    def hover(self, event):
        """Hook for subclasses"""
        pass

    def __repr__(self) -> str:
        return "{name}{coord}".format(name=self.__class__.__name__, coord=self.coordinates)

    def __str__(self):
        if self.label:
            return "{name} {label}".format(name=self.__class__.__name__, label=self.label)
        else:
            return self.__repr__()


class Straight(Track):
    def create(self):
        ids = namedtuple("image_ids", ["main"])
        return ids(self.canvas.create_line(self.start, self.end))


class Curve(Track):
    def __init__(self, canvas, branch, direction, start, end, left_right="", factor=4, label=""):
        self.factor = factor / 10
        if str(direction).lower() in ("1", "clockwise"):
            direction = 1
        elif str(direction).lower() in ("-1", "anticlockwise"):
            direction = -1
        else:
            raise Exception("Invalid direction {}".format(direction))
        if left_right:
            l_r = left_right.upper()[0]
        else:
            l_r = "L" if direction == -1 else "R"
        if l_r in ("R", "L"):
            self.left_right = l_r
        else:
            raise Exception("Curve not defined as L or R")
        super().__init__(canvas, branch, direction, start, end, label=label)

    def create(self):
        tangent = (self.start[1] - self.end[1], self.end[0] - self.start[0])
        midpoint = ((self.start[0] + self.end[0])/2, (self.start[1] + self.end[1])/2)
        if self.left_right == "R":
            curvepoint = (midpoint[0] - self.factor * tangent[0], midpoint[1] - self.factor * tangent[1])
        else:
            curvepoint = (midpoint[0] + self.factor * tangent[0], midpoint[1] + self.factor * tangent[1])
        ids = namedtuple("image_ids", ["main"])
        return ids(self.canvas.create_line(self.start, curvepoint, self.end, smooth=True))


class Point(Track):
    def __init__(self, canvas, branch, direction, start, end, alternate, facing=1, label=""):
        self.alternate = alternate
        self.facing = facing
        self.set = 0
        super().__init__(canvas, branch, direction, start, end, label=label)

        for imageID in self.image_ids:
            self.canvas.tag_bind(imageID, '<Button-1>', self.on_click)
            self.canvas.tag_bind(imageID, "<Enter>", self.hover, "+")
            self.canvas.tag_bind(imageID, "<Leave>", self.hover, "+")

    @property
    def coordinates(self):
        return self.start, self.end, self.alternate

    def next(self, reverse):
        """Returns the coordinates of the other end of the piece depending how the points are set."""
        if self.facing:
            if reverse:
                return self.start
            elif self.set:
                return self.alternate
            else:
                return self.end
        else:
            if not reverse:
                return self.start
            elif self.set:
                return self.alternate
            else:
                return self.end

    def create(self):
        main_id = self.canvas.create_line(self.start, self.end)
        if self.facing:
            alt_id = self.canvas.create_line(self.start, self.alternate, dash=1, fill="Red")
        else:
            alt_id = self.canvas.create_line(self.end, self.alternate, dash=1, fill="Red")
        ids = namedtuple("image_ids", ["main", "alt"])
        return ids(main_id, alt_id)

    def draw(self):
        if self.set:
            self.canvas.itemconfig(self.image_ids[0], dash=[1], fill="Red")
            self.canvas.itemconfig(self.image_ids[1], dash=[], fill="Black")
        else:
            self.canvas.itemconfig(self.image_ids[0], dash=[], fill="Black")
            self.canvas.itemconfig(self.image_ids[1], dash=[1], fill="Red")

    def on_click(self, event):
        self.set = not self.set
        print("Set:", self, self.set)
        self.draw()

    def hover(self, event):
        # Enter is type 7, leave is type 8
        if event.type == "7":
            if self.set:
                self.canvas.itemconfig(self.image_ids[0], fill="Green", width=1.5)
                self.canvas.itemconfig(self.image_ids[1], fill="Red", width=1.5)
            else:
                self.canvas.itemconfig(self.image_ids[0], fill="Red", width=1.5)
                self.canvas.itemconfig(self.image_ids[1], fill="Green", width=1.5)
        elif event.type == "8":
            if self.set:
                self.canvas.itemconfig(self.image_ids[0], fill="Red", width=1)
                self.canvas.itemconfig(self.image_ids[1], fill="Black", width=1)
            else:
                self.canvas.itemconfig(self.image_ids[0], fill="Black", width=1)
                self.canvas.itemconfig(self.image_ids[1], fill="Red", width=1)
        else:
            print("Unhandled event", event, event.type, event.type in ("7", "8"), self.set)

    def __repr__(self):
        return "{repr}, {facing})".format(repr=super().__repr__()[:-1], facing=self.facing)


class Crossover(Point):
    def __init__(self, canvas, branch, direction, start, end, altstart, altend, label=""):
        self.altstart = altstart
        self.altend = altend
        self.set = False
        super().__init__(canvas, branch, direction, start, end, None, label=label)

    def create(self):
        id1 = self.canvas.create_line(self.start, self.end)
        id2 = self.canvas.create_line(self.altstart, self.altend, dash=1, fill="Red")
        ids = namedtuple("image_ids", ["main", "alt"])
        return ids(id1, id2)

    @property
    def coordinates(self):
        return self.start, self.end, self.altstart, self.altend


class Signal:
    def __init__(self, canvas, pos, track_manager, red_conditions, label):
        self.canvas = canvas
        self.pos = pos
        self.track_manager = track_manager
        self.image_id = self.create()
        self.set = False
        self.red_conditions = red_conditions
        self.label = label
        self.canvas.tag_bind(self.image_id, "<Button-1>", self.on_click)
        create_tool_tip(self.canvas, self.image_id, str(self))

    def create(self):
        return self.canvas.create_oval((self.pos[0] - 4, self.pos[1] - 4), (self.pos[0] + 4, self.pos[1] + 4),
                                       fill="Red", outline="Red", width=0)

    def interlock_red(self):
        """Checks if track forces the signal to be red"""
        if self.red_conditions and eval(self.red_conditions):
            print("Interlocked:", self)
            self.set = 0
            self.draw()
            # Flash
            self.canvas.itemconfig(self.image_id, width=4)
            self.canvas.after(100, lambda: self.canvas.itemconfig(self.image_id, width=0))
            return False
        return True

    # noinspection PyUnusedLocal
    def on_click(self, event):
        """Checks and changes signal state"""
        if self.set:
            self.set = 0
        else:
            self.set = self.interlock_red()
        self.draw()

    def draw(self):
        if self.set:
            self.canvas.itemconfig(self.image_id, fill="Green", outline="Green")
        else:
            self.canvas.itemconfig(self.image_id, fill="Red", outline="Red")

    def __repr__(self) -> str:
        return "{name}{coord}".format(name=self.__class__.__name__, coord=self.pos)

    def __str__(self):
        if self.label:
            return "{name} {label}".format(name="Signal", label=self.label)
        else:
            return self.__repr__()
