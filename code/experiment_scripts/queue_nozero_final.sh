#!/usr/bin/env bash
set -euo pipefail

cd /root/autodl-tmp/asc27
RESULT_ROOT=/root/asc27_system_results/optimization_runs

for mode in full short; do
  if [[ "$mode" == "full" ]]; then
    NI_STACK=7
    NI_CLEAN=8
    LABEL=opt_amp_fastio_gpuaccum_nozero
  else
    NI_STACK=1
    NI_CLEAN=1
    LABEL=opt_amp_fastio_gpuaccum_nozero_short
  fi
  for scen in unitree_z1_dual_arm_stackbox unitree_z1_dual_arm_cleanup_pencils; do
    if [[ "$scen" == "unitree_z1_dual_arm_stackbox" ]]; then
      NI=$NI_STACK
    else
      NI=$NI_CLEAN
    fi
    for c in 1 2 3 4; do
      save="$RESULT_ROOT/$LABEL/$scen/case$c"
      if [[ -f "$save/psnr.json" ]]; then
        echo "SKIP $LABEL $scen case$c"
        continue
      fi
      bash run_experiment.sh "$LABEL" "$scen" "$c" 50 "$NI" 16 4 1 1.0 \
        scripts/evaluation/world_model_interaction_optimized.py 0 0.7 uniform_trailing 123 1.0 1
      vid=$(find "$save/inference" -type f -name '*_full_fs4.mp4' | head -1)
      gt="/root/autodl-tmp/asc27/ASC26-Embodied-World-Model-Optimization-main/$scen/case$c/${scen}_case${c}.mp4"
      if [[ -n "$vid" && -f "$gt" ]]; then
        /root/autodl-tmp/miniconda3/envs/asc_wma/bin/python \
          ASC26-Embodied-World-Model-Optimization-main/psnr_score_for_challenge.py \
          --gt_video "$gt" --pred_video "$vid" --output_file "$save/psnr.json" | tee -a "$save/output.log"
      fi
    done
  done
done

touch /root/asc27_system_results/optimization_nozero_full_short_done
