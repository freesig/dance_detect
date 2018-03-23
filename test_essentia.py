import sys
import essentia

import essentia.standard
import essentia.streaming

from essentia.streaming import MonoLoader
from essentia.streaming import VectorInput
from essentia.streaming import BeatTrackerDegara
from essentia.standard import FrameGenerator

#print dir(essentia.standard)

if len(sys.argv) < 2:
    print("Supports 16 bit wave file. Use %s filename.wav" % sys.argv[0])
    sys.exit(-1)
loader = essentia.standard.MonoLoader(filename = sys.argv[1])()
beat_tracker = BeatTrackerDegara()

pool = essentia.Pool()
print "made it"
for frame in FrameGenerator(loader, frameSize = 100*1024, hopSize = 512, startFromZero=True):
    v_in = VectorInput(frame)
    v_in.data >> beat_tracker.signal
    beat_tracker.ticks >> (pool, 'Rhythm.ticks')

    essentia.run(v_in)

    print "beats: ", pool['Rhythm.ticks']

