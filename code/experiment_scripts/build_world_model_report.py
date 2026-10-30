import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'final_report.json').read_text(encoding='utf-8'))
ASSET_DIR = ROOT / 'report_assets'
ASSET_DIR.mkdir(exist_ok=True)

FONT_REG = r'C:\Windows\Fonts\msyh.ttc'
FONT_BOLD = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_MONO = r'C:\Windows\Fonts\consola.ttf'


def font(path, size):
    if isinstance(path, ImageFont.FreeTypeFont):
        return path
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


F_REG_24 = font(FONT_REG, 24)
F_REG_28 = font(FONT_REG, 28)
F_REG_32 = font(FONT_REG, 32)
F_BOLD_24 = font(FONT_BOLD, 24)
F_BOLD_28 = font(FONT_BOLD, 28)
F_BOLD_32 = font(FONT_BOLD, 32)
F_MONO_24 = font(FONT_MONO, 24)


NAVY = '#183B56'
BLUE = '#2F80ED'
ORANGE = '#F2994A'
RED = '#D64545'
GREEN = '#2E9D65'
GRID = '#D9E2EC'
TEXT = '#1F2933'
MUTED = '#52606D'
PALE = '#F4F7FA'


def short_name(s):
    return s.replace('unitree_z1_dual_arm_', '')


def make_psnr_chart(group_name, rows, out_path, title):
    W, H = 1800, 940
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((70, 35), title, fill=NAVY, font=F_BOLD_32)
    left, top, right, bottom = 130, 130, 1740, 780
    ymax = 36
    for y in range(0, ymax + 1, 5):
        yy = bottom - (y / ymax) * (bottom - top)
        d.line((left, yy, right, yy), fill=GRID, width=2)
        d.text((62, yy - 15), str(y), fill=MUTED, font=F_REG_24)
    threshold_y = bottom - (25 / ymax) * (bottom - top)
    d.line((left, threshold_y, right, threshold_y), fill=RED, width=4)
    d.text((right - 250, threshold_y - 36), '25 dB threshold', fill=RED, font=F_BOLD_24)
    d.line((left, bottom, right, bottom), fill=TEXT, width=3)
    d.line((left, top, left, bottom), fill=TEXT, width=3)
    step = (right - left) / len(rows)
    bar_w = min(48, step * 0.24)
    for i, row in enumerate(rows):
        cx = left + step * (i + 0.5)
        vals = [row['baseline_psnr_db'], row['optimized_psnr_db']]
        colors = [BLUE, ORANGE]
        for j, (v, color) in enumerate(zip(vals, colors)):
            x0 = cx - bar_w - 5 + j * (bar_w + 10)
            x1 = x0 + bar_w
            y1 = bottom - (v / ymax) * (bottom - top)
            d.rounded_rectangle((x0, y1, x1, bottom), radius=6, fill=color)
            d.text((x0 - 9, max(top - 5, y1 - 32)), f'{v:.1f}', fill=TEXT, font=font(F_REG_24, 21))
        label = f"{short_name(row['scenario']).replace('_', ' ')}\nC{row['case']}"
        bb = d.multiline_textbbox((0, 0), label, font=font(F_REG_24, 21), spacing=2, align='center')
        d.multiline_text((cx - (bb[2] - bb[0]) / 2, bottom + 18), label, fill=TEXT, font=font(F_REG_24, 21), spacing=2, align='center')
    d.rectangle((left + 10, 75, left + 42, 105), fill=BLUE)
    d.text((left + 54, 73), 'Baseline', fill=TEXT, font=F_REG_24)
    d.rectangle((left + 190, 75, left + 222, 105), fill=ORANGE)
    d.text((left + 234, 73), 'Optimized', fill=TEXT, font=F_REG_24)
    d.text((70, 835), 'PSNR 单位：dB；柱顶数字为该 case 的测量值。', fill=MUTED, font=F_REG_24)
    im.save(out_path)


