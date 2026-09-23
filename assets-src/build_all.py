# -*- coding: utf-8 -*-
"""Rebuild frontend/public/media from the source masters.

The generated tree is ~164 MB and is not in version control, so run this once
after a clone (and again whenever a master changes):

    python assets-src/build_all.py

Requires ffmpeg on PATH, plus Pillow and numpy. Video transcoding is the slow
step — roughly ten minutes for the seven project films — and is skipped for any
output that already exists.
"""
import importlib
import shutil
import sys
import time

STEPS = [
    ("brand",   "build_brand",  "logo cut-outs, light and dark"),
    ("chatbot", "build_chatbot", "the assistant's mascot, launcher-sized"),
    ("images",  "build_images", "interiors, product renders, project photo"),
    ("frames",  "build_frames", "stills pulled from the 4K project masters"),
    ("video",   "build_video",  "web-ready mp4 + poster + muted loop"),
]

OPTIONAL = [
    ("sourced", "fetch_openverse", "CC-licensed stand-ins (needs network)"),
    ("prune",   "prune_sourced",   "drop the unusable ones, write ATTRIBUTION.md"),
]


def run(module_name, label):
    print(f"\n=== {label} " + "=" * max(0, 58 - len(label)))
    started = time.time()
    module = importlib.import_module(module_name)
    module.main()
    print(f"--- {label}: {time.time() - started:.1f}s")


def main():
    only = set(sys.argv[1:])
    steps = STEPS + OPTIONAL if "--with-sourced" in only else STEPS
    only.discard("--with-sourced")

    selected = [key for key, _, _ in steps if not only or key in only]
    if not selected:
        print(f"Nothing to do. Known steps: {', '.join(k for k, _, _ in steps)}", file=sys.stderr)
        return 1

    # Only the video and frame steps shell out to ffmpeg. Demanding it for all
    # of them meant a contributor without it could not rebuild the logo or the
    # assistant's mascot either.
    if {"video", "frames"} & set(selected) and not shutil.which("ffmpeg"):
        print("ffmpeg is not on PATH — install it before running this.", file=sys.stderr)
        return 1

    for key, module_name, label in steps:
        if only and key not in only:
            continue
        try:
            run(module_name, label)
        except Exception as e:
            print(f"!! {key} failed: {e}", file=sys.stderr)
            return 1

    print("\nAll assets rebuilt -> frontend/public/media")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    sys.exit(main())
