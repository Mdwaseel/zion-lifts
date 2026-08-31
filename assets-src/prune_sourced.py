# -*- coding: utf-8 -*-
"""Keep only the sourced images that actually read as Zion's subject matter.

Openverse matches on loose text, so most results were wrong (the "hospital
lift" was a church, the "macro gears" a pile of bicycles). Everything not on
KEEP is deleted rather than shipped. What survives is documentary-grade
supporting imagery, flagged in ATTRIBUTION.md for replacement by a real shoot.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "media" / "sourced"
MANIFEST = ROOT / "assets-src" / "sourced-manifest.json"
ATTR = ROOT / "frontend" / "public" / "media" / "ATTRIBUTION.md"

KEEP = {
    "factory-machining":  "Home 10 / About 07 - machining",
    "factory-welding":    "Home 10 / About 07 - welding",
    "factory-floor":      "About 03 - archival factory floor",
    "factory-assembly":   "About 07 - dispatch",
    "macro-circuit":      "Home 05 - control board",
    "macro-sensor":       "Home 05 - sensors",
    "macro-bearing":      "Home 05 - precision measurement",
    "macro-brake":        "Home 14 - hands at work",
    "people-team":        "Home 14 / About 11 - site engineers",
    "people-engineer":    "Home 14 - installation team",
    "people-electrician": "Home 05 - plant / controls",
    "people-drafting":    "Home 08 - blueprint stage",
    "blueprint-technical": "Home 08 - blueprint stage",
    "skyline-city":       "Home 16 - final ascent plate",
    "skyline-hyderabad":  "Home 16 - Hyderabad skyline",
}

LICENCE_URL = {
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "PDM": "https://creativecommons.org/publicdomain/mark/1.0/",
    "BY": "https://creativecommons.org/licenses/by/4.0/",
    "BY-SA": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    removed = 0
    for slug in list(manifest):
        if slug in KEEP:
            continue
        for f in OUT.glob(f"{slug}*"):
            f.unlink()
        manifest.pop(slug)
        removed += 1
    for slug in KEEP:
        if slug in manifest:
            manifest[slug]["used_for"] = KEEP[slug]
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Third-party image attribution",
        "",
        "Every photograph of a Zion lift, cabin, project or installation on this site is",
        "Zion's own. The images below are Creative Commons stand-ins used only in the",
        "factory, component-macro and people sections, where Zion has not yet supplied a",
        "shoot. **All of them should be replaced with real Zion photography before launch** —",
        "the brief explicitly calls for authentic footage in these sections.",
        "",
        "| Asset | Used for | Creator | Licence | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for slug, m in sorted(manifest.items()):
        lic = m.get("license", "")
        ver = m.get("license_version", "")
        url = m.get("license_url") or LICENCE_URL.get(lic, "")
        label = f"CC {lic} {ver}".strip() if lic not in ("CC0", "PDM") else lic
        licence_cell = f"[{label}]({url})" if url else label
        creator = m.get("creator") or "Unknown"
        if m.get("creator_url"):
            creator = f"[{creator}]({m['creator_url']})"
        src = m.get("foreign_landing_url") or ""
        src_cell = f"[{m.get('source', 'source')}]({src})" if src else m.get("source", "")
        lines.append(
            f"| `{slug}` | {m.get('used_for', '')} | {creator} | {licence_cell} | {src_cell} |"
        )
    lines += [
        "",
        "CC BY and CC BY-SA require the credit above to remain visible wherever the image",
        "is published. CC BY-SA additionally requires that modified versions carry the same",
        "licence — so those assets must not be composited into artwork Zion wants to own.",
        "",
        f"_{len(manifest)} sourced assets; {removed} rejected during review._",
    ]
    ATTR.write_text("\n".join(lines), encoding="utf-8")
    print(f"kept {len(manifest)}, removed {removed}")
    print(f"attribution -> {ATTR}")


if __name__ == "__main__":
    main()
