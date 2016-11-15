"""For running with serial"""
from collections import defaultdict
from Managers import TrackManager, SignalManager
import tkinter
from ResizingCanvas import ResizingCanvas
from SerialManager import SerialManager

if __name__ == "__main__":
    # Setup tkinter
    root = tkinter.Tk()
    frame = tkinter.Frame(root)
    frame.pack(fill="both", expand="yes")
    root.wm_title("Railway Manager")
    canvas = ResizingCanvas(frame, bg="cyan", height=600, width=1000)
    track_manager = TrackManager(canvas, "Loft.track")
    signal_manager = SignalManager(track_manager, canvas, "Loft.accessory")
    canvas.pack(fill="both", expand="yes")

    # Setup serial
    write_mapping = defaultdict(dict)
    read_mapping = defaultdict(list)
    creation = {"PRA": ["R1a", "R2a", "R3a", "R4a"], "PRB": ["R5a", "C1", "C2a"], "PLA": ["L1a", "L2a", "L3a", "L4a"],
                "PST": ["St1a", "St2", "St3", "St4"], "PLB": ["L5a", "B1"], "PUP": ["U1", "U2a"]}
    for header, labels in creation.items():
        for i, label in enumerate(labels):
            piece = track_manager.track_labels[label]
            write_mapping[piece]["HEADER"] = header
            write_mapping[piece][0] = 2 * i
            write_mapping[piece][1] = 2 * i + 1
            read_mapping[header].append(piece.groups[0])
    print(write_mapping)
    print(read_mapping)
    serial_manager = SerialManager("COM3", write_mapping, read_mapping, root)
    for group in track_manager.groups:
        group.serial_manager = serial_manager

    # Run
    root.mainloop()
    print("Done")
