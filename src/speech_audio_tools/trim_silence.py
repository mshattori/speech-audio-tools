import os
import subprocess
import time
import numpy as np
from pydub import AudioSegment


def analyze_volume_distribution(input_file):
    """Analyze volume distribution across the entire audio file."""
    audio = AudioSegment.from_file(input_file)
    segment_length = 1000  # 1 second
    segment_levels = []
    for i in range(0, len(audio), segment_length):
        segment = audio[i : i + segment_length]
        if len(segment) > 0:
            segment_samples = np.array(segment.get_array_of_samples())
            if segment.channels == 2:
                segment_samples = segment_samples.reshape((-1, 2))
                segment_samples = segment_samples.mean(axis=1)
            segment_float = segment_samples.astype(float) / (2**15)
            non_zero = segment_float[segment_float != 0]
            if len(non_zero) > 0:
                rms = np.sqrt(np.mean(non_zero**2))
                segment_dbfs = 20 * np.log10(rms) if rms > 0 else -60
            else:
                segment_dbfs = -60
            segment_levels.append(segment_dbfs)
    return np.array(segment_levels), len(audio) / 1000


def trim_with_ffmpeg(input_file, output_file, min_silence=1.0, threshold_db=-20):
    """Trim silence using FFmpeg."""
    original_audio = AudioSegment.from_file(input_file)
    original_length = len(original_audio) / 1000
    print(f'Original audio length: {original_length:.1f}s')
    ff_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-af",
        f"silenceremove=start_periods=1:start_silence={min_silence}:"
        f"start_threshold={threshold_db}dB:"
        f"stop_periods=-1:stop_silence={min_silence}:"
        f"stop_threshold={threshold_db}dB",
        output_file,
    ]
    start_time = time.time()
    print(f'Trimming silence from "{input_file}" with FFmpeg...')
    subprocess.run(ff_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    end_time = time.time()
    print(f"Processing time: {end_time - start_time:.2f} seconds")

    processed_audio = AudioSegment.from_file(output_file)
    processed_length = len(processed_audio) / 1000
    reduction = original_length - processed_length
    reduction_percent = (reduction / original_length) * 100
    print(f'Processed audio length: {processed_length:.1f}s')
    print(f"Reduced by: {reduction:.1f}s ({reduction_percent:.1f}%)")

