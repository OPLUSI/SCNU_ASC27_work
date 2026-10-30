import json
import re
from pathlib import Path

ROOT = Path('/root/asc27_system_results')

SCENARIOS = [
    'unitree_z1_dual_arm_stackbox',
    'unitree_z1_dual_arm_cleanup_pencils',
]
CASES = [1, 2, 3, 4]


def read_psnr(path: Path):
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text())
        return float(obj['psnr'])
    except Exception:
        return None


def parse_runtime(path: Path):
    if not path.exists():
        return None
    text = path.read_text(errors='ignore')
    # GNU time output used by run_experiment.sh: real\tXmYs or real\tYs
    matches = re.findall(r'^real\s+([^\r\n]+)', text, flags=re.MULTILINE)
    if not matches:
        return None
    value = matches[-1].strip()
    m = re.fullmatch(r'(?:(\d+)h)?(?:(\d+)m)?([0-9.]+)s', value)
    if not m:
        return None
    h = int(m.group(1) or 0)
    minute = int(m.group(2) or 0)
    sec = float(m.group(3))
    return h * 3600 + minute * 60 + sec


def find_runtime(case_dir: Path):
    for name in ('run.log', 'output.log'):
        value = parse_runtime(case_dir / name)
        if value is not None:
            return value
    return None


def collect_group(group, baseline_label, optimized_label):
    rows = []
    for scenario in SCENARIOS:
        for case in CASES:
            base_dir = ROOT / baseline_label / scenario / f'case{case}'
            opt_dir = ROOT / optimized_label / scenario / f'case{case}'
            base_psnr = read_psnr(base_dir / 'psnr.json')
            opt_psnr = read_psnr(opt_dir / 'psnr.json')
            base_time = find_runtime(base_dir)
            opt_time = find_runtime(opt_dir)
            row = {
                'group': group,
                'scenario': scenario,
                'case': case,
                'baseline_psnr_db': base_psnr,
                'optimized_psnr_db': opt_psnr,
                'psnr_delta_db': None if base_psnr is None or opt_psnr is None else opt_psnr - base_psnr,
                'baseline_runtime_s': base_time,
                'optimized_runtime_s': opt_time,
                'speedup': None if base_time is None or opt_time is None or opt_time == 0 else base_time / opt_time,
                'baseline_dir': str(base_dir),
                'optimized_dir': str(opt_dir),
            }
            rows.append(row)
    return rows


