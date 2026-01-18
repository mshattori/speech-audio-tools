import numpy as np
from pydub import AudioSegment


def make_beep(
    output_file="beep.mp3",
    frequency=880,
    duration=0.25,
    amplitude=0.5,
    sampling_rate=44100,
    gain_db=10.0,
):
    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    sine_wave = amplitude * np.sin(2 * np.pi * frequency * t)
    audio_segment = AudioSegment(
        (sine_wave * frequency).astype(np.int16).tobytes(),
        frame_rate=sampling_rate,
        sample_width=2,
        channels=1,
    )
    audio_segment = audio_segment.apply_gain(volume_change=gain_db)
    audio_segment.export(output_file, format="mp3")
    return output_file

