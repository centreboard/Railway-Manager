from Managers import TrackManager, SignalManager
import tkinter
from ResizingCanvas import ResizingCanvas


class Train:
    def __init__(self, canvas, track_manager, pos, direction):
        self.canvas = canvas
        self.track_manager = track_manager
        self.pos = list(pos)
        coord = tuple(pos)
        if coord not in self.track_manager.coordinate_dict:
            raise KeyError(coord)
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
                    raise NotImplementedError
        self.segment_start = pos
        self.segment_end = self.track_segment.next(pos)
        #self.track_segment = track_manager.coordinate_dict[pos][0]
        self.direction = direction
        self.image_id = self.create()
        self.canvas.after(10, self.move)

    def create(self):
        return self.canvas.create_oval((self.pos[0] - 4, self.pos[1] - 4), (self.pos[0] + 4, self.pos[1] + 4),
                                       fill="Blue")

    def move(self):

        def close_to(x, y, diff=0.5):
            if y[0] - diff <= x[0] <= y[0] + diff and y[1] - diff <= x[1] <= y[1] + diff:
                return True
            else:
                return False
        # Stop at red signals
        label = self.track_segment.label
        signal_manager = self.track_manager.signal_manager
        if label and signal_manager and label in signal_manager.all:
            signal = signal_manager.all[label]
            if signal.direction == self.direction and not signal.set and tuple(self.pos) == self.segment_start:
                # Check if points have changed
                self.segment_end = self.track_segment.next(self.segment_start)
                self.canvas.after(10, self.move)
                return

        if self.segment_end is None:
            self.segment_end = self.track_segment.next(self.pos)
        elif tuple(self.pos) != self.segment_start and close_to(self.pos, self.segment_end):
            temp = [x for x in self.track_manager.coordinate_dict[self.segment_end] if x is not self.track_segment]
            self.track_segment = temp[0]
            if self.track_segment is None:
                print("End of line")
                return
            self.segment_start = self.segment_end
            self.pos = list(self.segment_end)
            self.segment_end = self.track_segment.next(self.segment_end)
            print(self.track_segment)

        else:
            dx = self.segment_end[0] - self.pos[0]
            dy = self.segment_end[1] - self.pos[1]
            normalise = (dx**2 + dy **2)**0.5
            self.canvas.move(self.image_id, dx/normalise, dy/normalise)
            self.pos[0] += dx/normalise
            self.pos[1] += dy/normalise

        self.canvas.after(10, self.move)



if __name__ == "__main__":
    root = tkinter.Tk()
    myframe = tkinter.Frame(root)
    myframe.pack(fill="both", expand="yes")
    root.wm_title("Railway Manager")
    C = ResizingCanvas(myframe, bg="cyan", height=600, width=1000)
    track_manager = TrackManager(C, "Loft.track")
    signal_manager = SignalManager(track_manager, C, "Loft.accessory")
    C.pack(fill="both", expand="yes")
    train = Train(C, track_manager, (950, 575), 1)
    root.mainloop()
    print("Done")