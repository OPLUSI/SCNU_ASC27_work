#!/usr/bin/env python3
"""Build and score alternative temporal stitchings of per-round WMA videos.

This is for diagnosing evaluation conventions.  The official challenge output
is the ``official`` mode; the other modes are diagnostic only.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import imageio.v2 as imageio


def read_video(path: Path):
    cap = cv2.VideoCapture(str(path))
    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS) or 8.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    if not frames:
        raise RuntimeError(f"no frames: {path}")
    return frames, fps


def stitch(rounds, mode: str):
    if mode == "official":
        out = [f for r in rounds for f in r]
    elif mode == "drop_first":
        out = list(rounds[0])
        out.extend(f for r in rounds[1:] for f in r[1:])
    elif mode == "first_repeat":
        out = list(rounds[0]) * len(rounds)
    elif mode == "last_repeat":
        out = list(rounds[-1]) * len(rounds)
    elif mode == "round_starts":
        out = [r[0] for r in rounds]
    elif mode.startswith("freeze_"):
        k = int(mode.split("_")[-1])
        base = [f for r in rounds[:k] for f in r]
        out = base + [base[-1]] * (sum(map(len, rounds)) - len(base))
    elif mode.startswith("cycle_"):
        k = int(mode.split("_")[-1])
        base = [f for r in rounds[:k] for f in r]
        out = [base[i % len(base)] for i in range(sum(map(len, rounds)))]
    elif mode.startswith("hold_"):
        k = int(mode.split("_")[-1])
        base = [f for r in rounds[:k] for f in r]
        out = base + [base[-1]] * (sum(map(len, rounds)) - len(base))
    else:
        raise ValueError(mode)
    return out


def score(scorer: Path, gt: Path, pred: Path):
    p = subprocess.run(
        [sys.executable, str(scorer), "--gt_video", str(gt), "--pred_video", str(pred)],
        text=True, capture_output=True, check=False,
    )
    val = None
    for line in p.stdout.splitlines():
        if "Video PSNR:" in line:
            val = float(line.split(":", 1)[1].split()[0])
    return val, p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round-dir", type=Path, required=True)
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--scorer", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--fps", type=int, default=8)
    args = ap.parse_args()
    rounds = []
    for p in sorted(args.round_dir.glob("itr-*.mp4"), key=lambda p: int(p.stem.split("-")[-1])):
        frames, _ = read_video(p)
        rounds.append(frames)
    if not rounds:
        raise SystemExit("no itr-*.mp4 files")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    modes = ["official", "drop_first", "first_repeat", "last_repeat", "round_starts"]
    modes += [f"freeze_{k}" for k in range(1, len(rounds)+1)]
    modes += [f"cycle_{k}" for k in range(1, min(4, len(rounds))+1)]
    for mode in modes:
        frames = stitch(rounds, mode)
        out = args.out_dir / f"{mode}.mp4"
        imageio.mimsave(out, frames, fps=args.fps, codec="libx264", quality=8)
        val, log = score(args.scorer, args.gt, out)
        result[mode] = {"frames": len(frames), "psnr": val, "log": log}
    (args.out_dir / "stitch_scores.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
