# dance_detect
This project is designed to be used with [Baxter Boogie](https://github.com/freesig/baxter_boogie).
It uses the [Essentia](http://essentia.upf.edu/documentation/) library to extract information 
from music for a robot to respond to.
It also plays the song.

## Information
- __Beats:__ It extracts beat information from the current fram of music and makes a prediction of 
when a beat will occur in the future.
- __Energy:__ It extracts the amount of energy in the current frame buffer. 
- __Onset:__ It extracts the number of new music onsets on the frame buffer.


