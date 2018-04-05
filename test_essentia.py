import sys
import essentia

import pyaudio

import socket

import threading
import Queue

import time

import wave

import essentia.standard
import essentia.streaming

from essentia.streaming import VectorInput
from essentia.streaming import RhythmExtractor2013
from essentia.standard import FrameGenerator 
UDP_IP = "10.42.1.254"
UDP_PORT = 65000 
CHUNK = 1024*100
FORMAT = pyaudio.paFloat32

class ExtractionThread(threading.Thread):
    def __init__(self, ed, ps):
        super(ExtractionThread, self).__init__()
        self.extract_done = ed
        self.play_started = ps
        self.stoprequest = threading.Event()

    def run(self):
        loader = essentia.standard.MonoLoader(filename = sys.argv[1])()

        msg = "0"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for frame in FrameGenerator(loader, frameSize = CHUNK, hopSize = 512, startFromZero=True):
            if self.stoprequest.isSet():
                break
            else:
                print "e wait"
                self.play_started.get()
            print "e start"
            v_in = VectorInput(frame)
            beat_tracker = RhythmExtractor2013(method="degara")
            pool = essentia.Pool()
            v_in.data >> beat_tracker.signal
            beat_tracker.ticks >> (pool, 'Rhythm.ticks')
            beat_tracker.bpm >> (pool, 'Rhythm.bpm')
            beat_tracker.confidence >> None 
            beat_tracker.estimates >> None 
            beat_tracker.bpmIntervals >> None 
            essentia.run(v_in)

            bpm = pool['Rhythm.bpm']
            bps = bpm / 60.0

            next_beat = time.time() + bps

            sock.sendto(str(next_beat), (UDP_IP, UDP_PORT))

            print "beats: ", pool['Rhythm.ticks']
            print "bpm: ", pool['Rhythm.bpm']
            print "bps: ", bps
            print "next_beat: ", next_beat
            print "time: ", time.clock()
            print "e done"
            self.extract_done.put(True)

    def stop(self):
        self.stoprequest.set()


class PlayingThread(threading.Thread):
    def __init__(self, ed, ps):
        super(PlayingThread, self).__init__()
        self.extract_done = ed
        self.play_started = ps
        self.stoprequest = threading.Event()

    def run(self):
        wf = wave.open(sys.argv[1], 'rb')

        p = pyaudio.PyAudio()

        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True)
        data = wf.readframes(CHUNK)
        while len(data) > 0:
            print "p start"
            self.play_started.put(True)
            stream.write(data)
            data = wf.readframes(CHUNK)
            if self.stoprequest.isSet():
                break
            else:
                print "p wait"
                self.extract_done.get()
            print "p continue"

        # stop stream (4)
        stream.stop_stream()
        stream.close()

        # close PyAudio (5)
        p.terminate()

    def stop(self):
        self.stoprequest.set()



def play():
    if len(sys.argv) < 2:
        print("Supports 16 bit wave file. Use %s filename.wav" % sys.argv[0])
        sys.exit(-1)
    play_started = Queue.Queue()
    extract_done = Queue.Queue()
    pt = PlayingThread(extract_done, play_started)
    et = ExtractionThread(extract_done, play_started)
    pt.daemon = True
    et.daemon = True
    pt.start()
    et.start()
    while True:
        try:
            pt.join(1)
            et.join(1)
            print "alive"
            if not pt.isAlive() and not et.isAlive():
                break
        except (KeyboardInterrupt, SystemExit):
            print "interupt"
            pt.stop()
            et.stop()
            sys.exit()

if __name__ == '__main__':
    play()

