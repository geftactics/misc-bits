import os
import io
import base64
import struct
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, GEOB
from serato_crate.serato_crate import SeratoCrate

FMT_VERSION = 'BB'
OUTPUT_XML = "rekordbox.xml"

class CueEntry:
    NAME = 'CUE'
    FMT = '>cBIc3s2s'
    FIELDS = ('field1', 'index', 'position', 'field4', 'color', 'field6', 'name')

    def __init__(self, *args):
        for field, value in zip(self.FIELDS, args):
            setattr(self, field, value)

    @classmethod
    def load(cls, data):
        info_size = struct.calcsize(cls.FMT)
        info = struct.unpack(cls.FMT, data[:info_size])
        name, nullbyte, _ = data[info_size:].partition(b'\x00')
        return cls(*info, name.decode('utf-8'))

def parse_serato_markers2(data):
    versionlen = struct.calcsize(FMT_VERSION)
    version = struct.unpack(FMT_VERSION, data[:versionlen])
    if version != (0x01, 0x01):
        return []

    try:
        b64data = data[versionlen:data.index(b'\x00', versionlen)].replace(b'\n', b'')
        padding = b'=' * (-len(b64data) % 4)
        payload = base64.b64decode(b64data + padding)
    except Exception as e:
        raise ValueError(f"Invalid base64: {e}")

    fp = io.BytesIO(payload)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x01, 0x01)

    cues = []
    while True:
        entry_name_bytes = bytearray()
        while (b := fp.read(1)) and b != b'\x00':
            entry_name_bytes.extend(b)
        if not entry_name_bytes:
            break
        entry_name = entry_name_bytes.decode('utf-8')

        entry_len = struct.unpack('>I', fp.read(4))[0]
        entry_data = fp.read(entry_len)

        if entry_name == CueEntry.NAME:
            cues.append(CueEntry.load(entry_data))

    return cues

def create_track_element(track_id, filepath):
    filename = os.path.basename(filepath)
    location = "file://localhost" + quote(os.path.abspath(filepath))
    filepath2 = filepath.replace("/Users/geoff/Users/geoff/Music", "/Users/geoff/Library/Mobile Documents/com~apple~CloudDocs/Music")
    audio = MP3(filepath2)
    tags = ID3(filepath2)

    name = audio.get("TIT2", filename).text[0] if "TIT2" in audio else os.path.splitext(filename)[0]
    artist = audio.get("TPE1", [""])[0]
    album = audio.get("TALB", [""])[0]
    genre = audio.get("TCON")
    genre = genre.text[0] if genre and hasattr(genre, "text") and genre.text else ""
    bpm = float(audio.get("TBPM")[0]) if "TBPM" in audio else None
    comment = ""
    for comm in tags.getall("COMM"):
        if comm.desc == "" and comm.lang == "eng":
            comment = comm.text[0]
            break
    duration = int(audio.info.length)
    size = os.path.getsize(filepath2)

    track = ET.Element("TRACK", {
        "TrackID": str(track_id),
        "Name": name,
        "Artist": artist,
        "Composer": "",
        "Album": album,
        "Grouping": "",
        "Genre": genre,
        "Kind": "MP3 File",
        "Size": str(size),
        "TotalTime": str(duration),
        "DiscNumber": "0",
        "TrackNumber": "0",
        "Year": str(datetime.today().year),
        "AverageBpm": f"{bpm:.2f}" if bpm else "",
        "DateAdded": datetime.today().strftime("%Y-%m-%d"),
        "BitRate": str(audio.info.bitrate // 1000),
        "SampleRate": str(audio.info.sample_rate),
        "Comments": comment,
        "PlayCount": "0",
        "Rating": "0",
        "Location": location,
        "Remixer": "",
        "Tonality": "",
        "Label": "",
        "Mix": ""
    })

    if bpm:
        ET.SubElement(track, "TEMPO", {
            "Inizio": "0.000",
            "Bpm": f"{bpm:.2f}",
            "Metro": "4/4",
            "Battito": "1"
        })

    try:
        geob = tags["GEOB:Serato Markers2"].data
        cues = parse_serato_markers2(geob)
        for cue in cues:
            position_secs = cue.position / 1000.0
            r, g, b = cue.color[0], cue.color[1], cue.color[2]
            ET.SubElement(track, "POSITION_MARK", {
                "Name": cue.name,
                "Type": "0",
                "Start": f"{position_secs:.3f}",
                "Num": str(cue.index),
                "Red": str(r),
                "Green": str(g),
                "Blue": str(b)
            })
    except Exception as e:
        print(f"No cues for {filename}: {e}")

    return track

def build_rekordbox_xml(crate_path):
    crate = SeratoCrate.load(crate_path)
    crate_name = os.path.splitext(os.path.basename(crate_path))[0].replace("%%", "-")
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    ET.SubElement(root, "PRODUCT", {
        "Name": "rekordbox",
        "Version": "7.0.9",
        "Company": "AlphaTheta"
    })

    mp3_files = []

    for rel_path in crate.tracks:
        abs_path = os.path.join("/", rel_path)
        if abs_path.lower().endswith(".mp3"):
            mp3_files.append(abs_path)

    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(mp3_files)))
    for idx, filepath in enumerate(mp3_files, start=1):
        collection.append(create_track_element(idx, filepath))

    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", {
        "Type": "0", "Name": "ROOT", "Count": "1"
    })
    playlist = ET.SubElement(root_node, "NODE", {
        "Name": crate_name,
        "Type": "1",
        "KeyType": "0",
        "Entries": str(len(mp3_files))
    })

    for idx in range(1, len(mp3_files)+1):
        ET.SubElement(playlist, "TRACK", Key=str(idx))

    return root

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("crate", help="Path to Serato crate file (.crate)")
    args = parser.parse_args()

    print(f"Using Serato crate: {args.crate}")
    root = build_rekordbox_xml(args.crate)

    import xml.dom.minidom
    pretty = xml.dom.minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ")

    with open(OUTPUT_XML, "w", encoding="utf-8") as f:
        f.write(pretty)

    print(f"🎉 rekordbox.xml written to {OUTPUT_XML}")

if __name__ == "__main__":
    main()
