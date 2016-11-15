"""Controls serial input/output and can run a simulation via virtually linked com ports"""
import serial
import random
import time


class SerialManager:
    """Controls the serial input and output.
    Consist of two dictionaries, a tkinter widget or root to call the read function.
    write_mapping for output is Dict[Track Dict] where the inner dict has the header associated with the piece, and
    the bit associated with setting and resetting the track.
    read_mapping for input is a Dict[str TrackGroup]
    delay is between calls of read() in ms"""
    def __init__(self, port, write_mapping, read_mapping, tk_caller, header_len=3, delay=100):
        self.com = serial.Serial(port, timeout=0, write_timeout=0)
        self.write_mapping = write_mapping
        self.read_mapping = read_mapping
        self.header_len = header_len
        self.delay = delay
        self.tk_caller = tk_caller
        self.read()

    def write(self, changed_object):
        """Takes a track piece and writes the change correct bit to com."""
        if changed_object not in self.write_mapping:
            return
        header = self.write_mapping[changed_object]["HEADER"]
        bit = self.write_mapping[changed_object][changed_object.set]
        byte = "".join(("0" if i != bit else "1" for i in range(8)))
        if not self.com.write("{header}{byte}\n".format(header=header, byte=byte).encode()):
            # Writes or prints error message
            print("Writing {header}{byte} failed".format(header=header, byte=byte))

    def read(self):
        """Called by tkinter, and sets itself to be called again.
        Reads and processes all messages in the pipeline. It sends them to a TrackGroups set method to change track
        pieces.
        To invert a track piece have it set initially in the layout definition."""
        while self.com.in_waiting:
            data = self.com.readline().strip(b"\n").decode()
            header = data[:self.header_len]
            byte = data[self.header_len:]
            if header in self.read_mapping:
                for i, group in enumerate(self.read_mapping[header]):
                    group.set(int(byte[i]))
        self.tk_caller.after(self.delay, self.read)


if __name__ == '__main__':
    # A test simulating serial input. Run this file at the same time as main.
    # Test read/writes to COM4 which is virtually linked to COM3 for the main Railway Manager.
    com4 = serial.Serial("COM4")
    USER = "USER"
    RANDOM = "RANDOM"
    mode = USER

    if mode == USER:
        while 1:
            data = input("Input>")
            for _ in range(11 - len(data)):
                data += "0"
            data += "\n"
            com4.write(data.encode())
            print("Read from serial:", com4.read_all().decode(), sep="\n")
    elif mode == RANDOM:
        # Tests a high input rate to check the track remains responsive.
        while 1:
            header = "PRA"
            data = "".join((random.choice(("0", "1")) for _ in range(8)))
            com4.write("{}{}\n".format(header, data).encode())
            header = "PRB"
            data = "".join((random.choice(("0", "1")) for _ in range(8)))
            com4.write("{}{}\n".format(header, data).encode())
            if com4.in_waiting:
                print("Read from serial:", com4.read_all().decode(), sep="\n")
            time.sleep(0.001)
