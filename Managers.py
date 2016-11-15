"""Classes controlling groups of models"""
import re
from collections import defaultdict
from Models import Track, Straight, Curve, Point, Crossover, Signal
from typing import Dict


class TrackManager(object):
    """A central class for the whole layout."""

    def __init__(self, canvas, filename="", auto_group=True):
        # Create Track
        self.canvas = canvas
        self.signal_manager = None
        self.track_labels = {}
        self.track_branches = self.load_track(filename, auto_group)
        self.track_pieces = [x for _, v in self.track_branches.items() for x in v]
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
            for piece in self.track_pieces:
                if isinstance(piece, Point) and not piece.groups:
                    self.groups.append(TrackGroup((piece,)))

    @staticmethod
    def nonenone():
        """For default coordinate dictionary"""
        return [None, None]

    def load_track(self, filename, auto_group) -> Dict[str, list]:
        """Loads track from a text file. Returns a dictionary with keys being the name of track branches from the file
        """
        out = defaultdict(list)
        track_name_re = re.compile(r"NEW::\s*([^(]*)\(")
        # Splits at spaces outside of brackets, and also at outermost brackets
        space_split_re = re.compile(r"[^:\s\[(\"]+|\"[^\"]+\"|\[[^\]]*]|\([^)]*\)|::.*")
        comma_split_re = re.compile(r"\([^)]*\)|[^\s,[(\]]+")

        def coord_handler(text):
            """Checks and converts "(0, 1)" to (0, 1)"""
            if not re.match(r"^\(\s*[\d]+\s*,\s*[\d]+\)", text):
                return None, None
            c1, c2 = (int(x) for x in text[1:-1].split(","))
            return c1, c2

        def argument_handler(text):
            """Splits arguments by commas and converts to coords, integers or string as appropriate"""
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
            """Converts string to a piece class"""
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
                                              next_coord, *arguments, label=label, click=not auto_group)
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
                                                                end_coord, *arguments, label=label,
                                                                click=not auto_group))
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

    def piece_by_id(self, image_id) -> Track:
        return next(x for x in self.track_pieces if image_id in x.image_ids)

    def iter_from(self, coord, direction) -> Track:
        """Follows the track from a starting coordinate in a given direction"""
        segment_end = tuple(coord)
        if segment_end not in self.coordinate_dict:
            raise KeyError(coord)
        else:
            piece_list = self.coordinate_dict[segment_end]
            if None in piece_list:
                track_segment = next((x for x in piece_list if x is not None))
            else:
                if piece_list[0].direction == piece_list[1].direction:  # The common case
                    if direction == piece_list[0].direction:
                        track_segment = next((x for x in piece_list if x.start == segment_end))
                    else:
                        # TODO: Cope with alternates
                        track_segment = next((x for x in piece_list if x.end == segment_end))
                else:
                    raise NotImplementedError
        while track_segment is not None:
            yield track_segment
            segment_end = track_segment.next(segment_end)
            if segment_end is not None:
                track_segment = next((x for x in self.coordinate_dict[segment_end] if x is not track_segment))
            else:
                track_segment = None

    def __iter__(self) -> Track:
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
        self.labels = []
        self.invert = set()
        self.signal_manager = None
        self.serial_manager = None
        for item in self.all:
            item.groups.append(self)
            self.canvases.add(item.canvas)
            self.labels.append(item.label)
            if item.set:
                self.invert.add(item)
            for image_id in item.image_ids:
                self.image_ids.append(image_id)
                item.canvas.itemconfig(image_id, tag=str(self))
                item.canvas.tag_bind(image_id, "<Button-1>", self.on_click)
                item.canvas.tag_bind(image_id, "<Enter>", self.hover, "+")
                item.canvas.tag_bind(image_id, "<Leave>", self.hover, "+")

    def on_click(self, event):
        """Calls all pieces on_click method, forces signals to check if they should be red and outputs serial"""
        # Don't change if train in section
        if any((x.train_in for x in self.all)):
            print("Train in section")
        else:
            for item in self.all:
                item.on_click(event)
            if self.signal_manager is not None:
                for label in self.labels:
                    for signal in self.signal_manager.track_label_interlock[label]:
                        signal.interlock_red()
            if self.serial_manager is not None:
                for item in self.points:
                    self.serial_manager.write(item)

    def set(self, state):
        for item in self.all:
            if item in self.invert:
                item.set = not state
            else:
                item.set = state
            item.draw()
        if self.signal_manager is not None:
            for label in self.labels:
                for signal in self.signal_manager.track_label_interlock[label]:
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
        for image_id in other.image_ids:
            self.image_ids.append(image_id)
            other.canvas.itemconfig(image_id, tag=str(self))
            other.canvas.tag_bind(image_id, "<Button-1>", self.on_click)
            other.canvas.tag_bind(image_id, "<Enter>", self.hover, "+")
            other.canvas.tag_bind(image_id, "<Leave>", self.hover, "+")

    def __repr__(self):
        return "TrackGroup({})".format(self.all)


class SignalManager:
    def __init__(self, track_manager, canvas, filename):
        self.track_manager = track_manager
        track_manager.signal_manager = self
        for group in track_manager.groups:
            group.signal_manager = self
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
                if not line or line.startswith("#"):
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
                    # Normalise vector
                    track_dir_size = (track_dir[0] ** 2 + track_dir[1] ** 2) ** 0.5
                    track_dir = (track_dir[0] / track_dir_size, track_dir[1] / track_dir_size)
                    if groupdict["position"] == "Right":
                        # Get normal vector by (x,y) => (-y, x)
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
                        # Check it is valid statement
                        eval(red_condition)
                    direction = track_segment.direction
                    signal = Signal(self.canvas, direction, light_pos, groupdict["start"].lower(),
                                    self.track_manager, red_condition, groupdict["signal_label"])
                    self.all[groupdict["signal_label"]] = signal
                    for label in set(label_re.findall(red_condition)):
                        self.track_label_interlock[label.strip("\"")].append(signal)


class TrackSyntaxError(Exception):
    def __init__(self, line, string, text=""):
        super().__init__(string, line, text)


class AccessorySyntaxError(Exception):
    pass
