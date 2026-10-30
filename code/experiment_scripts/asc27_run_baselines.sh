#!/usr/bin/env bash
set -u
ROOT=/root/asc27_system_results
PROJECT=/root/autodl-tmp/unifolm-world-model-action
PYTHON=/root/autodl-tmp/miniconda3/envs/asc_wma/bin/python
DATA=/root/autodl-tmp/asc27/ASC26-Embodied-World-Model-Optimization-main
CONFIG=/root/autodl-tmp/asc27/config_eval.yaml
CKPT=/root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt
BASE_SCRIPT="$PROJECT/scripts/evaluation/world_model_interaction.py"
run_one() {
  SCENARIO="$1"; CASE_ID="$2"; N_ITER="$3"; FS="$4"; LABEL="$5"
  SAVE="$ROOT/$LABEL/$SCENARIO/case$CASE_ID"
  PROMPT="$DATA/$SCENARIO/case$CASE_ID/world_model_interaction_prompts"
  mkdir -p "$SAVE"
  if [[ -f "$SAVE/psnr.json" ]]; then echo "SKIP $LABEL $SCENARIO case$CASE_ID"; return; fi
  cd "$PROJECT"
  {
    echo "BASELINE label=$LABEL scenario=$SCENARIO case=$CASE_ID n_iter=$N_ITER ddim_steps=50 exe_steps=16 frame_stride=$FS amp=0 zero_state=0"
    date -Is
    time env CUDA_VISIBLE_DEVICES=0 "$PYTHON" "$BASE_SCRIPT" \
      --seed 123 --ckpt_path "$CKPT" --config "$CONFIG" --savedir "$SAVE" \
      --bs 1 --height 320 --width 512 --unconditional_guidance_scale 1.0 \
      --ddim_steps 50 --ddim_eta 1.0 --prompt_dir "$PROMPT" --dataset "$SCENARIO" \
      --video_length 16 --frame_stride "$FS" --n_action_steps 16 --exe_steps 16 \
      --n_iter "$N_ITER" --timestep_spacing uniform_trailing --guidance_rescale 0.7 --perframe_ae
    date -Is
  } 2>&1 | tee "$SAVE/run.log"
  VIDEO=$(find "$SAVE/inference" -type f -name '*_full_fs*.mp4' | head -1)
  GT="$DATA/$SCENARIO/case$CASE_ID/${SCENARIO}_case${CASE_ID}.mp4"
  if [[ -n "$VIDEO" && -f "$GT" ]]; then
    "$PYTHON" "$DATA/psnr_score_for_challenge.py" --gt_video "$GT" --pred_video "$VIDEO" --output_file "$SAVE/psnr.json" | tee -a "$SAVE/run.log"
    "$PYTHON" - "$SAVE/psnr.json" "$VIDEO" "$N_ITER" "$FS" "$LABEL" "$SCENARIO" "$CASE_ID" <<'PY'
import json,sys,subprocess
j=json.load(open(sys.argv[1])); v=sys.argv[2]
q=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=nb_frames,r_frame_rate,duration,width,height","-of","json",v]))
st=q["streams"][0]
j.update({"label":sys.argv[5],"scenario":sys.argv[6],"case":int(sys.argv[7]),"n_iter":int(sys.argv[3]),"frame_stride":int(sys.argv[4]),"nb_frames":int(st.get("nb_frames",0)),"fps":st.get("r_frame_rate"),"duration":float(st.get("duration",0)),"video":v})
json.dump(j,open(sys.argv[1],"w"),indent=2)
PY
  else
    echo "MISSING_VIDEO_OR_GT" | tee -a "$SAVE/run.log"
  fi
}
for mode in full short; do
  if [[ "$mode" == full ]]; then LABEL=baseline_official_full_system; else LABEL=baseline_official_short_system; fi
  for c in 1 2 3 4; do if [[ "$mode" == full ]]; then NI=7; else NI=1; fi; run_one unitree_z1_dual_arm_stackbox "$c" "$NI" 4 "$LABEL"; done
  for c in 1 2 3 4; do if [[ "$mode" == full ]]; then NI=8; else NI=1; fi; run_one unitree_z1_dual_arm_cleanup_pencils "$c" "$NI" 4 "$LABEL"; done
done
echo BASELINE_BATCH_DONE