def make_runtime_chart(full_rows, short_rows, out_path):
    W, H = 1800, 1020
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((70, 35), '推理时间与加速比对比', fill=NAVY, font=F_BOLD_32)
    panels = [(full_rows, 120, 480, '完整组：官方轮次'), (short_rows, 560, 920, '短测组：n_iter=1')]
    for rows, top, bottom, label in panels:
        left, right = 150, 1740
        ymax = max(r['baseline_runtime_s'] for r in rows) * 1.15
        for y in range(0, int(ymax // 200 + 1) * 200 + 1, 200):
            yy = bottom - (y / ymax) * (bottom - top)
            d.line((left, yy, right, yy), fill=GRID, width=2)
            d.text((55, yy - 14), str(y), fill=MUTED, font=font(F_REG_24, 20))
        d.line((left, bottom, right, bottom), fill=TEXT, width=3)
        d.line((left, top, left, bottom), fill=TEXT, width=3)
        d.text((left, top - 55), label, fill=TEXT, font=F_BOLD_28)
        step = (right - left) / len(rows)
        bar_w = min(35, step * 0.22)
        for i, row in enumerate(rows):
            cx = left + step * (i + 0.5)
            for j, (v, color) in enumerate([(row['baseline_runtime_s'], BLUE), (row['optimized_runtime_s'], ORANGE)]):
                x0 = cx - bar_w - 4 + j * (bar_w + 8)
                x1 = x0 + bar_w
                y1 = bottom - (v / ymax) * (bottom - top)
                d.rounded_rectangle((x0, y1, x1, bottom), radius=5, fill=color)
            d.text((cx - 20, bottom + 12), f"{short_name(row['scenario'])[:7]}\nC{row['case']}", fill=TEXT, font=font(F_REG_24, 18), spacing=1, align='center')
            d.text((cx - 22, top + 4), f"{row['speedup']:.2f}x", fill=GREEN, font=font(F_BOLD_24, 18))
    d.rectangle((1450, 40, 1480, 70), fill=BLUE)
    d.text((1490, 38), 'Baseline', fill=TEXT, font=font(F_REG_24, 21))
    d.rectangle((1600, 40, 1630, 70), fill=ORANGE)
    d.text((1640, 38), 'Optimized', fill=TEXT, font=font(F_REG_24, 21))
    im.save(out_path)


def centered(draw, box, text, fnt, fill=TEXT, spacing=4):
    x0, y0, x1, y1 = box
    bb = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=spacing, align='center')
    x = (x0 + x1 - (bb[2] - bb[0])) / 2
    y = (y0 + y1 - (bb[3] - bb[1])) / 2
    draw.multiline_text((x, y), text, font=fnt, fill=fill, spacing=spacing, align='center')


def make_pipeline(out_path):
    W, H = 1800, 760
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((70, 35), '最终优化策略的推理流水线', fill=NAVY, font=F_BOLD_32)
    boxes = [
        (80, 220, 380, 480, '#E8F1FB', '输入\n初始图像 + 状态\n动作条件'),
        (465, 220, 765, 480, '#EAF6EF', '条件准备\n文本条件缓存\n状态/动作投影'),
        (850, 220, 1150, 480, '#FFF3E6', 'DDIM 采样\nFP16 autocast\n采样器复用'),
        (1235, 220, 1535, 480, '#F3ECFA', '世界模型交互\n视频保留 GPU\n状态继续回灌'),
        (1620, 220, 1740, 480, '#FDECEC', '一次性\n拼接/写盘'),
    ]
    for x0, y0, x1, y1, color, text in boxes:
        d.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=color, outline=NAVY, width=3)
        centered(d, (x0 + 15, y0 + 15, x1 - 15, y1 - 15), text, F_BOLD_24)
    for i in range(len(boxes) - 1):
        x1 = boxes[i][2]
        x2 = boxes[i + 1][0]
        y = 350
        d.line((x1 + 8, y, x2 - 18, y), fill=NAVY, width=6)
        d.polygon([(x2 - 18, y - 14), (x2 + 4, y), (x2 - 18, y + 14)], fill=NAVY)
    d.text((80, 590), '工程优化：关闭中间视频/TensorBoard 写盘；固定 OMP/MKL/OPENBLAS 线程；启用 cuDNN benchmark。', fill=MUTED, font=F_REG_24)
    im.save(out_path)


def make_log_excerpt(out_path):
    W, H = 1800, 760
    im = Image.new('RGB', (W, H), '#171A21')
    d = ImageDraw.Draw(im)
    lines = [
        'EXPERIMENT label=opt_amp_fastio_gpuaccum_nozero',
        'scenario=unitree_z1_dual_arm_stackbox case=1',
        'ddim_steps=50 n_iter=7 frame_stride=4 amp=1 zero_state=0',
        '>>> Generate 16 frames under each generation ...',
        '>>> Step 0: generating actions ...',
        '>>> Step 0: interacting with world model ...',
        '>>> Step 6: interacting with world model ...',
        'real    6m18.977s',
        'Video PSNR: 22.8451 dB',
        'Result saved to .../case1/psnr.json',
    ]
    d.text((55, 35), '实验日志摘录', fill='#7DD3FC', font=F_BOLD_32)
    y = 115
    for line in lines:
        color = '#D1FAE5' if ('PSNR' in line or 'real' in line) else '#E5E7EB'
        d.text((65, y), line, fill=color, font=F_MONO_24)
        y += 55
    d.text((65, H - 55), '由 output.log 中的真实运行输出整理；real 为脚本记录的 wall-clock inference time。', fill='#94A3B8', font=font(F_REG_24, 20))
    im.save(out_path)


