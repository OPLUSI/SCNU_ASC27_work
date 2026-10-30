from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--gt-root',type=Path,required=True); ap.add_argument('--scorer',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args()
    rows=[]
    for scene in sorted(args.root.iterdir()):
        if not scene.is_dir(): continue
        for pred in sorted(scene.glob('case*.mp4')):
            case=pred.stem
            gt=args.gt_root/scene.name/case/f'{scene.name}_{case}.mp4'
            r=subprocess.run([sys.executable,str(args.scorer),'--gt_video',str(gt),'--pred_video',str(pred)],capture_output=True,text=True)
            score=None
            for line in r.stdout.splitlines():
                if 'Video PSNR:' in line: score=float(line.split(':',1)[1].split()[0])
            import cv2
            cap=cv2.VideoCapture(str(pred)); fps=cap.get(cv2.CAP_PROP_FPS); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); dur=n/fps if fps else None; cap.release()
            rows.append({'scene':scene.name,'case':case,'pred_video':str(pred),'gt_video':str(gt),'frames':n,'fps':fps,'duration_s':dur,'psnr_db':score,'passes':score is not None and score>=25.0})
    result={'threshold_db':25.0,'evaluation_note':'The challenge scorer compares only min(gt_duration,pred_duration); candidate durations are therefore reported explicitly.','results':rows,'all_pass':all(x['passes'] for x in rows)}
    args.out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
