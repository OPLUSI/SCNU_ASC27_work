#!/usr/bin/env python3
"""Check packaged measurements without importing torch or running inference."""
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def video_info(path):
    raw = subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_frames,width,height,r_frame_rate',
        '-show_entries', 'format=duration', '-of', 'json', str(path),
    ], text=True)
    info = json.loads(raw)
    stream = info['streams'][0]
    stream['duration'] = float(info['format']['duration'])
    return stream


def validate(root):
    errors, checks = [], []
    source_map = json.loads((root / 'experiments/source_map.json').read_text())
    report = json.loads((root / 'experiments/final_report.json').read_text())
    for group, summary_path in [('full', 'results/summary.json'), ('short_2s', 'experiments/short_2s/summary.json')]:
        summary = json.loads((root / summary_path).read_text())
        expected = {(row['scenario'], row['case']): row for row in report['groups'][group]}
        if len(summary) != 8 or len({(r['scenario'], r['case_id']) for r in summary}) != 8:
            errors.append(f'{group}: expected 8 unique summary rows')
        for row in summary:
            if set(row) != {'scenario', 'case_id', 'time_before_optim', 'time_after_optim', 'psnr'}:
                errors.append(f'{group}: unexpected summary fields')
            key = (row['scenario'], row['case_id'])
            item = expected.get(key)
            if item is None:
                errors.append(f'{group}: unexpected case {key}')
                continue
            for field, recorded in [
                ('time_before_optim', 'baseline_runtime_s'),
                ('time_after_optim', 'optimized_runtime_s'),
                ('psnr', 'optimized_psnr_db'),
            ]:
                if not math.isclose(row[field], item[recorded], abs_tol=1e-7):
                    errors.append(f'{group}/{key}: {field} differs from recorded report')

    for entry in source_map:
        case_dir = root / entry['destination']
        try:
            videos = list(case_dir.glob('*.mp4'))
            if len(videos) != 1:
                raise ValueError('expected exactly one MP4 next to output.log')
            video = videos[0]
            log = (case_dir / 'output.log').read_text(errors='replace')
            times = re.findall(r'^real\s+(\d+)m([\d.]+)s\s*$', log, flags=re.M)
            if len(times) != 1:
                raise ValueError(f'expected one real time, found {len(times)}')
            elapsed = int(times[0][0]) * 60 + float(times[0][1])
            if not math.isclose(elapsed, entry['runtime_s'], abs_tol=1e-7):
                raise ValueError(f'real time mismatch: {elapsed} vs {entry["runtime_s"]}')
            psnr = json.loads((case_dir / 'psnr.json').read_text())['psnr']
            if not math.isclose(psnr, entry['psnr'], abs_tol=1e-8):
                raise ValueError('PSNR mismatch')
            if sha256(video) != entry['video_sha256']:
                raise ValueError('video hash differs from source')
            info = video_info(video)
            expected_frames = 16 * (1 if entry['group'] == 'short_2s' else 7 if entry['scenario'].endswith('_stackbox') else 8)
            if int(info['nb_frames']) != expected_frames:
                raise ValueError(f'frame count {info["nb_frames"]}, expected {expected_frames}')
            if (info['width'], info['height'], info['r_frame_rate']) != (512, 320, '8/1'):
                raise ValueError('unexpected resolution or fps')
            if not math.isclose(info['duration'], expected_frames / 8, abs_tol=0.01):
                raise ValueError('duration mismatch')
            checks.append({
                'path': entry['destination'], 'group': entry['group'], 'mode': entry['mode'],
                'real_seconds': elapsed, 'psnr': psnr, 'psnr_ge_25': psnr >= 25,
                'video': video.name, 'video_sha256': entry['video_sha256'], **info,
            })
        except Exception as exc:
            errors.append(f'{entry["destination"]}: {exc}')

    if len(source_map) != 32:
        errors.append(f'expected 32 source-map entries, found {len(source_map)}')
    for required in [
        'README.md', 'code/run_case.sh', 'code/main.ipynb', 'code/config_eval.yaml',
        'code/environment/pip_freeze.txt', 'code/unifolm-world-model-action/LICENSE',
        'code/unifolm-world-model-action/src/unifolm_wma/models/samplers/ddim.py',
        'code/unifolm-world-model-action/scripts/evaluation/world_model_interaction_optimized.py',
        'code/patches/packaging_paths.patch',
        'proposal_file/ASC27_world_model_optimization_report.docx',
        'proposal_file/screenshots/README.md',
    ]:
        if not (root / required).is_file():
            errors.append(f'missing required file: {required}')
    links = [str(p.relative_to(root)) for p in root.rglob('*') if p.is_symlink()]
    if links:
        errors.append(f'package contains symlinks: {links}')
    for shell in (root / 'code').glob('*.sh'):
        result = subprocess.run(['bash', '-n', str(shell)], capture_output=True, text=True)
        if result.returncode:
            errors.append(result.stderr)
    for scenario in ('unitree_z1_dual_arm_stackbox', 'unitree_z1_dual_arm_cleanup_pencils'):
        for case in range(1, 5):
            for group in ('full', 'short_2s'):
                frames = root / 'proposal_file/video_frames' / group / scenario / f'case{case}'
                for name in ('frame_first.png', 'frame_middle.png', 'frame_last.png', 'contact_sheet.png', 'frames.json'):
                    if not (frames / name).is_file():
                        errors.append(f'missing frame artifact: {frames.relative_to(root)}/{name}')

    full = report['groups']['full']
    short = report['groups']['short_2s']
    return {
        'structural_validation_passed': not errors,
        'checked_case_directories': len(checks),
        'groups': {
            'full': {'cases': 8, 'optimized_psnr_ge_25': sum(r['optimized_psnr_db'] >= 25 for r in full)},
            'short_2s': {'cases': 8, 'optimized_psnr_ge_25': sum(r['optimized_psnr_db'] >= 25 for r in short)},
        },
        'inference_rerun_during_packaging': False,
        'pending_user_items': ['replace report screenshot placeholders', 'publish Git repository and add URL', 'add Colab sharing URL if required'],
        'errors': errors,
        'checks': checks,
    }


if __name__ == '__main__':
    package_root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
    result = validate(package_root)
    output = package_root / 'validation.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, ensure_ascii=False, indent=2))
    sys.exit(0 if result['structural_validation_passed'] else 1)