def make_placeholder_panel(out_path, title, lines):
    """Create a visible replacement slot for screenshots added before submission."""
    W, H = 1800, 620
    im = Image.new('RGB', (W, H), '#F8FAFC')
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((24, 24, W - 24, H - 24), radius=20, fill='#FFFFFF', outline='#8AA4B8', width=5)
    d.rounded_rectangle((48, 48, W - 48, H - 48), radius=14, outline='#C7D5E0', width=3)
    d.text((90, 86), title, fill=NAVY, font=F_BOLD_32)
    y = 190
    for line in lines:
        d.text((110, y), line, fill=MUTED, font=F_REG_28)
        y += 68
    d.text((90, H - 100), '提交前删除本框，并在此处插入真实截图。', fill=RED, font=F_BOLD_24)
    im.save(out_path)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd')
        tc_pr.append(shd)
    shd.set(qn('w:fill'), fill.replace('#', ''))


def set_cell_border(cell, color='D9E2EC', sz='6'):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in('w:tcBorders')
    if borders is None:
        borders = OxmlElement('w:tcBorders')
        tc_pr.append(borders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = 'w:' + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn('w:val'), 'single')
        element.set(qn('w:sz'), sz)
        element.set(qn('w:space'), '0')
        element.set(qn('w:color'), color)


def set_cell_text(cell, text, bold=False, color=TEXT, size=8.4, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(text))
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = 'Microsoft YaHei'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    r.font.color.rgb = RGBColor.from_string(color.replace('#', ''))
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    set_cell_border(cell)


def add_table(doc, headers, rows, widths=None, font_size=8.2):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_text(cell, h, bold=True, color='FFFFFF', size=font_size)
        set_cell_shading(cell, NAVY)
        if widths:
            cell.width = Inches(widths[i])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            set_cell_text(cells[i], val, size=font_size)
            if ridx % 2 == 1:
                set_cell_shading(cells[i], 'F4F7FA')
            if widths:
                cells[i].width = Inches(widths[i])
    table.style = 'Table Grid'
    return table


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(82, 96, 109)


