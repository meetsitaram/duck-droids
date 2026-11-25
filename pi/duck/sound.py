"""The duck's voice: play one of microduck's emotion sounds by name (pi/sounds/microduck/, from Pollen Robotics, Apache-2.0: see
pi/sounds/README.md). No extra package. One sound at a time: a new one cuts off the one playing, as on Pollen's robot.

On the Pi the sound goes to the default audio output: the Bluetooth speaker once bt_speaker.sh has paired it (the Pi Zero 2 W has no
headphone jack). It plays through the first player found: pw-play (PipeWire), paplay (PulseAudio or pipewire-pulse), then aplay (ALSA).
On Windows it plays through winsound, on macOS through afplay, so the sounds can be tried on the PC.

  python -m duck.sound --list          the sound names
  python -m duck.sound yes             plays yes.wav and waits for it to end
  python -m duck.sound --all           plays each in turn
  python -m duck.sound /path/to/x.wav  any wav file

From code:
  from duck import sound
  sound.play('laugh')                  returns at once; sound.play('laugh', wait=True) blocks until it ends
  sound.stop()
"""
import os
import shutil
import subprocess
import sys
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
SOUNDS = os.path.join(os.path.dirname(HERE), 'sounds', 'microduck')

_child = None                                   # the player process now playing (Linux and macOS)


def names():
    """The sound names, from the wav files in pi/sounds/microduck/."""
    return sorted(f[:-4] for f in os.listdir(SOUNDS) if f.endswith('.wav'))


def path(name):
    """A sound's file: a name from names(), or a path to any wav."""
    if os.path.isfile(name):
        return name
    p = os.path.join(SOUNDS, name + '.wav')
    if not os.path.isfile(p):
        raise ValueError(f'no sound {name!r}: one of {", ".join(names())}')
    return p


def duration(name):
    with wave.open(path(name)) as w:
        return w.getnframes() / w.getframerate()


def _player():
    if sys.platform == 'darwin':
        return ['afplay']
    for cmd in (['pw-play'], ['paplay'], ['aplay', '-q']):
        if shutil.which(cmd[0]):
            return cmd
    raise RuntimeError('no audio player: install pipewire-bin, pulseaudio-utils or alsa-utils (setup_pi.sh does)')


def stop():
    global _child
    if sys.platform == 'win32':
        import winsound
        winsound.PlaySound(None, 0)
    elif _child is not None and _child.poll() is None:
        _child.terminate()
        try:
            _child.wait(1)
        except subprocess.TimeoutExpired:
            _child.kill()
    _child = None


def play(name, wait=False):
    """Play a sound by name (or a wav path), cutting off any sound still playing. Returns at once unless wait=True."""
    global _child
    p = path(name)
    stop()
    if sys.platform == 'win32':
        import winsound
        winsound.PlaySound(p, winsound.SND_FILENAME | (0 if wait else winsound.SND_ASYNC))
        return
    _child = subprocess.Popen(_player() + [p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if wait:
        _child.wait()


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    if argv[0] == '--list':
        for n in names():
            print(f'{n:12s} {duration(n):4.1f} s')
        return 0
    todo = names() if argv[0] == '--all' else argv
    for n in todo:
        print(n)
        play(n, wait=True)
        time.sleep(0.3)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