def avg(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return sum(vals) / len(vals) if vals else None


def fmt(value, digits=2):
    return '—' if value is None else f'{value:.{digits}f}'


groups = {
    'full': collect_group(
        'full',
        'baseline_official_full_system',
        'optimization_runs/opt_amp_fastio_gpuaccum_nozero',
    ),
    'short_2s': collect_group(
        'short_2s',
        'baseline_official_short_system',
        'optimization_runs/opt_amp_fastio_gpuaccum_nozero_short',
    ),
}

# The optimized label is nested under optimization_runs; normalize paths above.
for rows in groups.values():
    for row in rows:
        row['optimized_dir'] = str(ROOT / row['optimized_dir'])

report = {
    'title': 'ASC27 赛题二：官方基线与优化实验汇总',
    'remote_host': 'AutoDL_3090',
    'baseline_settings': {
        'ddim_steps': 50,
        'frame_stride': 4,
        'video_length': 16,
        'exe_steps': 16,
        'n_iter': {'unitree_z1_dual_arm_stackbox': 7, 'unitree_z1_dual_arm_cleanup_pencils': 8},
        'seed': 123,
        'timestep_spacing': 'uniform_trailing',
        'guidance_rescale': 0.7,
        'ddim_eta': 1.0,
    },
    'optimization_strategy': [
        'CUDA FP16 autocast（模型权重保持原精度）',
        '保留预测状态回灌（不启用 zero_pred_state，避免个别场景质量崩落）',
        'torch.no_grad、DDIM sampler 复用、文本条件缓存',
        'fast_io：跳过动作分支视频解码、中间视频/TensorBoard 写盘',
        'world-model 视频留在 GPU，最后统一拼接并传回 CPU',
        'cuDNN benchmark 与线程数固定',
    ],
    'groups': groups,
    'probe_conclusions': {
        'torch_compile': '未纳入正式策略：动态形状/einops/xformers 导致反复重编译，首轮 CPU 占满且 GPU 利用率下降。',
        'cuda_graph': '静态 Conv3D capture/replay 探针通过，但完整链路包含随机噪声、动态条件和动态形状，未直接套用。',
        'ddim30': '仅作极限速度对照：约 3.6×，但 cleanup case1 PSNR 约下降 1.63 dB，未作为正式方案。',
        'zero_state_ablation': 'AMP+fast_io+GPU 累积但启用 zero_pred_state 时，stackbox case3 为 24.2687 dB；关闭后为 26.2456 dB，因此正式方案不启用该开关。',
        'fp32_probe': 'stackbox case3 的 FP32+fast_io+不置零为 26.7792 dB、11m49.5s（约 1.28×），质量更稳但速度不满足目标，作为精度对照。',
        'repeatability': '同一配置重复运行的 PSNR 会有波动（例如 cleanup case1 不置零 probe 为 21.2404 dB，而统一队列为 20.3101 dB），因此最终表格以统一队列单次结果为准。',
    },
}

(ROOT / 'final_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))

lines = []
lines.append('# ASC27 赛题二：官方基线与优化实验汇总')
lines.append('')
lines.append('正式优化方案不计入基线：FP16 autocast、fast_io、GPU 累积拼接、DDIM/文本缓存、no_grad 与 cuDNN benchmark；保留预测状态，不启用 zero_pred_state。')
lines.append('')
lines.append('## 官方参数')
lines.append('')
lines.append('DDIM steps=50，frame_stride=4，video_length=16，exe_steps=16，seed=123，timestep_spacing=uniform_trailing，guidance_rescale=0.7，eta=1.0；stackbox n_iter=7，cleanup_pencils n_iter=8。')
lines.append('')
for name, rows in groups.items():
    lines.append(f'## {"完整组" if name == "full" else "2 秒短测组"}')
    lines.append('')
    lines.append('| 场景 | case | 基线 PSNR | 优化 PSNR | ΔPSNR | 基线时间(s) | 优化时间(s) | 加速比 |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|')
    for r in rows:
        scene = r['scenario'].replace('unitree_z1_dual_arm_', '')
        lines.append(f"| {scene} | {r['case']} | {fmt(r['baseline_psnr_db'])} | {fmt(r['optimized_psnr_db'])} | {fmt(r['psnr_delta_db'])} | {fmt(r['baseline_runtime_s'])} | {fmt(r['optimized_runtime_s'])} | {fmt(r['speedup'], 2)}× |")
    lines.append('')
    lines.append(f"平均：PSNR {fmt(avg(rows, 'baseline_psnr_db'))} → {fmt(avg(rows, 'optimized_psnr_db'))} dB；平均加速比 {fmt(avg(rows, 'speedup'))}×。")
    lines.append('')
lines.append('## 额外探针')
lines.append('')
for key, value in report['probe_conclusions'].items():
    lines.append(f'- **{key}**：{value}')
lines.append('')
lines.append('注：短测组使用同一正式优化策略，仅将官方完整交互轮数改为 n_iter=1，用于展示约 2 秒输出下的速度/质量上限。')
(ROOT / 'final_report.md').write_text('\n'.join(lines) + '\n')
print('wrote', ROOT / 'final_report.json')
print('wrote', ROOT / 'final_report.md')
for name, rows in groups.items():
    print(name, len(rows), 'complete_psnr=', sum(r['optimized_psnr_db'] is not None for r in rows), 'complete_runtime=', sum(r['optimized_runtime_s'] is not None for r in rows))
