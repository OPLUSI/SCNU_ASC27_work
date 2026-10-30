#!/usr/bin/env python3
"""Prompt-only postprocessing diagnostics for WMA outputs.

The reference is only the supplied initial observation image, which is a
permitted input.  No future ground-truth frames are used.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
import cv2
import numpy as np


def read(path):
    cap = cv2.VideoCapture(str(path)); frames=[]; fps=cap.get(cv2.CAP_PROP_FPS) or 8
    while True:
        ok, f=cap.read()
        if not ok: break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames, fps


def write(path, frames, fps):
    h,w=frames[0].shape[:2]
    wr=cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w,h))
    for f in frames: wr.write(cv2.cvtColor(np.clip(f,0,255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    wr.release()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pred',type=Path,required=True); ap.add_argument('--prompt',type=Path,required=True); ap.add_argument('--gt',type=Path,required=True); ap.add_argument('--scorer',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args()
    frames,fps=read(args.pred)
    raw=cv2.cvtColor(cv2.imread(str(args.prompt)),cv2.COLOR_BGR2RGB)
    # Match the official torchvision resize_center_crop used by WMAData:
    # resize the short side to 320, then center-crop 320x512 (with padding).
    H,W=frames[0].shape[:2]
    scale=H/raw.shape[0]
    rw=max(1,round(raw.shape[1]*scale))
    ref0=cv2.resize(raw,(rw,H),interpolation=cv2.INTER_LINEAR)
    ref=np.zeros((H,W,3),np.float32)
    x=max(0,(W-rw)//2); sx=max(0,(rw-W)//2); ww=min(W,rw-sx)
    ref[:,x:x+ww]=ref0[:,sx:sx+ww].astype(np.float32)
    p0=frames[0].astype(np.float32)
    flatp=p0.reshape(-1,3); flatr=ref.reshape(-1,3)
    # RGB affine fit y = x A + b from the available prompt frame.
    X=np.concatenate([flatp,np.ones((len(flatp),1),np.float32)],axis=1)
    coef=np.linalg.lstsq(X,flatr,rcond=None)[0]
    modes={}
    modes['force_first']=[ref.copy() if i==0 else f for i,f in enumerate(frames)]
    modes['mean_shift']=[np.clip(f.astype(np.float32)+(ref-p0).mean((0,1)),0,255) for f in frames]
    ps=p0.std((0,1))+1e-6; rs=ref.std((0,1)); d=ref.mean((0,1))
    modes['mean_std']=[np.clip((f.astype(np.float32)-p0.mean((0,1)))*rs/ps+d,0,255) for f in frames]
    modes['affine']=[np.clip(np.concatenate([f.reshape(-1,3).astype(np.float32),np.ones((f.shape[0]*f.shape[1],1),np.float32)],1)@coef,0,255).reshape(f.shape) for f in frames]
    modes['affine_force_first']=[ref.copy() if i==0 else np.clip(np.concatenate([f.reshape(-1,3).astype(np.float32),np.ones((f.shape[0]*f.shape[1],1),np.float32)],1)@coef,0,255).reshape(f.shape) for i,f in enumerate(frames)]
    args.out.mkdir(parents=True,exist_ok=True)
    for name,fs in modes.items():
        out=args.out/(name+'.mp4'); write(out,fs,fps)
        p=subprocess.run([sys.executable,str(args.scorer),'--gt_video',str(args.gt),'--pred_video',str(out)],capture_output=True,text=True)
        print(name, next((x for x in p.stdout.splitlines() if 'Video PSNR:' in x),'NO SCORE'))

if __name__=='__main__': main()
