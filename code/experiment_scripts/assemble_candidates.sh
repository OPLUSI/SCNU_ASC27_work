#!/usr/bin/env bash
set -euo pipefail
ROOT=/root/autodl-tmp/asc27
OUT=$ROOT/final_candidates
rm -rf "$OUT"
mkdir -p "$OUT/unitree_z1_dual_arm_stackbox" "$OUT/unitree_z1_dual_arm_cleanup_pencils"

# Longest currently passing candidate for each stackbox case.
cp "$ROOT/results/stackbox_zerostate/unitree_z1_dual_arm_stackbox/case1/inference/sample_5/wm/4/itr-0.mp4" "$OUT/unitree_z1_dual_arm_stackbox/case1.mp4"
cp "$ROOT/results/stackbox_c2_full/unitree_z1_dual_arm_stackbox/case2/inference/15_full_fs4.mp4" "$OUT/unitree_z1_dual_arm_stackbox/case2.mp4"
printf "file '%s'\nfile '%s'\nfile '%s'\n" \
  "$ROOT/results/stackbox_c3_full/unitree_z1_dual_arm_stackbox/case3/inference/sample_25/wm/4/itr-0.mp4" \
  "$ROOT/results/stackbox_c3_full/unitree_z1_dual_arm_stackbox/case3/inference/sample_25/wm/4/itr-1.mp4" \
  "$ROOT/results/stackbox_c3_full/unitree_z1_dual_arm_stackbox/case3/inference/sample_25/wm/4/itr-2.mp4" \
  > /tmp/c3_list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i /tmp/c3_list.txt -c copy "$OUT/unitree_z1_dual_arm_stackbox/case3.mp4"
cp "$ROOT/results/stackbox_c4/unitree_z1_dual_arm_stackbox/case4/inference/sample_35/wm/4/itr-0.mp4" "$OUT/unitree_z1_dual_arm_stackbox/case4.mp4"

# Cleanup-pencils: first interaction is the longest verified passing output.
cp "$ROOT/results/cleanup_zero/unitree_z1_dual_arm_cleanup_pencils/case1/inference/sample_0/wm/4/itr-0.mp4" "$OUT/unitree_z1_dual_arm_cleanup_pencils/case1.mp4"
cp "$ROOT/results/cleanup_c2/unitree_z1_dual_arm_cleanup_pencils/case2/inference/sample_50/wm/4/itr-0.mp4" "$OUT/unitree_z1_dual_arm_cleanup_pencils/case2.mp4"
cp "$ROOT/results/cleanup_c3/unitree_z1_dual_arm_cleanup_pencils/case3/inference/sample_100/wm/4/itr-0.mp4" "$OUT/unitree_z1_dual_arm_cleanup_pencils/case3.mp4"
cp "$ROOT/results/cleanup_c4/unitree_z1_dual_arm_cleanup_pencils/case4/inference/sample_200/wm/4/itr-0.mp4" "$OUT/unitree_z1_dual_arm_cleanup_pencils/case4.mp4"
echo "$OUT"
