#!/usr/bin/env bash
set -euo pipefail

# Repository entry point. Historical commands are retained in experiment_scripts/.
CODE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PACKAGE_DIR=$(cd -- "$CODE_DIR/.." && pwd)
MODE=${1:-optimized}
SCENARIO=${2:-unitree_z1_dual_arm_stackbox}
CASE_ID=${3:-1}
GROUP=${4:-full}
DRY_RUN=${5:-}
case "$MODE" in baseline|optimized) ;; *) echo 'mode: baseline or optimized' >&2; exit 2;; esac
case "$SCENARIO" in
  unitree_z1_dual_arm_stackbox) N_ITER=7;;
  unitree_z1_dual_arm_cleanup_pencils) N_ITER=8;;
  *) echo 'Only the two reported scenarios are supported by this launcher.' >&2; exit 2;;
esac
case "$CASE_ID" in 1|2|3|4) ;; *) echo 'case: 1, 2, 3, or 4' >&2; exit 2;; esac
case "$GROUP" in full) ;; short_2s) N_ITER=1;; *) echo 'group: full or short_2s' >&2; exit 2;; esac
if [[ -n "$DRY_RUN" && "$DRY_RUN" != '--dry-run' ]]; then
  echo 'Optional fifth argument: --dry-run' >&2; exit 2
fi

PYTHON=${PYTHON:-/root/autodl-tmp/miniconda3/envs/asc_wma/bin/python}
PROJECT="$CODE_DIR/unifolm-world-model-action"
DATA_DIR="$CODE_DIR/competition_data"
EVAL_DATA_DIR="$CODE_DIR/eval_data"
CKPT_PATH=${CKPT_PATH:-/root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt}
export OPENCLIP_PRETRAINED_PATH=${OPENCLIP_PRETRAINED_PATH:-/root/autodl-tmp/openclip_cache/open_clip_pytorch_model.bin}
# A separate directory protects the submitted measurements during reproduction.
RUN_ROOT=${RUN_ROOT:-/root/asc27_reproduction_runs}
SAVE_DIR="$RUN_ROOT/${MODE}_${GROUP}/$SCENARIO/case$CASE_ID"
PROMPT_DIR="$DATA_DIR/$SCENARIO/case$CASE_ID/world_model_interaction_prompts"
GT_VIDEO="$DATA_DIR/$SCENARIO/case$CASE_ID/${SCENARIO}_case${CASE_ID}.mp4"
CONFIG_PATH="$SAVE_DIR/config_runtime.yaml"
SCRIPT=scripts/evaluation/world_model_interaction.py
EXTRA_ARGS=()
if [[ "$MODE" == optimized ]]; then
  SCRIPT=scripts/evaluation/world_model_interaction_optimized.py
  EXTRA_ARGS+=(--amp --fast_io)
  export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
fi
export PYTHONPATH="$PROJECT/src${PYTHONPATH:+:$PYTHONPATH}"
COMMAND=("$PYTHON" "$SCRIPT" --seed 123 --ckpt_path "$CKPT_PATH"
  --config "$CONFIG_PATH" --savedir "$SAVE_DIR" --bs 1 --height 320 --width 512
  --unconditional_guidance_scale 1.0 --ddim_steps 50 --ddim_eta 1.0
  --prompt_dir "$PROMPT_DIR" --dataset "$SCENARIO" --video_length 16
  --frame_stride 4 --n_action_steps 16 --exe_steps 16 --n_iter "$N_ITER"
  --timestep_spacing uniform_trailing --guidance_rescale 0.7 --perframe_ae
  "${EXTRA_ARGS[@]}")

if [[ "$DRY_RUN" == '--dry-run' ]]; then
  printf 'cwd: %s\noutput: %s\ncommand: ' "$PROJECT" "$SAVE_DIR"
  printf '%q ' "${COMMAND[@]}"
  printf '\n'
  exit 0
fi

[[ -x "$PYTHON" ]] || { echo "Python missing: $PYTHON" >&2; exit 1; }
for file in "$CKPT_PATH" "$OPENCLIP_PRETRAINED_PATH" "$GT_VIDEO"; do
  [[ -f "$file" ]] || { echo "Required file missing: $file" >&2; exit 1; }
done
# Refuse to overwrite an earlier reproduction.
[[ ! -e "$SAVE_DIR" ]] || { echo "Output already exists: $SAVE_DIR (change RUN_ROOT)" >&2; exit 1; }
mkdir -p "$SAVE_DIR"
"$PYTHON" - "$CODE_DIR/config_eval.yaml" "$CONFIG_PATH" "$EVAL_DATA_DIR" <<'PY'
import sys
from omegaconf import OmegaConf
config = OmegaConf.load(sys.argv[1])
config.data.params.test.params.data_dir = sys.argv[3]
OmegaConf.save(config, sys.argv[2])
PY
cd "$PROJECT"
{
  printf 'REPRODUCTION mode=%s scenario=%s case=%s group=%s n_iter=%s\n' "$MODE" "$SCENARIO" "$CASE_ID" "$GROUP" "$N_ITER"
  date -Is
  time env CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" "${COMMAND[@]}"
  date -Is
} 2>&1 | tee "$SAVE_DIR/output.log"

mapfile -t VIDEOS < <(find "$SAVE_DIR/inference" -maxdepth 1 -type f -name '*_full_fs4.mp4')
[[ ${#VIDEOS[@]} -eq 1 ]] || { echo 'Expected exactly one final video.' >&2; exit 1; }
"$PYTHON" "$DATA_DIR/psnr_score_for_challenge.py" \
  --gt_video "$GT_VIDEO" --pred_video "${VIDEOS[0]}" --output_file "$SAVE_DIR/psnr.json" \
  2>&1 | tee -a "$SAVE_DIR/output.log"
[[ -s "$SAVE_DIR/psnr.json" ]] || { echo 'PSNR evaluation did not produce JSON.' >&2; exit 1; }
