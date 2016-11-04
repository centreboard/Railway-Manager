"""Contains model classes"""
from collections import namedtuple

from CreateToolTip import create_tool_tip


class Track(object):
    """A piece of Track will have a start and end.
    Direction indicates normal running direction, which must be either clockwise(1) or anti-clockwise(-1). Sidings
    direction is defined as the direction of the loop it comes off, so will terminate at .end
    """

    def __init__(self, canvas, branch, direction, start, end):
        self.conflict = False
        self.branch = branch
        self.start = start
        self.end = end
        self.canvas = canvas
        self.direction = direction
        self.imageIDs = self.create()
        for id in self.imageIDs:
            create_tool_tip(self.canvas, id, str(self))


    @property
    def coordinates(self):
        """Returns all the coordinates of endpoints"""
        return self.start, self.end

    def next(self, reverse):
        return self.start if reverse else self.end

    def create(self):
        """Create and Return an iterable of ids of line segments that make up the image on the canvas"""
        raise NotImplementedError

    def __repr__(self):
        return "{name}{coord}".format(name=self.__class__.__name__, coord=self.coordinates)


class Straight(Track):
    # def __init__(self, canvas, branch, start, end, direction=0):
    #     super(Straight, self).__init__(canvas, branch, start, end, direction)
    #     self.direction = direction

    def create(self):
        ids = namedtuple("image_ids", ["main"])
        return ids(self.canvas.create_line(self.start, self.end))


class Curve(Track):
    def __init__(self, canvas, branch, direction, start, end, left_right="", factor=4):
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
        super().__init__(canvas, branch, direction, start, end)


    def create(self):
        # TODO: Make curved (smooth=True?)
        tangent = (self.start[1] - self.end[1], self.end[0] - self.start[0])
        midpoint = ((self.start[0] + self.end[0])/2, (self.start[1] + self.end[1])/2)
        if self.left_right == "R":
            curvepoint = (midpoint[0] - self.factor * tangent[0], midpoint[1] - self.factor * tangent[1])
        else:
            curvepoint = (midpoint[0] + self.factor * tangent[0], midpoint[1] + self.factor * tangent[1])
        ids = namedtuple("image_ids", ["main"])
        return ids(self.canvas.create_line(self.start, curvepoint, self.end, smooth=True))


class Point(Track):
    def __init__(self, canvas, branch, direction, start, end, alternate, facing=1):
        self.alternate = alternate
        self.facing = facing
        self.set = 0
        super().__init__(canvas, branch, direction, start, end)

        for imageID in self.imageIDs:
            self.canvas.tag_bind(imageID, '<Button-1>', self.on_click)

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
        main_id = self.canvas.create_line(self.start, self.end, activefill="Red")
        if self.facing:
            alt_id = self.canvas.create_line(self.start, self.alternate, dash=1, fill="Red", activefill="Green")
        else:
            alt_id = self.canvas.create_line(self.end, self.alternate, dash=1, fill="Red", activefill="Green")
        ids = namedtuple("image_ids", ["main", "alt"])
        return ids(main_id, alt_id)

    def draw(self):
        if self.set:
            self.canvas.itemconfig(self.imageIDs[0], dash=[1], fill="Red", activefill="Green")
            self.canvas.itemconfig(self.imageIDs[1], dash=[], fill="Black", activefill="Red")
        else:
            self.canvas.itemconfig(self.imageIDs[0], dash=[], fill="Black", activefill="Red")
            self.canvas.itemconfig(self.imageIDs[1], dash=[1], fill="Red", activefill="Green")

    def on_click(self, event):
        self.set = not self.set
        print("Set:", self, self.set)
        self.draw()

    def __repr__(self):
        return "{repr}, {facing})".format(repr=super().__repr__()[:-1], facing=self.facing)


class Crossover(Straight):
    def __init__(self, canvas, branch, direction, start, end, altstart, altend):
        self.altstart = altstart
        self.altend = altend
        super().__init__(canvas, branch, direction, start, end)

    def create(self):
        id1 = self.canvas.create_line(self.start, self.end)
        id2 = self.canvas.create_line(self.altstart, self.altend)
        ids = namedtuple("image_ids", ["main", "alt"])
        return ids(id1, id2)

    @property
    def coordinates(self):
        return self.start, self.end, self.altstart, self.altend

