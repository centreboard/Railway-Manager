import tkinter
import re
from collections import defaultdict
from Models import Straight, Curve, Point, Crossover, Signal


class TrackManager(object):
    # TODO: Fix docstring for new spec
    """A central class for the whole layout."""

    def __init__(self, canvas, filename=""):
        # Create Track
        self.canvas = canvas
        self.track_branches = self.load_track(filename)
        self.track_pieces = set([x for _, v in self.track_branches.items() for x in v])
        self.coordinate_dict = defaultdict(self.nonenone)
        for piece in self.track_pieces:
            for coord in piece.coordinates:
                if self.coordinate_dict[coord][0] is None:
                    self.coordinate_dict[coord][0] = piece
                elif self.coordinate_dict[coord][1] is None:
                    self.coordinate_dict[coord][1] = piece
                else:
                    raise Exception("Three pieces assigned to coordinate {}".format(coord))
        self.auto_point_group()

    @staticmethod
    def nonenone():
        return [None, None]

    def load_track(self, filename):
        out = defaultdict(list)
        track_name_re = re.compile(r"NEW::\s*([^(]*)\(")
        # Splits at spaces outside of brackets, and also at outermost brackets
        space_split_re = re.compile(r"[^:\s\[(]+|\[[^\]]*]|\([^)]*\)|::.*")
        comma_split_re = re.compile(r"\([^)]*\)|[^\s,[(\]]+")

        def coord_handler(text):
            if not re.match(r"^\(\s*[\d]+\s*,\s*[\d]+\)", text):
                return None, None
            c1, c2 = (int(x) for x in text[1:-1].split(","))
            return c1, c2

        def argument_handler(text):
            text_split = comma_split_re.findall(text)
            out = []
            for text_part in text_split:
                test = coord_handler(text_part)
                if test[0] is None:
                    try:
                        test = int(text_part)
                    except ValueError:
                        test = text_part
                out.append(test)
            return out

        def piece_handler(text):
            text = text.lower()
            possible = {"straight": Straight, "st": Straight, "point": Point, "pt": Point, "curve": Curve, "cv": Curve,
                        "crossover": Crossover, "xx": Crossover}
            if text in possible:
                return possible[text]
            else:
                return None

        with open(filename) as f:
            current_track = None
            for line in f:
                # Make empty line blank and tidy up
                line = line.strip('\n').strip()
                if not line or line.startswith('#'):
                    # This is a blank line or comment
                    continue
                elif line.startswith("NEW::"):
                    # A new track segment. Should not have coordinates or pieces on this line.
                    if current_track is not None:
                        raise TrackSyntaxError("NEW:: defined without closure")
                    else:
                        current_track = track_name_re.findall(line)[0]
                        direction_txt = re.findall(r"{}\s*\(([^(]*)\)".format(current_track), line)
                        # if not direction_txt or direction_txt[0].lower() in ("none", "0"):
                        #     direction = 0
                        if direction_txt[0].lower() in ("clockwise", "1"):
                            direction = 1
                        elif direction_txt[0].lower() in ("anticlockwise", "-1"):
                            direction = -1
                        else:
                            raise TrackSyntaxError("Invalid direction: {}".format(direction_txt[0]))
                        # Reset for new track
                        last_coord = (None, None)
                        piece = None
                        arguments = []
                        print(current_track, direction)
                else:
                    if current_track is None:
                        raise TrackSyntaxError("No track segment started")
                    coord_and_pieces = space_split_re.findall(line)

                    # If it is the start. For subsequent lines this is skipped
                    if last_coord[0] is None:
                        last_coord = coord_handler(coord_and_pieces[0])
                        if last_coord[0] is None:
                            raise TrackSyntaxError("No starting coordinate given")
                        coord_and_pieces = coord_and_pieces[1:]

                    for text in coord_and_pieces:
                        # Test if comment, then coord, argument, finally piece
                        if text.startswith("#"):
                            # Rest of the line is a comment
                            break
                        if text.startswith("("):
                            next_coord = coord_handler(text)
                            if next_coord[0] is None:
                                raise TrackSyntaxError("Invalid coordinate given")
                            if piece is None:
                                raise TrackSyntaxError("No piece between coordinates")
                            # All track pieces are start, end then optional further arguments
                            out[current_track].append(piece(self.canvas, current_track, direction, last_coord,
                                                            next_coord, *arguments))
                            last_coord = next_coord
                            piece = None
                            arguments = []
                        elif text.startswith("["):
                            arguments = argument_handler(text)
                        elif text == "::END":
                            if piece is not None:
                                raise TrackSyntaxError("::END called before final coordinates")
                            else:
                                current_track = None
                        elif text == "::CLOSE":
                            if piece is None:
                                raise TrackSyntaxError("::CLOSE called without piece")
                            else:
                                end_coord = out[current_track][0].start
                                # noinspection PyUnboundLocalVariable
                                out[current_track].append(piece(self.canvas, current_track, direction, last_coord,
                                                                end_coord, *arguments))
                                current_track = None
                        else:
                            piece = piece_handler(text)
        return out

    def auto_point_group(self):
        self.point_groups = []
        for coord, pieces in self.coordinate_dict.items():
            if ((isinstance(pieces[0], Point) or isinstance(pieces[0], Crossover)) and
                    (isinstance(pieces[1], Point) or isinstance(pieces[1], Crossover)) and not
                (coord in (pieces[0].start, pieces[0].end) and
                            coord in (pieces[1].start, pieces[1].end))):
                if pieces[0].groups and pieces[1].groups:
                    print(pieces, coord)
                    #raise NotImplementedError
                elif pieces[0].groups:
                    pieces[0].groups[0].append(pieces[1])
                elif pieces[1].groups:
                    pieces[1].groups[0].append(pieces[0])
                else:
                    self.point_groups.append(PointGroup(pieces))
                    # print(self.point_groups)

                    # def iter_from(self, coord, reverse=False):
                    # TODO: Rewrite this
                    # """Iterates through track pieces, stating from a coordinate.
                    # If reverse is false it goes from piece.start to piece.end (unless specified by piece to other such as
                    # piece.alternate)
                    # Returns track pieces, starting with the piece at the given coords."""
                    # i = 0 if reverse else 1
                    # piece = self.track[coord][i]
                    # while piece is not None:
                    #     yield piece
                    #     coordinates = piece.next(reverse)
                    #     i = 0 if reverse else 1
                    #     piece = self.track[coordinates][i]

    def __iter__(self):
        for piece in self.track_pieces:
            yield piece


