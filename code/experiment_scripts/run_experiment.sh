#!/usr/bin/env bash
set -euo pipefail

LABEL="$1"
SCENARIO="$2"
CASE_ID="$3"
DDIM_STEPS="$4"
N_ITER="$5"
EXE_STEPS="$6"
FRAME_STRIDE="$7"
AMP_MODE="${8:-0}"
ETA="${9:-1.0}"
SCRIPT_PATH="${10:-scripts/evaluation/world_model_interaction.py}"
ZERO_STATE_MODE="${11:-0}"
GUIDANCE_RESCALE="${12:-0.7}"
TIMESTEP_SPACING="${13:-uniform_trailing}"
SEED="${14:-123}"
GUIDANCE_SCALE="${15:-1.0}"
FAST_IO_MODE="${16:-0}"
COMPILE_MODE="${17:-0}"

DATA_ROOT=/root/autodl-tmp/asc27
RESULT_ROOT="${RESULT_ROOT:-/root/asc27_system_results/optimization_runs}"
PROJECT=/root/autodl-tmp/unifolm-world-model-action
PYTHON=/root/autodl-tmp/miniconda3/envs/asc_wma/bin/python
PROMPT_DIR="$DATA_ROOT/ASC26-Embodied-World-Model-Optimization-main/$SCENARIO/case$CASE_ID/world_model_interaction_prompts"
SAVE_DIR="$RESULT_ROOT/$LABEL/$SCENARIO/case$CASE_ID"
LOG_FILE="$SAVE_DIR/output.log"
mkdir -p "$SAVE_DIR"
cd "$PROJECT"
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
EXTRA_ARGS=()
if [[ "$AMP_MODE" == "1" ]]; then
  EXTRA_ARGS+=(--amp)
fi
if [[ "$ZERO_STATE_MODE" == "1" ]]; then
  EXTRA_ARGS+=(--zero_pred_state)
fi
if [[ "$FAST_IO_MODE" == "1" ]]; then
  EXTRA_ARGS+=(--fast_io)
fi
if [[ "$COMPILE_MODE" == "1" ]]; then
  EXTRA_ARGS+=(--torch_compile)
fi
{
  echo "EXPERIMENT label=$LABEL scenario=$SCENARIO case=$CASE_ID ddim_steps=$DDIM_STEPS n_iter=$N_ITER exe_steps=$EXE_STEPS frame_stride=$FRAME_STRIDE amp=$AMP_MODE eta=$ETA zero_state=$ZERO_STATE_MODE guidance_rescale=$GUIDANCE_RESCALE script=$SCRIPT_PATH"
  date -Is
  time CUDA_VISIBLE_DEVICES=0 "$PYTHON" "$SCRIPT_PATH" \
    --seed "$SEED" \
    --ckpt_path /root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt \
    --config "$DATA_ROOT/config_eval.yaml" \
    --savedir "$SAVE_DIR" \
    --bs 1 --height 320 --width 512 \
    --unconditional_guidance_scale "$GUIDANCE_SCALE" \
    --ddim_steps "$DDIM_STEPS" \
    --ddim_eta "$ETA" \
    --prompt_dir "$PROMPT_DIR" \
    --dataset "$SCENARIO" \
    --video_length 16 \
    --frame_stride "$FRAME_STRIDE" \
    --n_action_steps 16 \
    --exe_steps "$EXE_STEPS" \
    --n_iter "$N_ITER" \
    --timestep_spacing "$TIMESTEP_SPACING" \
    --guidance_rescale "$GUIDANCE_RESCALE" \
    --perframe_ae \
    "${EXTRA_ARGS[@]}"
  date -Is
} 2>&1 | tee "$LOG_FILE"
