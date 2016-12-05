"""For running with serial"""
from collections import defaultdict
from Managers import TrackManager, SignalManager
import tkinter
from ResizingCanvas import ResizingCanvas
from SerialManager import SerialManager
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--com", type=str, default="COM3", help="Serial port for input/output")
    args = parser.parse_args()
    print("Using", args.com)

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
    write_point_mapping = defaultdict(dict)
    read_mapping = defaultdict(list)
    point_mapping = {"PRA": ["R1a", "R2a", "R3a", "R4a"], "PRB": ["R5a", "C1", "C2a"], "PLA": ["L1a", "L2a", "L3a", "L4a"],
                "PST": ["St1a", "St2", "St3"], "PLB": ["L5a", "B1"], "PUP": ["U1", "U2a"]}
    signal_mapping = {"SRA": ["R2a", "R4a", "R1b", "St1a"], "SST": ["Platform 1", "Platform 2"], "SLA": ["L1a", "L3b", "L4a", "L5b"]}
    for header, labels in point_mapping.items():
        for i, label in enumerate(labels):
            piece = track_manager.track_labels[label]
            write_point_mapping[piece]["HEADER"] = header
            write_point_mapping[piece][0] = 2 * i
            write_point_mapping[piece][1] = 2 * i + 1
            read_mapping[header].append(piece.groups[0])
    write_signal_mapping = {}
    for header, labels in signal_mapping.items():
        write_signal_mapping[header] = [signal_manager.all[label] for label in labels]

    serial_manager = SerialManager(args.com, write_point_mapping, write_signal_mapping, read_mapping, root, track_manager)

    # Run
    root.mainloop()
    print("Done")
