#!/usr/bin/env python3
"""Copy the newest firmware .bin for every board from the source repos and write the install manifests.

Usage: python3 tools/sync.py <folder holding the checked-out source repos>

The source folder must contain one checkout per project repo, named after the repo
(W10-Beat-Conductor/, T-Scan/, W10-ISM-Waterfall/). For each board in boards.json the newest
firmware/<prefix>-v<version>[-<suffix>].bin is copied to firmware/, and manifests/<board id>.json
plus firmware.json (what the page shows) are regenerated. Old .bins that no board uses are removed.
"""
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def version_key(v):
    return tuple(int(x) for x in v.split("."))


def find_bin(repo_dir, prefix, suffix):
    fw = os.path.join(repo_dir, "firmware")
    if not os.path.isdir(fw):
        return None, None
    tail = ("-" + re.escape(suffix)) if suffix else ""
    pat = re.compile(r"^" + re.escape(prefix) + r"-v(\d+(?:\.\d+)*)" + tail + r"\.bin$")
    best = None
    for name in os.listdir(fw):
        m = pat.match(name)
        if m and (best is None or version_key(m.group(1)) > version_key(best[1])):
            best = (name, m.group(1))
    if not best:
        return None, None
    return os.path.join(fw, best[0]), best[1]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    cfg = json.load(open(os.path.join(SITE, "boards.json"), encoding="utf-8"))
    repos = {p["id"]: p["repo"].split("/")[-1] for p in cfg["projects"]}
    os.makedirs(os.path.join(SITE, "firmware"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "manifests"), exist_ok=True)

    out, used, problems = {}, set(), []
    for b in cfg["boards"]:
        path, ver = find_bin(os.path.join(src, repos[b["project"]]), b["prefix"], b.get("suffix"))
        if not path:
            problems.append(f"{b['id']}: no {b['prefix']}-v*{('-' + b['suffix']) if b.get('suffix') else ''}.bin found")
            continue
        name = os.path.basename(path)
        data = open(path, "rb").read()
        # merged images start with the bootloader header 0xE9: at 0x0 (S3/C3/...), 0x1000 (classic ESP32) or 0x2000 (P4)
        if not (data[:1] == b"\xe9" or any(len(data) > o and data[o:o + 1] == b"\xe9" for o in (0x1000, 0x2000))):
            problems.append(f"{b['id']}: {name} doesn't start with an ESP image header (0xE9); is it a merged .bin?")
            continue
        dst = os.path.join(SITE, "firmware", name)
        if not os.path.exists(dst) or open(dst, "rb").read() != data:
            shutil.copyfile(path, dst)
        used.add(name)
        manifest = {
            "name": f"{b['title']} ({b['board']})",
            "version": ver,
            "new_install_prompt_erase": True,      # let people keep their saved settings if they want
            "new_install_improv_wait_time": 0,     # these firmwares don't speak Improv: skip the 10 s wait
            "builds": [{"chipFamily": b["chip"], "parts": [{"path": f"../firmware/{name}", "offset": 0}]}],
        }
        with open(os.path.join(SITE, "manifests", b["id"] + ".json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.write("\n")
        out[b["id"]] = {"file": name, "version": ver, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()}

    for name in os.listdir(os.path.join(SITE, "firmware")):
        if name.endswith(".bin") and name not in used:
            os.remove(os.path.join(SITE, "firmware", name))
            print("removed old", name)

    prev = {}
    fj = os.path.join(SITE, "firmware.json")
    if os.path.exists(fj):
        prev = json.load(open(fj, encoding="utf-8")).get("boards", {})
    changed = {k for k in out if prev.get(k, {}).get("sha256") != out[k]["sha256"]}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for k, v in out.items():
        v["updated"] = stamp if k in changed else prev.get(k, {}).get("updated", stamp)
    with open(fj, "w", encoding="utf-8") as fh:
        json.dump({"boards": out}, fh, indent=2)
        fh.write("\n")

    for k in sorted(out):
        print(f"{k:28s} v{out[k]['version']:8s} {out[k]['file']}" + ("  (new)" if k in changed else ""))
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
