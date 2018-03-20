import pyaudio
import wave
import sys
import struct
import rospy
from std_msgs.msg import String

def detect():
    CHUNK = 1024
    MIN_VAL = -32768
    MAX_VAL = 32767
    RANGE = float(MAX_VAL - MIN_VAL)
    EVENT_TRIGGER = 0.9

    if len(sys.argv) < 2:
        print("Supports 16 bit wave file. Use %s filename.wav" % sys.argv[0])
        sys.exit(-1)

    pub = rospy.Publisher('dance', String, queue_size=10)
    rospy.init_nade('dance_detect', anonymous=True)

    wf = wave.open(sys.argv[1], 'rb')
    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True)
    sample_width = wf.getsampwidth()
    total_samples = CHUNK * wf.getnchannels()
    """
    #if we want 8 bit support
    if sample_width == 1:
    fmt = "%iB" % total_samples # read unsigned chars
    """

    if sample_width == 2:
        fmt = "%ih" % total_samples
    else:
        raise ValueError("Only supports 16 bit wave")

    norm = lambda x: (x - MIN_VAL) / RANGE
    max_norm = norm(MAX_VAL)
    above = lambda x: (x - EVENT_TRIGGER) / (max_norm - EVENT_TRIGGER)

    data = wf.readframes(CHUNK)

    while data != '':
        stream.write(data)
        int_data = struct.unpack(fmt, data)
        volume = norm( max(int_data) )
        if volume > EVENT_TRIGGER:
          print "Event by: ", above(volume), " volume: ", volume
          pub.publish( above(volume) )

        data = wf.readframes(CHUNK)

    stream.stop_stream()
    stream.close()

    p.terminate()

if __name__ == '__main__':
    try:
        detect()
    except rospy.ROSInterruptException:
        pass
