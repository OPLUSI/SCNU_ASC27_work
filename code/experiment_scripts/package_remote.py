#!/usr/bin/env python3
"""Assemble an independent system-disk submission from recorded experiments."""
import ast
import difflib
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STAGE = Path(__file__).resolve().parent
TARGET = Path('/root/ASC27_worldmodel')
RESULTS = Path('/root/asc27_system_results')
WORK = Path('/root/autodl-tmp/asc27')
PROJECT = Path('/root/autodl-tmp/unifolm-world-model-action')
DATA = WORK / 'ASC26-Embodied-World-Model-Optimization-main'
IGNORE = shutil.ignore_patterns('.git', '__pycache__', '*.pyc', '*.pyo', '*.egg-info', 'build', '.ipynb_checkpoints')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def write_json(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def checked_output(command):
    run = subprocess.run(command, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f'{command[0]} failed: {run.stderr[-1000:]}')
    return run.stdout


def frames(video, destination, row, group):
    destination.mkdir(parents=True, exist_ok=True)
    info = json.loads(checked_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_frames,r_frame_rate', '-of', 'json', str(video),
    ]))['streams'][0]
    count = int(info['nb_frames'])
    a, b = map(int, info['r_frame_rate'].split('/'))
    fps = a / b
    indices = [('first', 0), ('middle', count // 2), ('last', count - 1)]
    details = []
    for name, index in indices:
        image_path = destination / f'frame_{name}.png'
        checked_output([
            'ffmpeg', '-v', 'error', '-nostdin', '-threads', '1', '-i', str(video),
            '-vf', f'select=eq(n\\,{index})', '-frames:v', '1', '-threads', '1', str(image_path),
        ])
        details.append({'file': image_path.name, 'zero_based_frame': index, 'time_seconds': index / fps})
    sheet = Image.new('RGB', (1536, 392), 'white')
    draw = ImageDraw.Draw(sheet)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 16) if Path(font_path).exists() else ImageFont.load_default()
    title = f'{group} | {row["scenario"]} | case{row["case"]} | PSNR {row["optimized_psnr_db"]:.4f} dB'
    draw.text((10, 8), title, fill='black', font=font)
    for i, detail in enumerate(details):
        with Image.open(destination / detail['file']) as im:
            sheet.paste(im.convert('RGB').resize((512, 320)), (512 * i, 36))
        draw.text((512 * i + 8, 363), f'frame {detail["zero_based_frame"]} | t={detail["time_seconds"]:.3f}s', fill='black', font=font)
    sheet.save(destination / 'contact_sheet.png')
    write_json(destination / 'frames.json', {
        'source_video': str(video.relative_to(TARGET)), 'video_sha256': digest(video),
        'fps': fps, 'frame_count': count, 'indexing': 'zero-based', 'frames': details,
    })


def notebook():
    def md(text):
        return {'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(keepends=True)}
    def code(text):
        return {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': text.splitlines(keepends=True)}
    return {
        'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python'}, 'colab': {'name': 'ASC27 world model reproduction'}},
        'cells': [
            md('# ASC27 world model reproduction\n\n复现入口，未在本次打包时运行。正式测量来自AutoDL RTX 3090。使用GPU运行前先按README准备依赖和权重；Colab免费T4的显存和内存不保证能运行该模型。'),
            md('## 1 挂载提交目录\n\n在AutoDL/Jupyter上直接使用默认目录。在Colab中先将提交目录放入Drive，然后运行挂载并调整PACKAGE。'),
            code('from pathlib import Path\nimport os, subprocess\nPACKAGE = Path("/root/ASC27_worldmodel")\n# Colab example:\n# from google.colab import drive\n# drive.mount("/content/drive")\n# PACKAGE = Path("/content/drive/MyDrive/ASC27_worldmodel")\nassert (PACKAGE / "code/run_case.sh").is_file(), PACKAGE\n'),
            md('## 2 环境与路径\n\n首次迁移需安装GPU版本PyTorch及README所列依赖，并安装项目。权重路径必须指向实际下载的文件。'),
            code('import sys\nPYTHON = "/root/autodl-tmp/miniconda3/envs/asc_wma/bin/python"\nif not Path(PYTHON).exists():\n    PYTHON = sys.executable\nos.environ["PYTHON"] = PYTHON\nos.environ["CKPT_PATH"] = "/root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt"\nos.environ["OPENCLIP_PRETRAINED_PATH"] = "/root/autodl-tmp/openclip_cache/open_clip_pytorch_model.bin"\nos.environ["RUN_ROOT"] = str(PACKAGE.parent / "asc27_notebook_reproduction_runs")\nsubprocess.run([PYTHON, "-m", "pip", "install", "--no-deps", "-e", str(PACKAGE / "code/unifolm-world-model-action")], check=True)\n'),
            md('## 3 先查看命令\n\n本单元不运行GPU推理。完整组stackbox使用7轮，cleanup使用8轮；短测改为short_2s。'),
            code('MODE = "optimized"\nSCENARIO = "unitree_z1_dual_arm_stackbox"\nCASE_ID = "1"\nGROUP = "full"\ncommand = ["bash", str(PACKAGE / "code/run_case.sh"), MODE, SCENARIO, CASE_ID, GROUP]\nsubprocess.run(command + ["--dry-run"], check=True)\n'),
            md('## 4 运行单case\n\n需要GPU。RUN_INFERENCE默认关闭，以免无卡模式误启动；确认资源后设为True。'),
            code('RUN_INFERENCE = False\nif RUN_INFERENCE:\n    subprocess.run(command, check=True)\nelse:\n    print("Inference disabled; set RUN_INFERENCE=True when the GPU environment is ready.")\n'),
            md('## 5 查看已有提交汇总'),
            code('import json\nsummary = json.loads((PACKAGE / "results/summary.json").read_text())\nfor row in summary:\n    print(row["scenario"], row["case_id"], "speedup", round(row["time_before_optim"] / row["time_after_optim"], 3), "PSNR", row["psnr"])\n'),
        ],
    }


def finalize():
    if not TARGET.is_dir() or TARGET.is_symlink():
        raise RuntimeError('Submission directory is missing or is a symlink')
    code_dir = TARGET / 'code'
    syntax_findings = []
    for path in (code_dir / 'unifolm-world-model-action').rglob('*.py'):
        try:
            ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            syntax_findings.append({'file': str(path.relative_to(TARGET)), 'line': exc.lineno, 'message': exc.msg})
    write_json(code_dir / 'environment/source_syntax_audit.json', {
        'scope': 'copied source; unused upstream files are preserved without speculative fixes',
        'findings': syntax_findings,
    })
    for relative in [
        'scripts/evaluation/world_model_interaction.py',
        'scripts/evaluation/world_model_interaction_optimized.py',
        'scripts/evaluation/eval_utils.py',
        'src/unifolm_wma/modules/encoders/condition.py',
        'src/unifolm_wma/models/samplers/ddim.py',
    ]:
        path = code_dir / 'unifolm-world-model-action' / relative
        ast.parse(path.read_text(), filename=str(path))
    checked_output(['bash', '-n', str(code_dir / 'run_case.sh')])
    print(checked_output([sys.executable, str(code_dir / 'validate_submission.py'), str(TARGET)]))
    write(TARGET / 'MANIFEST.sha256', ''.join(
        f'{digest(path)}  {path.relative_to(TARGET)}\n'
        for path in sorted(TARGET.rglob('*')) if path.is_file() and path.name != 'MANIFEST.sha256'
    ))
    print(f'Submission folder: {TARGET}')


def main():
    if sys.argv[1:] == ['--finalize-only']:
        finalize()
        return
    if TARGET.exists():
        raise RuntimeError(f'Refusing to overwrite an existing directory: {TARGET}')
    if TARGET.parent != Path('/root') or TARGET.is_symlink():
        raise RuntimeError('Unexpected submission target')
    TARGET.mkdir()
    code_dir = TARGET / 'code'
    proposal = TARGET / 'proposal_file'
    exp = TARGET / 'experiments'
    for folder in (code_dir, proposal, exp, TARGET / 'results'):
        folder.mkdir()
    copy(STAGE / 'README.md', TARGET / 'README.md')
    copy(STAGE / '.gitignore', TARGET / '.gitignore')
    copy(STAGE / 'run_case.sh', code_dir / 'run_case.sh')
    copy(STAGE / 'validate_submission.py', code_dir / 'validate_submission.py')
    copy(STAGE / 'package_remote.py', code_dir / 'experiment_scripts/package_remote.py')
    copy(STAGE / 'SCREENSHOTS_README.md', proposal / 'screenshots/README.md')
    for path in (code_dir / 'run_case.sh', code_dir / 'validate_submission.py'):
        path.chmod(0o755)
    shutil.copytree(PROJECT, code_dir / 'unifolm-world-model-action', ignore=IGNORE)
    shutil.copytree(DATA, code_dir / 'competition_data', ignore=IGNORE)
    shutil.copytree(WORK / 'eval_data', code_dir / 'eval_data', ignore=IGNORE)
    copy(WORK / 'config_eval.yaml', code_dir / 'config_eval.yaml')
    shutil.copytree(STAGE / 'figures', proposal / 'figures')
    copy(STAGE / 'ASC27_world_model_optimization_report.docx', proposal / 'ASC27_world_model_optimization_report.docx')
    for path in sorted(WORK.glob('*.sh')) + sorted(WORK.glob('*.py')):
        copy(path, code_dir / 'experiment_scripts' / path.name)
    for name in ('asc27_system_run_case.sh', 'asc27_run_baselines.sh', 'asc27_run_optimized.sh'):
        copy(Path('/root') / name, code_dir / 'experiment_scripts' / name)
    for name in ('queue_nozero_final.sh', 'make_final_report.py', 'build_world_model_report.py'):
        copy(STAGE / name, code_dir / 'experiment_scripts' / name)

    # Preserve the actual experimental file before a packaging-only path change.
    rel = Path('src/unifolm_wma/modules/encoders/condition.py')
    old = (PROJECT / rel).read_text()
    copy(PROJECT / rel, code_dir / 'experiment_scripts/condition.py.recorded')
    new = old.replace('import torch\n', 'import os\nimport torch\n', 1).replace(
        'pretrained="/root/autodl-tmp/openclip_cache/open_clip_pytorch_model.bin"',
        'pretrained=os.environ.get("OPENCLIP_PRETRAINED_PATH", "/root/autodl-tmp/openclip_cache/open_clip_pytorch_model.bin")',
    )
    if new.count('pretrained=os.environ.get("OPENCLIP_PRETRAINED_PATH"') != 2:
        raise RuntimeError('Unexpected OpenCLIP code; refusing a speculative patch')
    write(code_dir / 'unifolm-world-model-action' / rel, new)
    write(code_dir / 'patches/packaging_paths.patch', ''.join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), fromfile=f'a/{rel}', tofile=f'b/{rel}',
    )))
    upstream = WORK / 'unifolm-world-model-action'
    changed = []
    for folder in ('src', 'scripts', 'configs'):
        for path in sorted((PROJECT / folder).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
                continue
            relative = path.relative_to(PROJECT)
            base = upstream / relative
            if base.exists() and base.read_bytes() == path.read_bytes():
                continue
            if path.suffix not in ('.py', '.yaml', '.yml', '.sh'):
                continue
            base_text = base.read_text() if base.exists() else ''
            edited_text = path.read_text()
            patch = ''.join(difflib.unified_diff(base_text.splitlines(True), edited_text.splitlines(True), fromfile=f'a/{relative}', tofile=f'b/{relative}'))
            write(code_dir / 'patches' / (str(relative).replace('/', '__') + '.patch'), patch)
            changed.append(str(relative))
    write_json(code_dir / 'patches/changed_files.json', {
        'comparison': 'local extracted original source vs experimental working project',
        'upstream_commit_verified': False, 'experimental_changed_files': changed,
        'packaging_only_change': str(rel),
    })

    report = json.loads((RESULTS / 'final_report.json').read_text())
    copy(RESULTS / 'final_report.json', exp / 'final_report.json')
    copy(RESULTS / 'final_report.md', exp / 'final_report.md')
    source_map = []
    for group, rows in report['groups'].items():
        summary = []
        for row in rows:
            for mode, key, parent in [
                ('optimized', 'optimized_dir', TARGET / 'results' if group == 'full' else exp / 'short_2s'),
                ('baseline', 'baseline_dir', exp / 'baseline_full' if group == 'full' else exp / 'baseline_short_2s'),
            ]:
                source = Path(row[key])
                videos = list((source / 'inference').glob('*_full_fs4.mp4'))
                if len(videos) != 1:
                    raise RuntimeError(f'Expected exactly one final video: {source}')
                log = source / ('output.log' if mode == 'optimized' else 'run.log')
                if not log.is_file():
                    raise RuntimeError(f'Missing original log: {log}')
                dest = parent / row['scenario'] / f'case{row["case"]}'
                copy(videos[0], dest / videos[0].name)
                copy(log, dest / 'output.log')
                copy(source / 'psnr.json', dest / 'psnr.json')
                entry = {
                    'group': group, 'mode': mode, 'scenario': row['scenario'], 'case_id': row['case'],
                    'source_directory': str(source), 'original_log': str(log),
                    'source_video': str(videos[0]), 'video_sha256': digest(videos[0]),
                    'destination': str(dest.relative_to(TARGET)),
                    'runtime_s': row[f'{mode}_runtime_s'], 'psnr': row[f'{mode}_psnr_db'],
                }
                source_map.append(entry)
                if mode == 'optimized':
                    frames(dest / videos[0].name, proposal / 'video_frames' / group / row['scenario'] / f'case{row["case"]}', row, group)
            summary.append({
                'scenario': row['scenario'], 'case_id': row['case'],
                'time_before_optim': row['baseline_runtime_s'],
                'time_after_optim': row['optimized_runtime_s'],
                'psnr': row['optimized_psnr_db'],
            })
        summary_dir = TARGET / 'results' if group == 'full' else exp / 'short_2s'
        write_json(summary_dir / 'summary.json', summary)
    write_json(exp / 'source_map.json', source_map)

    for source in sorted((RESULTS / 'optimization_runs').iterdir()):
        if source.is_dir() and source.name not in ('opt_amp_fastio_gpuaccum_nozero', 'opt_amp_fastio_gpuaccum_nozero_short'):
            shutil.copytree(source, exp / 'probes' / source.name, ignore=shutil.ignore_patterns('tensorboard', '__pycache__'))
    for source in sorted(RESULTS.glob('*.log')) + sorted(RESULTS.glob('*probe*.json')):
        copy(source, exp / 'batch_logs' / source.name)
    write_json(code_dir / 'main.ipynb', notebook())

    env_dir = code_dir / 'environment'
    write(env_dir / 'pip_freeze.txt', checked_output([sys.executable, '-m', 'pip', 'freeze']))
    write(env_dir / 'python_version.txt', sys.version + '\n')
    write(env_dir / 'os_release.txt', Path('/etc/os-release').read_text())
    write(env_dir / 'cpu_at_packaging.txt', checked_output(['lscpu']))
    versions = {}
    for name in ['torch', 'torchvision', 'xformers', 'open-clip-torch', 'numpy', 'pytorch-lightning', 'diffusers', 'transformers', 'Pillow', 'imageio', 'moviepy', 'h5py']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    write_json(env_dir / 'versions.json', {
        'collected_at_utc': datetime.now(timezone.utc).isoformat(),
        'collection_mode': 'CPU-only packaging session; not a new GPU hardware measurement',
        'python': sys.version, 'packages': versions,
        'experiment_gpu': 'NVIDIA RTX 3090 24 GB (recorded experiment platform)',
        'checkpoint_path': '/root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt',
        'checkpoint_bytes': Path('/root/autodl-tmp/checkpoints/UnifoLM-WMA-0-Dual/unifolm_wma_dual.ckpt').stat().st_size,
        'openclip_path': '/root/autodl-tmp/openclip_cache/open_clip_pytorch_model.bin',
        'openclip_bytes': Path('/root/autodl-tmp/openclip_cache/open_clip_pytorch_model.bin').stat().st_size,
    })
    finalize()


if __name__ == '__main__':
    main()
