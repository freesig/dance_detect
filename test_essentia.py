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

        for frame in FrameGenerator(loader, frameSize = CHUNK, hopSize = CHUNK, startFromZero=True):
            if self.stoprequest.isSet():
                break
            else:
                self.play_started.get()
            
            start_time =  time.time()
            pool2 = essentia.Pool()
            pool = essentia.Pool()
            def beat_call():
                v_in = VectorInput(frame)
                beat_tracker = RhythmExtractor2013(method="degara")
                v_in.data >> beat_tracker.signal
                beat_tracker.ticks >> (pool, 'Rhythm.ticks')
                beat_tracker.bpm >> (pool, 'Rhythm.bpm')
                beat_tracker.confidence >> None 
                beat_tracker.estimates >> None 
                beat_tracker.bpmIntervals >> None 
                essentia.run(v_in)

            def onset_call():
                v_in2 = VectorInput(frame)
                onset = OnsetRate()
                v_in2.data >> onset.signal 
                onset.onsetRate >> (pool2, 'Rhythm.onsetRate')
                onset.onsetTimes >> None
                essentia.run(v_in2)
            
            beat_thread = threading.Thread(target=beat_call, args=())
            onset_thread = threading.Thread(target=onset_call, args=())
            beat_thread.daemon = True
            onset_thread.daemon = True
            #print "time1: ", time.time()
            beat_thread.start()
            #print "time2: ", time.time()
            onset_thread.start()
            #print "time3: ", time.time()


            energy = Energy()
            frame_energy = energy(frame)
            beat_thread.join()
            onset_thread.join()


            bpm = pool['Rhythm.bpm']
            spb = 60.0 / bpm if bpm > 0 else 0.0
            look_ahead_n = 16
            beats = pool['Rhythm.ticks']
            onset = pool2['Rhythm.onsetRate']

            for i, b in enumerate(beats):
                beat_count += 1
                if(beat_count % N_BEATS == 0):
                    next_beat = start_time + b + spb * look_ahead_n

                    for i, sock in enumerate(socks):
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

