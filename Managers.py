import tkinter
import re
from collections import defaultdict
from Models import Straight, Curve, Point, Crossover, Signal
from ResizingCanvas import ResizingCanvas


class TrackManager(object):
    # TODO: Fix docstring for new spec
    """A central class for the whole layout."""
    def __init__(self, canvas, filename="", auto_group=True):
        # Create Track
        self.canvas = canvas
        self.signal_managers = []
        self.track_labels = {}
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
        self.groups = []
        if auto_group:
            self.auto_point_group()

    @staticmethod
    def nonenone():
        return [None, None]

    def load_track(self, filename):
        out = defaultdict(list)
        track_name_re = re.compile(r"NEW::\s*([^(]*)\(")
        # Splits at spaces outside of brackets, and also at outermost brackets
        space_split_re = re.compile(r"[^:\s\[(\"]+|\"[^\"]+\"|\[[^\]]*]|\([^)]*\)|::.*")
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
                        raise TrackSyntaxError(line, "NEW:: defined without closure")
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
                            raise TrackSyntaxError(line, "Invalid direction: {}".format(direction_txt[0]))
                        # Reset for new track
                        last_coord = (None, None)
                        piece = None
                        label = ""
                        arguments = []
                        print(current_track, direction)
                else:
                    if current_track is None:
                        raise TrackSyntaxError(line, "No track segment started")
                    coord_and_pieces = space_split_re.findall(line)

                    # If it is the start. For subsequent lines this is skipped
                    if last_coord[0] is None:
                        last_coord = coord_handler(coord_and_pieces[0])
                        if last_coord[0] is None:
                            raise TrackSyntaxError(line, "No starting coordinate given")
                        coord_and_pieces = coord_and_pieces[1:]

                    for text in coord_and_pieces:
                        # Test if comment, then coord, argument, finally piece
                        if text.startswith("#"):
                            # Rest of the line is a comment
                            break
                        if text.startswith("("):
                            next_coord = coord_handler(text)
                            if next_coord[0] is None:
                                raise TrackSyntaxError(line, "Invalid coordinate given", text)
                            if piece is None:
                                raise TrackSyntaxError(line, "No piece between coordinates", text)
                            # All track pieces are start, end then optional further arguments
                            # noinspection PyUnboundLocalVariable
                            new_piece = piece(self.canvas, current_track, direction, last_coord,
                                              next_coord, *arguments, label=label)
                            out[current_track].append(new_piece)
                            self.track_labels[label] = new_piece
                            last_coord = next_coord
                            piece = None
                            label = ""
                            arguments = []
                        elif text.startswith("["):
                            arguments = argument_handler(text)
                        elif text == "::END":
                            # End of the branch
                            if piece is not None:
                                raise TrackSyntaxError(line, "::END called before final coordinates", text)
                            else:
                                current_track = None
                        elif text == "::CLOSE":
                            # Close a track loop
                            if piece is None:
                                raise TrackSyntaxError(line, "::CLOSE called without piece", text)
                            else:
                                end_coord = out[current_track][0].start
                                # noinspection PyUnboundLocalVariable
                                out[current_track].append(piece(self.canvas, current_track, direction, last_coord,
                                                                end_coord, *arguments))
                                current_track = None
                        elif text.startswith("\""):
                            label = text.strip("\"")
                            if label in self.track_labels:
                                raise TrackSyntaxError(line, "Repeated Label", label)
                        else:
                            piece = piece_handler(text)
        return out

    def auto_point_group(self):
        """Groups points and crossovers that join at at least 1 alt coordinate."""
        for coord, pieces in self.coordinate_dict.items():
            if ((isinstance(pieces[0], Point) or isinstance(pieces[0], Crossover)) and
                    (isinstance(pieces[1], Point) or isinstance(pieces[1], Crossover)) and not
            (coord in (pieces[0].start, pieces[0].end) and coord in (pieces[1].start, pieces[1].end))):
                if pieces[0].groups and pieces[1].groups:
                    # TODO: join groups together for more complex layout options.
                    print(pieces, coord)
                    raise Exception("Autogrouping error: both already in groups")
                elif pieces[0].groups:
                    pieces[0].groups[0].append(pieces[1])
                elif pieces[1].groups:
                    pieces[1].groups[0].append(pieces[0])
                else:
                    self.groups.append(TrackGroup(pieces))
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


class TrackGroup:
    """A group of track pieces (primarily points) that act in unison."""

    def __init__(self, pieces):
        self.all = list(pieces)
        self.points = [x for x in self.all if isinstance(x, Point)]
        self.crossover = [x for x in self.all if isinstance(x, Crossover)]
        self.other = [x for x in self.all if x not in self.points or x not in self.crossover]
        self.image_ids = []
        self.canvases = set()
        self.signal_managers = []
        for item in self.all:
            item.groups.append(self)
            self.canvases.add(item.canvas)
            for id in item.image_ids:
                self.image_ids.append(id)
                item.canvas.itemconfig(id, tag=str(self))
        for canvas in self.canvases:
            for id in self.image_ids:
                canvas.tag_bind(id, "<Button-1>", self.on_click)
                # Currently hover will be called twice for the piece the mouse is over, the second call having no affect
                #  on the display
                canvas.tag_bind(id, "<Enter>", self.hover, "+")
                canvas.tag_bind(id, "<Leave>", self.hover, "+")

    def on_click(self, event):
        labels = []
        for item in self.all:
            item.on_click(event)
            labels.append(item.label)
        for signal_manager in self.signal_managers:
            for label in labels:
                for signal in signal_manager.track_label_interlock[label]:
                    signal.interlock_red()

    def hover(self, event):
        for item in self.all:
            item.hover(event)

    def append(self, other):
        """Add a new track piece to the group"""
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
            other.canvas.tag_bind(id, "<Enter>", self.hover, "+")
            other.canvas.tag_bind(id, "<Leave>", self.hover, "+")

    def __repr__(self):
        return "TrackGroup({})".format(self.all)


