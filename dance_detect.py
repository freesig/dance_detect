import sys
import essentia

import pyaudio

import socket

import threading
import Queue


from multiprocessing.pool import ThreadPool

import time

import wave

import essentia.standard
import essentia.streaming

from essentia.streaming import VectorInput
from essentia.streaming import RhythmExtractor2013
from essentia.standard import Energy 
from essentia.streaming import OnsetRate
from essentia.standard import FrameGenerator 
UDP_IP = "10.42.1.254"
UDP_PORT = [55000, 54000, 52000]
LENGTH = 100
CHUNK = 1024 * LENGTH 
FORMAT = pyaudio.paFloat32

frame_g = None


class BeatThread(threading.Thread):
    def __init__(self, f_q, r_q):
        super(BeatThread, self).__init__()
        self.frame_q = f_q
        self.result_q = r_q
        self.stoprequest = threading.Event()
    
    def run(self):
        global frame_g
        while not self.stoprequest.isSet():
            pool = essentia.Pool()
            self.frame_q.get()
            v_in = VectorInput(frame_g)
            beat_tracker = RhythmExtractor2013(method="degara")
            v_in.data >> beat_tracker.signal
            beat_tracker.ticks >> (pool, 'Rhythm.ticks')
            beat_tracker.bpm >> (pool, 'Rhythm.bpm')
            beat_tracker.confidence >> None 
            beat_tracker.estimates >> None 
            beat_tracker.bpmIntervals >> None 
            essentia.run(v_in)
            self.result_q.put(pool)

    def stop(self):
        self.stoprequest.set()

class OnsetThread(threading.Thread):
    def __init__(self, f_q, r_q):
        super(OnsetThread, self).__init__()
        self.frame_q = f_q
        self.result_q = r_q
        self.stoprequest = threading.Event()
    
    def run(self):
        global frame_g
        while not self.stoprequest.isSet():
            pool = essentia.Pool()
            self.frame_q.get()
            v_in2 = VectorInput(frame_g)
            onset = OnsetRate()
            v_in2.data >> onset.signal 
            onset.onsetRate >> (pool, 'Rhythm.onsetRate')
            onset.onsetTimes >> None
            essentia.run(v_in2)
            self.result_q.put(pool)

    def stop(self):
        self.stoprequest.set()

class ExtractionThread(threading.Thread):
    def __init__(self, ed, ps):
        super(ExtractionThread, self).__init__()
        self.extract_done = ed
        self.play_started = ps
        self.stoprequest = threading.Event()
    

    def run(self):

        loader = essentia.standard.MonoLoader(filename = sys.argv[1])()

        msg = "0"

        socks = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
        beat_count = 0
        N_BEATS = 4
        global frame_g
        frame_q_o = Queue.Queue()
        result_q_o = Queue.Queue()
        frame_q_b = Queue.Queue()
        result_q_b = Queue.Queue()
        ot = OnsetThread(frame_q_o, result_q_o)
        bt = BeatThread(frame_q_b, result_q_b)
        ot.daemon = True
        bt.daemon = True
        ot.start()
        bt.start()

        for frame in FrameGenerator(loader, frameSize = CHUNK, hopSize = CHUNK, startFromZero=True):
            frame_g = frame
            if self.stoprequest.isSet():
                break
            else:
                self.play_started.get()
            
            start_time =  time.time()
            
            frame_q_b.put(True)
            frame_q_o.put(True)

            energy = Energy()
            frame_energy = energy(frame)
            pool2 = result_q_o.get()
            pool = result_q_b.get()


            bpm = pool['Rhythm.bpm']
            spb = 60.0 / bpm if bpm > 0 else 0.0
            look_ahead_n = 16
            beats = pool['Rhythm.ticks']
            onset = pool2['Rhythm.onsetRate']

            for i, b in enumerate(beats):
                beat_count += 1
                if(beat_count % N_BEATS == 0):
                    half_beat = start_time + b + spb * (look_ahead_n / 2)
                    next_beat = start_time + b + spb * look_ahead_n

                    for i, sock in enumerate(socks):
                        sock.sendto(str(half_beat) + "," + str(frame_energy) + "," + str(onset),
                                (UDP_IP, UDP_PORT[i]))
                        sock.sendto(str(next_beat) + "," + str(frame_energy) + "," + str(onset),
                                (UDP_IP, UDP_PORT[i]))
                    

            '''
            print "beats: ", pool['Rhythm.ticks']
            print "energy: ", frame_energy 
            print "onset: ", pool2['Rhythm.onsetRate']
            print "bpm: ", pool['Rhythm.bpm']
            print "spb: ", spb
            print "bar started: ", start_time
            print "time now: ", time.time()
            print "next_beat: ", next_beat
            '''
            self.extract_done.put(True)
        ot.stop()
        bt.stop()

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
            self.play_started.put(True)
            stream.write(data)
            data = wf.readframes(CHUNK)
            if self.stoprequest.isSet():
                break
            else:
                self.extract_done.get()

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
            if not pt.isAlive() and not et.isAlive():
                break
        except (KeyboardInterrupt, SystemExit):
            print "interupt"
            pt.stop()
            et.stop()
            sys.exit()

if __name__ == '__main__':
    play()

