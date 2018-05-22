# dance_detect
This project is designed to be used with [Baxter Boogie](https://github.com/freesig/baxter_boogie).
It uses the [Essentia](http://essentia.upf.edu/documentation/) library to extract information 
from music for a robot to respond to.
It also plays the song.
__Requires python 2.7__

## Information
- __Beats:__ It extracts beat information from the current fram of music and makes a prediction of 
when a beat will occur in the future.
- __Energy:__ It extracts the amount of energy in the current frame buffer. 
- __Onset:__ It extracts the number of new music onsets on the frame buffer.

## Usage
1. Place a __wav__ file in a subdirectory called "samples". _(So dance_detect/samples/my_music.wav)_
2. Set the IP of robot running Baxter Boogie and a port to use
3. Run with `python dance_detect.py /samples/some_music.wav`