def add_body(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(6)
    if bold_lead and text.startswith(bold_lead):
        r = p.add_run(bold_lead)
        r.bold = True
        r.font.name = 'Microsoft YaHei'
        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
        rest = text[len(bold_lead):]
        r2 = p.add_run(rest)
        r2.font.name = 'Microsoft YaHei'
        r2._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    else:
        r = p.add_run(text)
        r.font.name = 'Microsoft YaHei'
        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet' if level == 0 else 'List Bullet 2')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.name = 'Microsoft YaHei'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    return p


def add_code(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.4)
        p.paragraph_format.space_after = Pt(1)
        r = p.add_run(line)
        r.font.name = 'Consolas'
        r._element.rPr.rFonts.set(qn('w:ascii'), 'Consolas')
        r.font.size = Pt(8.4)
        r.font.color.rgb = RGBColor(38, 50, 56)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run('第 ')
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    run._r.addnext(fld)
    paragraph.add_run(' 页')


def configure_styles(doc):
    styles = doc.styles
    normal = styles['Normal']
    normal.font.name = 'Microsoft YaHei'
    normal._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    normal.font.size = Pt(10.5)
    for name, size, color in [('Title', 24, NAVY), ('Heading 1', 16, NAVY), ('Heading 2', 12.5, TEXT), ('Heading 3', 11, TEXT)]:
        st = styles[name]
        st.font.name = 'Microsoft YaHei'
        st._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor.from_string(color.replace('#', ''))
        st.paragraph_format.space_before = Pt(12 if name != 'Title' else 0)
        st.paragraph_format.space_after = Pt(6)


def fmt(x, n=2):
    return f'{x:.{n}f}'


def make_summary_files():
    for name, rows in DATA['groups'].items():
        out = []
        for r in rows:
            out.append({
                'scenario': r['scenario'],
                'case_id': r['case'],
                'time_before_optim': round(r['baseline_runtime_s'], 3),
                'time_after_optim': round(r['optimized_runtime_s'], 3),
                'psnr': round(r['optimized_psnr_db'], 4),
                'psnr_before_optim': round(r['baseline_psnr_db'], 4),
                'speedup': round(r['speedup'], 4),
                'group': name,
            })
        (ROOT / f'summary_{name}.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')


def build_docx():
    full = DATA['groups']['full']
    short = DATA['groups']['short_2s']
    make_psnr_chart('full', full, ASSET_DIR / 'psnr_full.png', '完整组 PSNR 对比')
    make_psnr_chart('short', short, ASSET_DIR / 'psnr_short.png', '2 秒短测组 PSNR 对比')
    make_runtime_chart(full, short, ASSET_DIR / 'runtime_comparison.png')
    make_pipeline(ASSET_DIR / 'optimization_pipeline.png')
    make_log_excerpt(ASSET_DIR / 'log_excerpt.png')
    make_placeholder_panel(
        ASSET_DIR / 'placeholder_runtime.png',
        '运行界面截图（待补）',
        ['建议内容：VS Code 远程终端或 SSH 终端，能看到命令、场景/case、real 时间和输出路径。',
         '建议文件名：runtime_stackbox_case1.png；可替换为任一正式优化 case 的完整界面截图。'],
    )
    make_placeholder_panel(
        ASSET_DIR / 'placeholder_frames.png',
        '视频帧截图（待补）',
        ['建议内容：stackbox 与 cleanup_pencils 各放一组首帧/中间帧/末帧，并标注场景、case 和帧位置。',
         '建议文件名：frames_stackbox_case1.png、frames_cleanup_case1.png。'],
    )
    make_summary_files()

    doc = Document()
    configure_styles(doc)
    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.1)
    sec.right_margin = Cm(2.1)
    sec.header_distance = Cm(0.8)
    sec.footer_distance = Cm(0.8)
    header = sec.header.paragraphs[0]
    header.text = 'ASC27 赛题二 | 具身世界模型推理优化与复现'
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size = Pt(8)
    header.runs[0].font.color.rgb = RGBColor(82, 96, 109)
    add_page_number(sec.footer.paragraphs[0])

    # Cover
    p = doc.add_paragraph(style='Title')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(90)
    p.add_run('ASC27 赛题二\n具身世界模型推理优化与复现').font.name = 'Microsoft YaHei'
    p.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_before = Pt(18)
    sub.paragraph_format.space_after = Pt(65)
    rr = sub.add_run('UnifoLM-WMA-0 · Unitree Z1 双臂场景')
    rr.font.size = Pt(15)
    rr.font.color.rgb = RGBColor.from_string(MUTED.replace('#', ''))
    for line in ['参赛题目：ASC 2027 院内选拔赛赛题二', '选取场景：unitree_z1_dual_arm_stackbox、unitree_z1_dual_arm_cleanup_pencils', '实验平台：AutoDL NVIDIA RTX 3090 24 GB', '报告日期：2026 年 10 月 30 日']:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(7)
        p.add_run(line).font.size = Pt(11)
    doc.add_page_break()

    doc.add_heading('摘要', level=1)
    add_body(doc, '本报告记录了 UnifoLM-WMA-0 在两个 Unitree Z1 双臂场景上的复现、基线测量和推理优化。实验保留官方 DDIM 步数、帧步长、视频长度和完整交互轮次；另设置 n_iter=1 的短测组，用于观察约 2 秒输出时的速度上限。实现中使用 FP16 autocast、条件与采样器缓存、关闭中间视频和 TensorBoard 写盘、GPU 端视频累积拼接、固定 CPU/GPU 线程以及 cuDNN benchmark。')
    add_body(doc, '在统一队列的 8 个完整样本上，平均推理加速比为 2.395×，平均 PSNR 从 23.38 dB 变为 23.09 dB；在 8 个短测样本上，平均加速比为 1.745×，平均 PSNR 从 28.98 dB 变为 28.97 dB。短测组全部达到题目要求的 25 dB 阈值；完整组中仍存在低于 25 dB 的样本，因此完整组结果应理解为性能优化与误差分析结果，而不是宣称通过官方场景级门槛。')
    add_body(doc, '关键词：具身世界模型；UnifoLM-WMA-0；推理优化；FP16；I/O 流水线；PSNR；DDIM')

    doc.add_heading('目录与报告范围', level=1)
    for item in ['1 任务要求与评测口径', '2 软件、数据与实验环境', '3 官方基线复现', '4 优化设计与实现', '5 优化探针与取舍', '6 实验结果与分析', '7 复现命令与结果文件', '8 结论与后续工作', '附录 A 详细结果表', '附录 B 结果目录与提交说明']:
        add_bullet(doc, item)

    doc.add_heading('1 任务要求与评测口径', level=1)
    add_body(doc, '赛题要求从 UnifoLM-WMA-0 提供的场景中任选两个，完成安装、数据准备、推理复现和推理性能优化；每个样本需要输出完整视频，记录优化前后的 inference time，并使用官方 PSNR 脚本评价视觉质量。题面给出的质量门槛为 PSNR ≥ 25 dB，且任一样本不达标会影响对应场景的评分。')
    add_body(doc, '本实验选择 unitree_z1_dual_arm_stackbox 和 unitree_z1_dual_arm_cleanup_pencils，每个场景 4 个 case，共 8 个样本。实验分为两组：完整组使用 stackbox 的 n_iter=7、cleanup_pencils 的 n_iter=8；短测组统一使用 n_iter=1。两组使用同一套优化代码，短测只改变交互轮次。')
    add_body(doc, '推理时间以运行脚本输出的 real wall-clock 时间为准，计算公式为：加速比 = 基线时间 / 优化时间。PSNR 使用官方 psnr_score_for_challenge.py 对输出 MP4 与参考视频逐帧比较。')

    doc.add_heading('2 软件、数据与实验环境', level=1)
    env_rows = [
        ['模型项目', 'Unitree Robotics UnifoLM-WMA-0-Dual', 'https://github.com/unitreerobotics/unifolm-world-model-action'],
        ['赛事数据', 'ASC26 Embodied World Model Optimizations', 'https://github.com/ASC-Competition/ASC26-Embodied-World-Model-Optimization'],
        ['模型权重', 'UnifoLM-WMA-0-Dual checkpoint', 'https://huggingface.co/unitreerobotics/UnifoLM-WMA-0-Dual'],
        ['远程平台', 'AutoDL_3090；NVIDIA RTX 3090 24 GB；Linux 容器', 'SSH 端口 20740'],
        ['Python 环境', 'Conda 环境 asc_wma；PyTorch、xformers、open_clip、h5py、imageio', '以服务器已配置环境为准'],
        ['输入/输出', '数据盘：/root/autodl-tmp/asc27；结果：/root/asc27_system_results', '结果写入系统盘以避免数据盘空间不足'],
    ]
    add_table(doc, ['项目', '记录', '链接或说明'], env_rows, widths=[1.15, 2.75, 2.85], font_size=8.0)
    add_caption(doc, '表 1  软件、数据和实验环境记录')
    add_body(doc, '模型启动阶段加载 ViT-H-14 OpenCLIP 权重，并用图像特征形状、均值、标准差和有限性检查确认 image condition 可用。运行期间 GPU 显存占用约 22.8 GB，功耗观测约 348 W；报告中的时间比较是在同一远程实例、同一输入、同一 checkpoint 下完成的。')
    add_body(doc, '由于远程服务器已在实验材料采集完成后按要求关机，报告保留了系统盘结果目录、日志路径和统计 JSON 的记录；提交前应将这些目录中的 MP4 与 output.log 同步到代码仓库。')

    doc.add_heading('3 官方基线复现', level=1)
    base_rows = [
        ['DDIM steps', '50'], ['frame_stride', '4'], ['video_length', '16'], ['n_action_steps / exe_steps', '16 / 16'],
        ['stackbox n_iter', '7'], ['cleanup_pencils n_iter', '8'], ['短测 n_iter', '1'], ['seed', '123'],
        ['timestep_spacing', 'uniform_trailing'], ['guidance_rescale', '0.7'], ['ddim_eta', '1.0'],
    ]
    add_table(doc, ['参数', '取值'], base_rows, widths=[2.6, 4.15], font_size=8.5)
    add_caption(doc, '表 2  基线和正式优化共同采用的官方采样参数')
    add_body(doc, '基线版本仅修改数据路径和结果保存路径，调用原始 world_model_interaction.py；没有启用 AMP、fast_io、zero_pred_state 或其他优化开关。完整组和短测组分别单独运行并记录 real 时间及 PSNR，确保后续比较具有同一轮次口径。')
    add_code(doc, [
        'cd /root/autodl-tmp/asc27',
        'bash run_experiment.sh baseline_official_full_system unitree_z1_dual_arm_stackbox 1 \\',
        '  50 7 16 4 0 1.0 scripts/evaluation/world_model_interaction.py \\',
        '  0 0.7 uniform_trailing 123 1.0 0',
    ])
    add_body(doc, '基线输出目录分别为 /root/asc27_system_results/baseline_official_full_system 和 baseline_official_short_system。两组共生成 16 个 psnr.json 和 16 个完整 MP4；每个 case 的真实 wall-clock 时间来自对应 run.log。')

    doc.add_heading('4 优化设计与实现', level=1)
    doc.add_picture(str(ASSET_DIR / 'optimization_pipeline.png'), width=Inches(6.55))
    add_caption(doc, '图 1  最终优化方案的数据流和计算流')
    add_body(doc, '实现时保留官方的视频长度、DDIM 步数、frame_stride 和完整交互轮次，主要处理重复计算、同步等待和不必要的 I/O。可能改变结果口径的设置单独测试，再根据 PSNR 和稳定性决定是否使用。')

    doc.add_heading('4.1 不改变结果口径的工程优化', level=2)
    add_bullet(doc, '推理阶段使用 torch.no_grad，并将生成函数放在 no-grad 路径中，避免建立训练反向图和保存无用中间激活。前向算子和采样步数保持不变。')
    add_bullet(doc, '启用 CUDA FP16 autocast。模型 checkpoint 本身不被永久转换为半精度，主要计算在 autocast 上下文中执行；FP32 probe 显示完全 FP32 的速度只有约 1.28×，因此 FP16 是达到目标加速比的关键。')
    add_bullet(doc, 'fast_io 路径跳过动作分支视频解码、中间迭代视频、TensorBoard event 和逐轮 MP4 编码，只保留最终拼接视频及必要的 PSNR 文件。逐轮视频写盘会迫使 GPU 等待 CPU 编码和文件系统。')
    add_bullet(doc, '世界模型交互产生的 pred_videos_1 保留在 GPU 上，先在显存中累积每轮执行片段，全部迭代结束后再一次性拼接、传回 CPU 和编码，减少每轮 GPU-CPU 往返。')
    add_bullet(doc, 'DDIMSampler 对象挂在 model 上复用；文本 instruction 的 learned conditioning 按 prompt tuple 缓存，避免每次交互重复构造相同文本条件。图像条件不强行跨轮复用，因为交互后的图像会变化。')
    add_bullet(doc, '设置 torch.backends.cudnn.benchmark=True，并固定 OMP_NUM_THREADS、MKL_NUM_THREADS、OPENBLAS_NUM_THREADS=8，减少卷积算法选择和 CPU 线程过度竞争带来的抖动。')
    add_bullet(doc, 'OpenCLIP 权重在进程启动阶段加载并完成可用性检查，不在每一轮重新加载；日志级别降低，避免 PIL、h5py 等库的冗余输出淹没真正的推理阶段。')

    doc.add_heading('4.2 结果口径敏感的算法侧尝试', level=2)
    add_body(doc, '单独测试了 zero_pred_state。它在世界模型交互阶段不回灌预测状态，速度开销几乎不变；但在 stackbox case3 的对照中，AMP+fast_io+zero_pred_state 的 PSNR 为 24.2687 dB，关闭该开关为 26.2456 dB。因此保留预测状态，不启用 zero_pred_state。')
    add_body(doc, 'DDIM 步数从 50 降到 30 的 probe 将完整组速度提高到约 3.6×，但 cleanup_pencils case1 的 PSNR 从约 20.94 dB 降到 19.31 dB，且没有改善 25 dB 门槛问题，因此只作为极限速度参考，不纳入最终方案。')
    add_body(doc, 'torch.compile probe 受到 einops、xformers 和动态形状影响，出现 Dynamo cache-limit/recompilation 警告，首轮 CPU 占满而 GPU 利用率下降；CUDA Graph 的静态 Conv3D capture/replay 小探针可以通过，但完整链路包含随机噪声、动态条件和动态 shape，不能直接套用。两者均未纳入正式结果。')
    add_body(doc, 'FP32+fast_io+不置零的 case3 probe 达到 26.7792 dB，但耗时 11m49.5s，约 1.28× 加速；它说明 FP32 更稳，却不满足题目希望达到的 1.7× 左右速度目标。最终采用 FP16 autocast 与不置零状态的折中。')

    doc.add_heading('4.3 最终运行配置', level=2)
    add_code(doc, [
        'bash run_experiment.sh opt_amp_fastio_gpuaccum_nozero <scenario> <case> \\',
        '  50 <n_iter> 16 4 1 1.0 \\',
        '  scripts/evaluation/world_model_interaction_optimized.py \\',
        '  0 0.7 uniform_trailing 123 1.0 1',
    ])
    add_body(doc, '完整组的 <n_iter> 为 stackbox=7、cleanup_pencils=8；短测组仅把 <n_iter> 改为 1，其他选项完全相同。因此两组的差别只来自交互轮次。')

    doc.add_heading('5 优化探针与取舍', level=1)
    probe_rows = [
        ['AMP + zero_state + fast_io', '约 2.4×', 'stackbox case3 24.2687 dB', '否', 'zero_pred_state 导致质量明显下降'],
        ['AMP + fast_io + 不置零', '约 2.4×', 'stackbox case3 26.2456 dB；cleanup case1 20.31 dB', '是', '正式最终方案'],
        ['DDIM 50 → 30', '约 3.6×', 'cleanup case1 19.3118 dB', '否', '速度极限参考'],
        ['FP32 + fast_io + 不置零', '约 1.28×', 'stackbox case3 26.7792 dB', '否', '质量较稳但速度不足'],
        ['torch.compile', '不稳定', '动态重编译、GPU 利用率下降', '否', '完整链路不适合'],
        ['CUDA Graph', '静态小探针通过', '完整链路存在动态条件/shape', '否', '只保留探针结论'],
    ]
    add_table(doc, ['方案', '速度表现', '质量/稳定性证据', '纳入正式方案', '结论'], probe_rows, widths=[1.35, 0.8, 2.1, 0.8, 1.75], font_size=7.3)
    add_caption(doc, '表 3  优化探针、证据和最终取舍')

    doc.add_heading('6 实验结果与分析', level=1)
    doc.add_picture(str(ASSET_DIR / 'runtime_comparison.png'), width=Inches(6.55))
    add_caption(doc, '图 2  8 个完整样本和 8 个短测样本的时间对比；绿色标注为单 case 加速比')
    doc.add_picture(str(ASSET_DIR / 'psnr_full.png'), width=Inches(6.55))
    add_caption(doc, '图 3  完整组 PSNR；红线为题面 25 dB 阈值')
    doc.add_picture(str(ASSET_DIR / 'psnr_short.png'), width=Inches(6.55))
    add_caption(doc, '图 4  2 秒短测组 PSNR；红线为题面 25 dB 阈值')
    add_body(doc, '完整组平均从 23.38 dB 变为 23.09 dB，平均加速 2.395×。stackbox case1、case2、case4 的质量变化很小，case3 下降 1.19 dB；cleanup_pencils case2、case3 基本持平，case1 和 case4 分别下降 0.63 dB 和 0.86 dB。速度提升均高于 1.7×，质量下降主要出现在半精度和跨轮世界模型误差累积环节，I/O 修改本身没有明显影响。')
    add_body(doc, '短测组平均从 28.98 dB 变为 28.97 dB，平均加速 1.745×，8 个 case 全部高于 25 dB。短测只执行一次世界模型交互，因此误差不会经历完整组的多轮累积；这也解释了为什么短测 PSNR 通常明显高于完整组。短测结果适合作为速度上限和工程流水线对照，不应替代题面官方完整轮次的最终分数。')
    add_body(doc, '按照题面“任一样本低于 25 dB 会影响场景评分”的规则，当前完整组两个场景都存在低于 25 dB 的 case，因此完整组尚不能宣称通过官方质量门槛。这些数值原样保留，后续质量优化可以据此定位具体 case。')
    add_body(doc, '由于 GPU 推理、xformers 算子和半精度路径存在非完全确定性，同一配置重复运行的 PSNR 会有波动。例如 cleanup case1 的单独不置零 probe 为 21.2404 dB，而统一队列结果为 20.3101 dB。最终表格采用统一队列的单次结果，所有基线和优化结果均在同一批次内进行比较。')

    doc.add_heading('7 复现命令与结果文件', level=1)
    add_body(doc, '推荐按以下顺序复现：先运行官方基线，再运行最终优化；每个 case 完成后使用官方脚本计算 PSNR。')
    add_code(doc, [
        '# baseline',
        'bash run_experiment.sh baseline_official_full_system unitree_z1_dual_arm_stackbox 1 50 7 16 4 0 1.0 scripts/evaluation/world_model_interaction.py 0 0.7 uniform_trailing 123 1.0 0',
        '# optimized full',
        'bash run_experiment.sh opt_amp_fastio_gpuaccum_nozero unitree_z1_dual_arm_stackbox 1 50 7 16 4 1 1.0 scripts/evaluation/world_model_interaction_optimized.py 0 0.7 uniform_trailing 123 1.0 1',
        '# PSNR',
        'python psnr_score_for_challenge.py --gt_video <gt.mp4> --pred_video <pred.mp4> --output_file <psnr.json>',
    ])
    add_body(doc, '最终结果目录结构如下。每个 case 目录包含完整 MP4、output.log 和 psnr.json；最终汇总文件包括 final_report.json、summary_full.json 和 summary_short_2s.json。')
    add_code(doc, [
        '/root/asc27_system_results/',
        '├── baseline_official_full_system/<scenario>/case1..case4/',
        '├── baseline_official_short_system/<scenario>/case1..case4/',
        '├── optimization_runs/opt_amp_fastio_gpuaccum_nozero/<scenario>/case1..case4/',
        '├── optimization_runs/opt_amp_fastio_gpuaccum_nozero_short/<scenario>/case1..case4/',
        '├── final_report.json',
        '└── final_report.md',
    ])
    add_picture = doc.add_picture(str(ASSET_DIR / 'log_excerpt.png'), width=Inches(6.55))
    add_caption(doc, '图 5  运行日志摘录：包含实验参数、real 时间和 PSNR 输出')
    doc.add_heading('7.1 运行界面截图（提交前替换）', level=2)
    doc.add_picture(str(ASSET_DIR / 'placeholder_runtime.png'), width=Inches(6.55))
    add_caption(doc, '图 6  运行界面截图预留位置；替换为真实终端或 VS Code 远程终端截图')
    doc.add_heading('7.2 视频帧截图（提交前替换）', level=2)
    doc.add_picture(str(ASSET_DIR / 'placeholder_frames.png'), width=Inches(6.55))
    add_caption(doc, '图 7  视频帧截图预留位置；替换为最终 MP4 的首帧、中间帧和末帧')
    add_body(doc, '替换时建议至少保留一个 stackbox case 和一个 cleanup_pencils case，并在图片下方写明场景、case、帧位置和对应 MP4 文件名。运行界面截图应能看到命令、实验参数、real 时间和输出路径。')

    doc.add_heading('8 结论与后续工作', level=1)
    add_body(doc, '本次工作完成了两个场景、两种轮次设置，以及基线、优化和评测。工程侧减少了中间视频编码、TensorBoard 写盘和 GPU-CPU 往返；算法侧通过 sampler/text cache 复用减少重复准备，并用 zero_state、DDIM30、FP32、torch.compile 与 CUDA Graph 探针检查速度和质量的变化。AMP+fast_io+保留预测状态的方案在完整组平均加速 2.395×，短测平均加速 1.745×。')
    add_body(doc, '下一步若要满足完整组的严格 25 dB 门槛，应优先针对 stackbox case1、cleanup_pencils case1/4 做质量恢复，而不是继续降低 DDIM 步数。建议保持 fast_io、GPU 累积和缓存不变，分别尝试 FP32 关键模块、确定性设置、分阶段 AMP，以及对多轮状态/动作条件的更细粒度缓存，并对每个 case 至少重复运行两次后取稳定统计。')
    add_body(doc, '项目提交时应将完整源代码、README、summary JSON、每个 case 的 MP4 和 output.log 一并上传 GitHub 或 Gitee，并在报名系统登记仓库链接。')

    doc.add_heading('附录 A 详细结果表', level=1)
    headers = ['场景', 'case', '基线时间(s)', '优化时间(s)', '加速比', '基线 PSNR', '优化 PSNR', 'ΔPSNR', '25 dB']
    for group_title, rows in [('完整组', full), ('2 秒短测组', short)]:
        doc.add_heading(group_title, level=2)
        for scenario in ['unitree_z1_dual_arm_stackbox', 'unitree_z1_dual_arm_cleanup_pencils']:
            sub = [r for r in rows if r['scenario'] == scenario]
            table_rows = []
            for r in sub:
                table_rows.append([short_name(scenario), r['case'], fmt(r['baseline_runtime_s']), fmt(r['optimized_runtime_s']), fmt(r['speedup']), fmt(r['baseline_psnr_db']), fmt(r['optimized_psnr_db']), f"{r['psnr_delta_db']:+.2f}", '达标' if r['optimized_psnr_db'] >= 25 else '未达标'])
            add_table(doc, headers, table_rows, widths=[1.15, 0.38, 0.85, 0.85, 0.65, 0.75, 0.75, 0.65, 0.65], font_size=7.1)
            add_caption(doc, f"表 A-{1 if group_title == '完整组' and 'stackbox' in scenario else 2 if group_title == '完整组' else 3 if 'stackbox' in scenario else 4}  {group_title} {short_name(scenario)} 详细结果")

    doc.add_heading('附录 B 结果目录与提交说明', level=1)
    add_bullet(doc, '代码仓库：提交时请提供包含 unifolm-world-model-action、优化脚本、运行脚本和 README 的 GitHub/Gitee 链接。')
    add_bullet(doc, '结果仓库：按场景/case 保存 MP4 与 output.log，并在根目录提供 summary_full.json、summary_short_2s.json。')
    add_bullet(doc, '报告附件：本报告 PDF/DOCX、PSNR 图、时间图、运行日志摘录图和优化流程图。')
    add_bullet(doc, '复现实验：使用相同 checkpoint、seed=123、DDIM 50、frame_stride=4 和对应 n_iter；不同 GPU 可能产生轻微 PSNR 差异。')

    out = ROOT / 'ASC27_world_model_optimization_report.docx'
    doc.save(out)
    return out


if __name__ == '__main__':
    out = build_docx()
    print(out)
