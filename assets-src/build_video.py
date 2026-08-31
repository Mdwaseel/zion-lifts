# -*- coding: utf-8 -*-
"""Transcode Zion project .mov masters into web-ready mp4 + poster + muted loop."""
import subprocess, pathlib, json, sys

ROOT = pathlib.Path(r"d:\Projects\Zion Lifts")
SRC  = ROOT / "videos-20260828T181837Z-1-004"
OUT  = ROOT / "frontend" / "public" / "media" / "video"
POST = ROOT / "frontend" / "public" / "media" / "poster"
OUT.mkdir(parents=True, exist_ok=True); POST.mkdir(parents=True, exist_ok=True)

# Each film opens on a white Zion title card. The poster already seeks past it;
# the background loops used to start at frame 0, so a featured project showed a
# white logo panel for its first few seconds. Loops now start at the same
# timestamp and run for LOOP_LEN, which also cuts them to a fraction of the size.
LOOP_LEN = 12

# slug : (filename fragment, poster timestamp seconds)
JOBS = [
    ("lacheta-nivas",      "Lacheta Nivas V F Video 1",       12),
    ("kashi-yadhav",       "Kasi Yadav V F Video",            14),
    ("chath-restaurant",   "Chath H Video O1",                10),
    ("lekha-nilayam",      "Lekha Nilayam H F Video",         16),
    ("niloufer-cafe",      "Testimonal-1_Niloufer F",         6),
    ("chilkuru-residence", "Chilukuru F House Final video",   14),
    ("owaisi-hospitals",   "Owaisi hospital Final Video",     12),
]

def find(frag):
    for p in SRC.rglob("*"):
        if p.suffix.lower() in (".mov",) and frag.lower() in p.name.lower():
            return p
    return None

def probe(p):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height","-of","json",str(p)],
        capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    return s["width"], s["height"]

def main():
    for slug, frag, ts in JOBS:
        src = find(frag)
        if not src:
            print("MISSING:", frag); continue
        w, h = probe(src)
        portrait = h > w
        # long edge -> 1280 for portrait (720x1280), 1920 for landscape
        vf = "scale=720:-2" if portrait else "scale=1920:-2"
        mp4 = OUT / f"{slug}.mp4"
        if not mp4.exists():
            print("encode", slug, f"{w}x{h}")
            subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(src),
                "-vf",vf,"-c:v","libx264","-preset","slow","-crf","25",
                "-pix_fmt","yuv420p","-movflags","+faststart",
                "-c:a","aac","-b:a","96k","-ac","2", str(mp4)], check=True)
        # muted, no-audio loop variant for background use
        loop = OUT / f"{slug}-loop.mp4"
        if not loop.exists():
            subprocess.run(["ffmpeg","-y","-loglevel","error",
                "-ss",str(ts),"-t",str(LOOP_LEN),"-i",str(src),
                "-vf",("scale=640:-2" if portrait else "scale=1280:-2"),
                "-an","-c:v","libx264","-preset","slow","-crf","28",
                "-pix_fmt","yuv420p","-movflags","+faststart", str(loop)], check=True)
        poster = POST / f"{slug}.jpg"
        if not poster.exists():
            subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(ts),"-i",str(src),
                "-vframes","1","-vf",("scale=900:-2" if portrait else "scale=1600:-2"),
                "-q:v","4", str(poster)], check=True)
        print("done", slug)
    print("ALL VIDEO DONE")


if __name__ == "__main__":
    main()
