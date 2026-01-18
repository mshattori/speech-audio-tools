import os
from pydub import AudioSegment


def tag_album(dirname, album, output_dir="output"):
    if not os.path.isdir(dirname):
        raise ValueError(f'"{dirname}" is not a directory')
    os.makedirs(output_dir, exist_ok=True)
    for filename in sorted(os.listdir(dirname)):
        if not os.path.splitext(filename)[1] in (".mp3", ".m4a", ".wav"):
            continue
        filepath = os.path.join(dirname, filename)
        audio = AudioSegment.from_file(filepath)
        title = os.path.splitext(os.path.basename(filepath))[0]
        tags = {"title": title, "album": album, "artist": "Homebrew"}
        outfilename = os.path.join(output_dir, title + ".mp3")
        audio.export(outfilename, format="mp3", tags=tags, id3v2_version="3")
        print(f"Exported: {outfilename}")

