"""Runs a simple train animation"""

from Managers import TrackManager, SignalManager
import tkinter
from ResizingCanvas import ResizingCanvas


class Train:
    """
    A basic train animation going around the track.
    Left click to stop/start
    Right click to change direction
    """

    def __init__(self, canvas, track_manager, pos, direction, colour="Blue", label="", speed=1.0):
        self.size = 4
        self.canvas = canvas
        self.track_manager = track_manager
        self.colour = colour
        self.label = label
        self.speed = speed
        self.pos = list(pos)
        coord = tuple(pos)
        if coord not in self.track_manager.coordinate_dict:
            near_id = self.canvas.find_closest(*self.pos)
            print(near_id)
            self.track_segment = self.track_manager.piece_by_id(near_id[0])
        else:
            piece_list = self.track_manager.coordinate_dict[coord]
            if None in piece_list:
                self.track_segment = next((x for x in piece_list if x is not None))
            else:
                if piece_list[0].direction == piece_list[1].direction:  # The common case
                    if direction == piece_list[0].direction:
                        self.track_segment = next((x for x in piece_list if x.start == coord))
                    else:
                        # TODO: Cope with alternates
                        self.track_segment = next((x for x in piece_list if x.end == coord))
                else:
                    # Assume we are going the right way on the track.
                    self.track_segment = next((x for x in piece_list if x.direction == direction))
        self.segment_start = pos
        self.segment_end = self.track_segment.next(pos)
        # Get the previous segment
        if self.segment_end is not None:
            self.segment_start = self.track_segment.next(self.segment_end)
            self.previous_segment = next(
                (x for x in self.track_manager.coordinate_dict[self.segment_start] if
                 x is not self.track_segment))
        else:
            self.previous_segment = None

        self.track_segment.train_in = self
        if self.previous_segment is not None:
            self.previous_segment.train_in = self
        # self.track_segment = track_manager.coordinate_dict[pos][0]
        self.direction = direction
        self.image_id = self.create()
        self.canvas.tag_bind(self.image_id, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.image_id, "<Button-3>", self.on_click)
        self.stop = False
        self.next_section_occupied_flag = False
        self.canvas.after(10, self.move)

    def create(self) -> int:
        """Draw on the canvas, returning the id"""
        return self.canvas.create_oval((self.pos[0] - self.size, self.pos[1] - self.size),
                                       (self.pos[0] + self.size, self.pos[1] + self.size),
                                       fill=self.colour, width=1.3)

    def draw(self):
        """Edits the current image"""
        if self.stop:
            self.canvas.itemconfig(self.image_id, outline="Red")
        else:
            self.canvas.itemconfig(self.image_id, outline="Black")

    @property
    def next_section(self):
        """Returns the next piece of track"""
        return next((x for x in self.track_manager.coordinate_dict[self.segment_end] if x is not self.track_segment))

    @staticmethod
    def close_to(x, y, diff=0.5):
        """Works out if two 2-vectors are sufficiently close (for small errors introduced by corners)
        """
        if y[0] - diff <= x[0] <= y[0] + diff and y[1] - diff <= x[1] <= y[1] + diff:
            return True
        else:
            return False

    def on_click(self, event):
        """Left click to stop/start, right click to change direction"""
        if event.num == 1:
            self.stop = not self.stop
        else:
            self.direction *= -1
            self.segment_start, self.segment_end = self.segment_end, self.segment_start
        self.draw()

    def __str__(self):
        return "Train {} ({})".format(self.label, self.colour)

    def move(self):
        """Called by tkinter. Checks whether the train can move (e.g. if stopped by click, at a red signal, points set
        against or other train ahead) sets the current and previous tack pieces as occupied and moves an increment
        towards the end of the track piece.
        Finally sets itself to be called again after 10ms.
        """
        if self.stop:
            self.canvas.after(10, self.move)
            return

        # Stop at red signals
        label = self.track_segment.label
        signal_manager = self.track_manager.signal_manager
        if label and signal_manager and label in signal_manager.all:
            signal = signal_manager.all[label]
            # Held by signal that is next to the start track segment.
            # Note this assumes signal is placed at segment start, which is default but not required.
            if signal.direction == self.direction and not signal.set and \
               tuple(self.pos) == getattr(self.track_segment, signal.track_relative_position):
                # Check if points have changed
                self.segment_end = self.track_segment.next(self.segment_start)
                self.canvas.after(10, self.move)
                return

        if self.segment_end is None:
            self.segment_end = self.track_segment.next(self.pos)
        elif self.close_to(self.pos, self.segment_end, 0.5*self.speed):
            next_section = self.next_section
            if next_section is None:
                print("End of line for", self)
                self.stop = True
                self.draw()
            elif next_section.train_in and next_section.train_in != self:
                if not self.next_section_occupied_flag:
                    print("Next section occupied for", self)
                    self.next_section_occupied_flag = True
            else:
                self.next_section_occupied_flag = False
                self.previous_segment = self.track_segment
                self.track_segment = next_section
                self.segment_start = self.segment_end
                self.pos = list(self.segment_end)
                self.segment_end = self.track_segment.next(self.segment_end)
        elif self.close_to(self.pos, self.segment_end, 20) and self.next_section is not None and \
                self.next_section.train_in and self.next_section.train_in.direction == -1 * self.direction:
            self.stop = True
            self.draw()
            print("Stopped due to conflicting traffic approaching")
        else:
            self.track_segment.train_in = self
            if self.previous_segment is not None and self.previous_segment.train_in == self:
                self.previous_segment.train_in = False
            dx = self.segment_end[0] - self.pos[0]
            dy = self.segment_end[1] - self.pos[1]
            normalise = (dx ** 2 + dy ** 2) ** 0.5
            # self.canvas.move(self.image_id, dx/normalise, dy/normalise)
            self.pos[0] += dx / normalise * self.speed
            self.pos[1] += dy / normalise * self.speed
            self.canvas.coords(self.image_id, (self.pos[0] - self.size) * self.canvas.wscale,
                               (self.pos[1] - self.size) * self.canvas.hscale,
                               (self.pos[0] + self.size) * self.canvas.wscale,
                               (self.pos[1] + self.size) * self.canvas.hscale)
        self.canvas.after(10, self.move)


if __name__ == "__main__":
    root = tkinter.Tk()
    frame = tkinter.Frame(root)
    frame.pack(fill="both", expand="yes")
    root.wm_title("Railway Manager")
    canvas = ResizingCanvas(frame, bg="cyan", height=600, width=1000)
    track_manager = TrackManager(canvas, "Loft.track")
    signal_manager = SignalManager(track_manager, canvas, "Loft.accessory")
    canvas.pack(fill="both", expand="yes")
    fast_up_train = Train(canvas, track_manager, (325, 575), 1, "Blue", "Fast Up", 1.6)
    fast_down_train = Train(canvas, track_manager, (700, 525), -1, "Purple", "Fast Down", 1.4)
    slow_down_train = Train(canvas, track_manager, (659, 380), -1, "Orange", "Slow Down")
    root.mainloop()
    print("\nDone")