class SignalManager:
    def __init__(self, trackmanager, canvas, filename):
        self.track_manager = trackmanager
        track_manager.signal_managers.append(self)
        for group in trackmanager.groups:
            group.signal_managers.append(self)
        self.canvas = canvas
        self.all = {}
        self.track_label_interlock = defaultdict(list)
        self.load(filename)

    def load(self, filename):
        signals_define = False
        # Line of the form "SignalLabel":: Pos["Label" Start/End/Alternate/tart/end Left/Right] Red["Label" 0/1 &/|]
        signal_definition_re = re.compile(r"\s*".join(
            (r'"(?P<signal_label>[^"]+)"::', 'Pos', r'\[', r'"(?P<pos_label>[^"]+)"',
             r'(?P<start>(Start)|(End)|(Alt((ernate)|(start)|(end))?))?', r'(?P<position>(Left)|(Right))?', r'\]',
             r'(Red', r'\[', r'(?P<red_condition>(\(*\s*"[^"]+"\s+[0-1]\s*\)*\s*(&|\|)?\s*)*)',
             r'\])?')))
        label_re = re.compile(r'"[^"]*"')
        with open(filename) as f:
            for line in f:
                line = line.strip("\n").strip()
                if not line:
                    continue
                elif line.startswith("SIGNALS::"):
                    signals_define = True
                elif line.startswith("::END"):
                    signals_define = False
                elif signals_define:
                    m = signal_definition_re.fullmatch(line)
                    if m is None:
                        raise AccessorySyntaxError(line, "Signal definition not of correct form")
                    groupdict = m.groupdict()
                    if groupdict["position"] is None:
                        groupdict["position"] = "Left"
                    if groupdict["start"] is None:
                        groupdict["start"] = "Start"
                    elif groupdict["start"] == "Alt":
                        groupdict["start"] = "Alternate"
                    track_segment = self.track_manager.track_labels[groupdict["pos_label"]]
                    track_pos = getattr(track_segment, groupdict["start"].lower())
                    if groupdict["start"] == "Start":
                        track_dir = (track_segment.end[0] - track_pos[0], track_segment.end[1] - track_pos[1])
                    elif groupdict["start"] == "Alternate" and isinstance(track_segment, Point) \
                            and not track_segment.facing:
                        track_dir = (track_pos[0] - track_segment.end[0], track_pos[1] - track_segment.end[1])
                    else:
                        track_dir = (track_pos[0] - track_segment.start[0], track_pos[1] - track_segment.start[1])
                    # Normalise
                    track_dir_size = (track_dir[0] ** 2 + track_dir[1] ** 2) ** 0.5
                    track_dir = (track_dir[0] / track_dir_size, track_dir[1] / track_dir_size)
                    if groupdict["position"] == "Right":
                        # Normal by (x,y) => (-y, x)
                        light_pos = (track_pos[0] - 10 * track_dir[1], track_pos[1] + 10 * track_dir[0])
                    else:
                        light_pos = (track_pos[0] + 10 * track_dir[1], track_pos[1] - 10 * track_dir[0])
                    red_condition = groupdict["red_condition"]
                    red_condition = red_condition.replace("&", "and").replace("|", "or")
                    for label in set(label_re.findall(red_condition)):
                        red_condition = red_condition.replace(label,
                                                              "self.track_manager.track_labels[{}]".format(label))
                    red_condition = re.sub(r'("[^"]*"\])\s*([0-1])', r'\1.set == \2', red_condition)
                    if red_condition:
                        eval(red_condition)
                    signal = Signal(self.canvas, light_pos, self.track_manager, red_condition,
                                    groupdict["signal_label"])
                    self.all[groupdict["signal_label"]] = signal
                    for label in set(label_re.findall(red_condition)):
                        self.track_label_interlock[label.strip("\"")].append(signal)


class TrackSyntaxError(Exception):
    def __init__(self, line, string, text=""):
        super().__init__(string, line, text)


class AccessorySyntaxError(Exception):
    pass


if __name__ == "__main__":
    root = tkinter.Tk()
    myframe = tkinter.Frame(root)
    myframe.pack(fill="both", expand="yes")
    root.wm_title("Railway Manager")
    C = ResizingCanvas(myframe, bg="cyan", height=600, width=1000)
    track_manager = TrackManager(C, "Loft.track")
    signal_manager = SignalManager(track_manager, C, "Loft.accessory")
    C.pack(fill="both", expand="yes")
    root.mainloop()
    print("Done")
