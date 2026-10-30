#!/usr/bin/env bash
set -u
ROOT=/root/asc27_system_results
PROJECT=/root/autodl-tmp/unifolm-world-model-action
PYTHON=/root/autodl-tmp/miniconda3/envs/asc_wma/bin/python
DATA=/root/autodl-tmp/asc27/ASC26-Embodied-World-Model-Optimization-main
CONFIG=/root/autodl-tmp/asc27/config_eval.yaml
CKPT=/root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt
SCENARIO="$1"
CASE_ID="$2"
N_ITER="$3"
LABEL="$4"
SAVE="$ROOT/$LABEL/$SCENARIO/case$CASE_ID"
mkdir -p "$SAVE"
PROMPT="$DATA/$SCENARIO/case$CASE_ID/world_model_interaction_prompts"
LOG="$SAVE/run.log"
cd "$PROJECT"
{
  echo "BASELINE label=$LABEL scenario=$SCENARIO case=$CASE_ID n_iter=$N_ITER ddim_steps=50 exe_steps=16 frame_stride=$5 amp=0 zero_state=0"
  date -Is
  time env CUDA_VISIBLE_DEVICES=0 "$PYTHON" "$PROJECT/scripts/evaluation/world_model_interaction.py" \
    --seed 123 \
    --ckpt_path "$CKPT" \
    --config "$CONFIG" \
    --savedir "$SAVE" \
    --bs 1 --height 320 --width 512 \
    --unconditional_guidance_scale 1.0 \
    --ddim_steps 50 --ddim_eta 1.0 \
    --prompt_dir "$PROMPT" \
    --dataset "$SCENARIO" \
    --video_length 16 --frame_stride "$5" \
    --n_action_steps 16 --exe_steps 16 --n_iter "$N_ITER" \
    --timestep_spacing uniform_trailing \
    --guidance_rescale 0.7 --perframe_ae
  date -Is
} 2>&1 | tee "$LOG"
VIDEO=$(find "$SAVE/inference" -type f -name '*_full_fs*.mp4' | head -1)
GT="$PROMPT/\${SCENARIO}_case\${CASE_ID}.mp4"
if [[ -n "$VIDEO" && -f "$GT" ]]; then
  "$PYTHON" "$DATA/psnr_score_for_challenge.py" --gt_video "$GT" --pred_video "$VIDEO" --output_file "$SAVE/psnr.json" | tee -a "$LOG"
fi