class PointManager:
    pass


class PointGroup:
    def __init__(self, pieces):
        self.all = list(pieces)
        self.points = [x for x in self.all if isinstance(x, Point)]
        self.crossover = [x for x in self.all if isinstance(x, Crossover)]
        self.other = [x for x in self.all if x not in self.points or x not in self.crossover]
        self.image_ids = []
        self.canvases = set()
        for item in self.all:
            item.groups.append(self)
            self.canvases.add(item.canvas)
            for id in item.image_ids:
                self.image_ids.append(id)
                item.canvas.itemconfig(id, tag=str(self))
        for canvas in self.canvases:
            for id in self.image_ids:
                canvas.tag_bind(id, "<Button-1>", self.on_click)
        print(self.all)

    def on_click(self, event):
        print(self, "Clicked")
        for item in self.all:
            item.on_click(event)

    def append(self, other):
        self.all.append(other)
        if isinstance(other, Point):
            self.points.append(other)
        elif isinstance(other, Crossover):
            self.crossover.append(other)
        else:
            self.other.append(other)
        other.groups.append(self)
        self.canvases.add(other.canvas)  # Adding to set if not in it
        for id in other.image_ids:
            self.image_ids.append(id)
            other.canvas.itemconfig(id, tag=str(self))
            other.canvas.tag_bind(id, "<Button-1>", self.on_click)

    def __repr__(self):
        return "PointGroup({})".format(self.all)


class TrackSyntaxError(Exception):
    pass


if __name__ == "__main__":
    top = tkinter.Tk()
    top.wm_title("Railway Manager")
    C = tkinter.Canvas(top, bg="blue", height=600, width=1000)
    track_manager = TrackManager(C, "Loft.track")
    # print(track_manager.track_pieces)
    test_lamp = Signal(C, (500, 300), None)
    C.pack()
    top.mainloop()
    print("Done")
