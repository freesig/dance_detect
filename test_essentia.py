import sys
import essentia

import essentia.standard
import essentia.streaming

from essentia.streaming import VectorInput
from essentia.streaming import RhythmExtractor2013
from essentia.standard import FrameGenerator 

if len(sys.argv) < 2:
    print("Supports 16 bit wave file. Use %s filename.wav" % sys.argv[0])
    sys.exit(-1)
loader = essentia.standard.MonoLoader(filename = sys.argv[1])()

for frame in FrameGenerator(loader, frameSize = 100*1024, hopSize = 512, startFromZero=True):
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

    print "beats: ", pool['Rhythm.ticks']
    print "bpm: ", pool['Rhythm.bpm']

