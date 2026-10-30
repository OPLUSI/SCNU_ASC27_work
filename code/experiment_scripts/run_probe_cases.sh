#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp/asc27
while read -r label scene case_id; do
  echo "RUN $label $scene case$case_id"
  bash /root/autodl-tmp/asc27/run_experiment.sh "$label" "$scene" "$case_id" 50 1 16 4 0 1.0 scripts/evaluation/world_model_interaction.py 1 0.7 uniform_trailing 123 1.0
done <<'EOF'
stackbox_c2 unitree_z1_dual_arm_stackbox 2
stackbox_c3 unitree_z1_dual_arm_stackbox 3
stackbox_c4 unitree_z1_dual_arm_stackbox 4
cleanup_c2 unitree_z1_dual_arm_cleanup_pencils 2
cleanup_c3 unitree_z1_dual_arm_cleanup_pencils 3
cleanup_c4 unitree_z1_dual_arm_cleanup_pencils 4
EOF
