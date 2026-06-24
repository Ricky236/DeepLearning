"""Jupyter notebook environment bootstrap for Bridge/课程设计.ipynb."""
from __future__ import annotations

import json
import platform
import sys
import warnings
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


def _configure_matplotlib_fonts() -> tuple[str | None, FontProperties | None]:
    """Register a CJK font file and set it as the default matplotlib font."""
    if sys.platform == "win32":
        font_files = [
            Path(r"C:/Windows/Fonts/msyh.ttc"),
            Path(r"C:/Windows/Fonts/msyhbd.ttc"),
            Path(r"C:/Windows/Fonts/simhei.ttf"),
            Path(r"C:/Windows/Fonts/simsun.ttc"),
        ]
    elif sys.platform == "darwin":
        font_files = [
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/System/Library/Fonts/STHeiti Light.ttc"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
        ]
    else:
        font_files = [
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        ]

    for fp in font_files:
        if fp.exists():
            font_manager.fontManager.addfont(str(fp))
            name = FontProperties(fname=str(fp)).get_name()
            prop = FontProperties(fname=str(fp))
            mpl.rcParams.update(
                {
                    "font.family": name,
                    "font.sans-serif": [name],
                    "axes.unicode_minus": False,
                    "mathtext.fontset": "stix",
                    "mathtext.rm": "Times New Roman",
                    "axes.titlelocation": "center",
                    "figure.titlesize": 12,
                    "axes.titlesize": 11,
                    "axes.labelsize": 10,
                    "xtick.labelsize": 9,
                    "ytick.labelsize": 9,
                    "legend.fontsize": 9,
                }
            )
            return name, prop

    # Fallback: match by installed font name
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "STSong",
        "PingFang SC",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    sans = [name for name in candidates if name in available]
    if sans:
        name = sans[0]
        mpl.rcParams.update(
            {
                "font.family": name,
                "font.sans-serif": sans,
                "axes.unicode_minus": False,
                "mathtext.fontset": "stix",
                "mathtext.rm": "Times New Roman",
                "axes.titlelocation": "center",
                "figure.titlesize": 12,
                "axes.titlesize": 11,
                "axes.labelsize": 10,
                "xtick.labelsize": 9,
                "ytick.labelsize": 9,
                "legend.fontsize": 9,
            }
        )
        return name, FontProperties(family=name)

    mpl.rcParams["axes.unicode_minus"] = False
    return None, None


_CJK_FONT, CJK_FONT_PROP = _configure_matplotlib_fonts()
_CJK_FONT_FILE = CJK_FONT_PROP.get_file() if CJK_FONT_PROP and CJK_FONT_PROP.get_file() else None

# Import pyplot only after CJK font is configured.
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, Markdown, display
from PIL import Image

_CENTER_CSS = """
<style>
.jp-OutputArea-output img, div.output_area img {
    display: block !important; margin-left: auto !important; margin-right: auto !important;
}
.jp-OutputArea-output .jp-RenderedHTMLCommon, div.output_html { text-align: center; }
.jp-RenderedHTMLCommon table.dataframe, table.dataframe {
    margin-left: auto; margin-right: auto; text-align: center;
}
.jp-RenderedHTMLCommon table.dataframe th, .jp-RenderedHTMLCommon table.dataframe td,
table.dataframe th, table.dataframe td { text-align: center; }
.jp-RenderedHTMLCommon .MathJax_Display, .MathJax_Display,
.jp-MarkdownCell .MathJax_Display, .jp-RenderedMarkdown .MathJax_Display {
    text-align: center !important; margin-left: auto !important; margin-right: auto !important;
}
.jp-MarkdownCell .jp-RenderedMarkdown table {
    margin-left: auto; margin-right: auto; text-align: center;
}
</style>
"""
display(HTML(_CENTER_CSS))


def display_table(df: pd.DataFrame, highlight_max: bool = False, **highlight_kw):
    styler = df.style.set_properties(**{"text-align": "center"})
    styler = styler.set_table_styles([
        {"selector": "th", "props": [("text-align", "center")]},
        {"selector": "td", "props": [("text-align", "center")]},
        {"selector": "table", "props": [("margin-left", "auto"), ("margin-right", "auto")]},
    ])
    if highlight_max:
        styler = styler.highlight_max(axis=highlight_kw.get("axis", 0), color=highlight_kw.get("color", "#d4edda"))
    display(styler)


FIG_TITLE_FONT = 11  # 全篇图题统一字号
FIG_LEGEND_FONT = 9


def cjk_font(size: int | None = None) -> FontProperties | None:
    """Return FontProperties for Chinese text."""
    if _CJK_FONT_FILE:
        fp = FontProperties(fname=_CJK_FONT_FILE)
    elif _CJK_FONT:
        fp = FontProperties(family=_CJK_FONT)
    else:
        return None
    if size is not None:
        fp.set_size(size)
    return fp


def _apply_cjk_to_figure(fig) -> None:
    """Ensure axis labels, ticks and legend use the CJK font."""
    fp_label = cjk_font(10)
    fp_tick = cjk_font(9)
    fp_title = cjk_font(FIG_TITLE_FONT)
    if fp_label is None:
        return
    for ax in fig.get_axes():
        xlabel, ylabel, title = ax.get_xlabel(), ax.get_ylabel(), ax.get_title()
        if xlabel:
            ax.set_xlabel(xlabel, fontproperties=fp_label)
        if ylabel:
            ax.set_ylabel(ylabel, fontproperties=fp_label)
        if title and fp_title:
            ax.set_title(title, fontproperties=fp_title)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(fp_tick)
        legend = ax.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                text.set_fontproperties(fp_tick)


def display_markdown_center(text: str):
    display(HTML(f'<div style="text-align:center;font-size:{FIG_TITLE_FONT}pt;font-weight:bold;margin:0.5em auto;">'))
    display(Markdown(text))
    display(HTML("</div>"))


def figure_caption(no: int, title: str) -> str:
    return f"图 {no}  {title}"


def set_figure_title(ax, no: int, title: str, **kwargs):
    """Set axis title with unified figure number and CJK font."""
    fp = cjk_font(kwargs.pop("fontsize", FIG_TITLE_FONT))
    cap = figure_caption(no, title)
    if fp is not None:
        ax.set_title(cap, fontproperties=fp, **kwargs)
    else:
        ax.set_title(cap, fontsize=FIG_TITLE_FONT, **kwargs)


def set_figure_suptitle(fig, no: int, title: str, **kwargs):
    """Set figure suptitle with unified figure number and CJK font."""
    fp = cjk_font(kwargs.pop("fontsize", FIG_TITLE_FONT))
    cap = figure_caption(no, title)
    kwargs.setdefault("ha", "center")
    if fp is not None:
        fig.suptitle(cap, fontproperties=fp, **kwargs)
    else:
        fig.suptitle(cap, fontsize=FIG_TITLE_FONT, **kwargs)


def finalize_figure(fig=None):
    if fig is None:
        fig = plt.gcf()
    title_fp = cjk_font(FIG_TITLE_FONT)
    if fig._suptitle is not None:
        fig._suptitle.set_ha("center")
        if title_fp is not None:
            fig._suptitle.set_fontproperties(title_fp)
    _apply_cjk_to_figure(fig)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*Glyph.*missing from font.*")
        fig.tight_layout()
    plt.show()


ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
if not (ROOT / "app.py").exists():
    for p in [Path.cwd(), *Path.cwd().parents]:
        if (p / "app.py").exists() and (p / "图片").is_dir():
            ROOT = p
            break
    else:
        for p in [Path.cwd(), *Path.cwd().parents]:
            if (p / "app.py").exists():
                ROOT = p
                break

MODELS_DIR = ROOT / "models"
RESULT_DIR = ROOT / "results"
TRAIN_DIR = ROOT / "train_model"
CONFIG_DIR = TRAIN_DIR / "configs"

CLASS_NAME_CN = {
    "Crack-Detection": "裂缝",
    "Exposed Rebar": "钢筋外露",
    "Spalling": "剥落",
    "Break": "破损",
    "Efflorescence": "白华",
}

EXPERIMENT_MAP = {
    "model1": ("baseline", "YOLO11n-seg 基线"),
    "model2": ("exp1", "Exp1: P2 分割头"),
    "model3": ("exp2", "Exp2: BiFPN 融合"),
    "model4": ("exp3", "Exp3: MSDC 多尺度卷积"),
    "model5": ("exp4", "Exp4: CGA 通道注意力"),
    "model6": ("exp5", "Exp5: SGA 空间注意力"),
    "model7": ("exp6", "Exp6: GRB 残差块"),
    "model8": ("exp7", "Exp7: 完整模型 + 损失增强"),
}

MODEL_FOLDER = {
    "model1": "model1.0",
    "model2": "model2.0",
    "model3": "model3.0",
    "model4": "model4.0",
    "model5": "model5.0",
    "model6": "model6.0",
    "model7": "model7.0",
    "model8": "model8.0",
}

DATA_DIR = ROOT / "data"
DATA_SPLITS = ["train", "valid", "test"]
CLASS_IDS_CN = ["裂缝", "钢筋外露", "剥落", "破损", "白华"]
_SEG_COLORS = ["#ef4444", "#3b82f6", "#facc15", "#8b5a2b", "#a855f7"]


def _label_image_path(label_path: Path) -> Path | None:
    """Map a label file under data/{split}/labels to its image in images/."""
    stem = label_path.stem
    img_dir = label_path.parent.parent / "images"
    for ext in (".jpg", ".JPG", ".jpeg", ".png"):
        direct = img_dir / f"{stem}{ext}"
        if direct.exists():
            return direct
        hits = list(img_dir.rglob(f"{stem}{ext}"))
        if hits:
            return hits[0]
    return None


def parse_yolo_seg_label(text: str) -> list[tuple[int, list[float]]]:
    instances: list[tuple[int, list[float]]] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        cid = int(float(parts[0]))
        if cid >= len(CLASS_IDS_CN):
            continue
        instances.append((cid, [float(x) for x in parts[1:]]))
    return instances


def compute_dataset_stats(splits: tuple[str, ...] = ("train", "valid", "test")) -> tuple[dict, dict[str, int]]:
    """Return per-split stats and overall class instance counts (Chinese labels)."""
    from collections import Counter

    split_stats: dict[str, dict] = {}
    overall: Counter[int] = Counter()
    for split in splits:
        lbl_dir = DATA_DIR / split / "labels"
        if not lbl_dir.is_dir():
            continue
        per_class: Counter[int] = Counter()
        n_images = 0
        n_instances = 0
        for lp in lbl_dir.rglob("*.txt"):
            inst = parse_yolo_seg_label(lp.read_text(encoding="utf-8", errors="ignore"))
            if not inst:
                continue
            n_images += 1
            for cid, _ in inst:
                per_class[cid] += 1
                overall[cid] += 1
                n_instances += 1
        split_stats[split] = {
            "images": n_images,
            "instances": n_instances,
            "per_class": {CLASS_IDS_CN[k]: v for k, v in sorted(per_class.items())},
        }
    class_counter = {CLASS_IDS_CN[k]: overall[k] for k in sorted(overall)}
    return split_stats, class_counter


def pick_dataset_samples(split: str = "train", n_per_class: int = 1) -> list[tuple[Path, Path, int]]:
    """Pick up to n images per class that contain that class (for sample display)."""
    lbl_dir = DATA_DIR / split / "labels"
    buckets: dict[int, list[tuple[Path, Path, int]]] = {i: [] for i in range(len(CLASS_IDS_CN))}
    if not lbl_dir.is_dir():
        return []
    for lp in sorted(lbl_dir.rglob("*.txt")):
        inst = parse_yolo_seg_label(lp.read_text(encoding="utf-8", errors="ignore"))
        if not inst:
            continue
        img = _label_image_path(lp)
        if img is None:
            continue
        for cid in {c for c, _ in inst}:
            if len(buckets[cid]) < n_per_class:
                buckets[cid].append((img, lp, cid))
        if all(len(v) >= n_per_class for v in buckets.values()):
            break
    out: list[tuple[Path, Path, int]] = []
    for cid in range(len(CLASS_IDS_CN)):
        out.extend(buckets[cid])
    return out


def draw_seg_on_axis(ax, img_path: Path, label_path: Path, title: str = "", highlight_cid: int | None = None):
    from matplotlib.patches import Polygon

    img = np.array(Image.open(img_path).convert("RGB"))
    h, w = img.shape[:2]
    ax.imshow(img)
    for cid, coords in parse_yolo_seg_label(label_path.read_text(encoding="utf-8", errors="ignore")):
        if highlight_cid is not None and cid != highlight_cid:
            continue
        pts = np.array(coords, dtype=float).reshape(-1, 2)
        pts[:, 0] *= w
        pts[:, 1] *= h
        color = _SEG_COLORS[cid]
        ax.add_patch(
            Polygon(
                pts,
                closed=True,
                fill=True,
                facecolor=(*mpl.colors.to_rgb(color), 0.25),
                edgecolor=color,
                linewidth=2,
            )
        )
    fp = cjk_font(FIG_TITLE_FONT)
    if fp is not None:
        ax.set_title(title, fontproperties=fp, ha="center")
    else:
        ax.set_title(title, fontsize=FIG_TITLE_FONT, ha="center")
    ax.axis("off")


def show_dataset_samples(split: str = "train", fig_no: int | None = 1, fig_caption: str = "数据集样本：五类病害标注示意"):
    samples = pick_dataset_samples(split=split, n_per_class=1)
    if not samples:
        print(f"未在 {DATA_DIR / split} 找到可用样本")
        return
    ncols = min(3, len(samples))
    nrows = (len(samples) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    axes = np.array(axes).reshape(-1)
    for ax, (img, lbl, cid) in zip(axes, samples):
        draw_seg_on_axis(ax, img, lbl, CLASS_IDS_CN[cid], highlight_cid=cid)
    for ax in axes[len(samples):]:
        ax.axis("off")
    if fig_no is not None:
        set_figure_suptitle(fig, fig_no, fig_caption)
    finalize_figure(fig)


def dataset_class_correlation(split: str = "train") -> pd.DataFrame | None:
    """Per-image class instance counts -> Pearson correlation matrix."""
    lbl_dir = DATA_DIR / split / "labels"
    if not lbl_dir.is_dir():
        return None
    rows: list[dict[str, int]] = []
    for lp in lbl_dir.rglob("*.txt"):
        inst = parse_yolo_seg_label(lp.read_text(encoding="utf-8", errors="ignore"))
        if not inst:
            continue
        row = {cn: 0 for cn in CLASS_IDS_CN}
        for cid, _ in inst:
            row[CLASS_IDS_CN[cid]] += 1
        rows.append(row)
    if len(rows) < 3:
        return None
    return pd.DataFrame(rows).corr(numeric_only=True)


def split_stats_dataframe(split_stats: dict) -> pd.DataFrame:
    """Build a summary table for train/valid/test splits."""
    rows = []
    for split in DATA_SPLITS:
        if split not in split_stats:
            continue
        info = split_stats[split]
        row = {"划分": split, "含标注图像": info["images"], "实例总数": info["instances"]}
        for cn in CLASS_IDS_CN:
            row[cn] = info["per_class"].get(cn, 0)
        rows.append(row)
    return pd.DataFrame(rows)


def show_dataset_distribution(
    split_stats: dict,
    dataset_class_counter: dict[str, int],
    fig_no: int = 2,
    fig_caption: str = "数据集：各划分类别实例统计分布",
):
    """Grouped bar chart + overall pie chart for class instance distribution."""
    if not dataset_class_counter:
        print("未找到 data/ 标注文件，请确认数据集目录。")
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    splits = [s for s in DATA_SPLITS if s in split_stats]
    x = np.arange(len(CLASS_IDS_CN))
    width = 0.25
    for i, split in enumerate(splits):
        vals = [split_stats[split]["per_class"].get(cn, 0) for cn in CLASS_IDS_CN]
        axes[0].bar(x + (i - 1) * width, vals, width, label=split)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(CLASS_IDS_CN, rotation=15)
    axes[0].set_ylabel("实例数")
    axes[0].legend()
    axes[0].set_title("各划分类别实例分布")

    labels = list(dataset_class_counter.keys())
    values = np.array([dataset_class_counter[k] for k in labels], dtype=float)
    colors = ["#ef4444", "#3b82f6", "#facc15", "#8b5a2b", "#a855f7"]
    wedges, _, autotexts = axes[1].pie(
        values,
        labels=labels,
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        colors=colors,
        startangle=90,
        textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_fontproperties(cjk_font(9) or t.get_fontproperties())
    axes[1].set_title("全数据集类别占比")

    set_figure_suptitle(fig, fig_no, fig_caption)
    finalize_figure(fig)


def show_correlation_heatmap(corr: pd.DataFrame, fig_no: int = 3, title: str = "训练集：各类别实例数 Pearson 相关矩阵"):
    fig, ax = plt.subplots(figsize=(7, 5.5))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=35, ha="right")
    ax.set_yticklabels(corr.columns)
    n = len(corr.columns)
    for i in range(n):
        for j in range(n):
            val = corr.values[i, j]
            ax.text(
                j, i, f"{val:.2f}",
                ha="center", va="center", fontsize=8,
                color="white" if abs(val) > 0.5 else "black",
            )
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    set_figure_title(ax, fig_no, title)
    finalize_figure(fig)


def show_images(images, ncols=2, figsize_per_col=5.5, fig_no=None, fig_caption=""):
    images = [(t, p) for t, p in images if p.exists()]
    if not images:
        print("未找到可展示的图片")
        return
    nrows = (len(images) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(figsize_per_col * ncols, 4.5 * nrows))
    axes = np.array(axes).reshape(-1)
    sub_fp = cjk_font(FIG_TITLE_FONT)
    for ax, (title, path) in zip(axes, images):
        ax.imshow(Image.open(path))
        if sub_fp is not None:
            ax.set_title(title, fontproperties=sub_fp, ha="center")
        else:
            ax.set_title(title, fontsize=FIG_TITLE_FONT, ha="center")
        ax.axis("off")
    for ax in axes[len(images):]:
        ax.axis("off")
    if fig_no is not None:
        cap = figure_caption(fig_no, fig_caption) if fig_caption else f"图 {fig_no}"
        if sub_fp is not None:
            fig.suptitle(cap, ha="center", fontproperties=sub_fp)
        else:
            fig.suptitle(cap, ha="center", fontsize=FIG_TITLE_FONT)
    finalize_figure(fig)


def collect_train_artifacts(folder: str) -> dict[str, Path]:
    base = MODELS_DIR / folder
    keys = [
        "results.png", "BoxPR_curve.png", "MaskPR_curve.png", "BoxF1_curve.png", "MaskF1_curve.png",
        "confusion_matrix_normalized.png", "val_batch0_labels.jpg", "val_batch0_pred.jpg",
    ]
    return {k: base / k for k in keys if (base / k).exists()}


def find_compare_group():
    groups = {}
    for p in RESULT_DIR.glob("*_model*_result.json"):
        stem = p.name.replace("_result.json", "")
        base = stem.rsplit("_model", 1)[0]
        groups.setdefault(base, []).append(p)
    for base, files in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(files) < 2:
            continue
        items = []
        for p in sorted(files):
            data = json.loads(p.read_text(encoding="utf-8"))
            mid = data.get("model_id", p.stem.split("_")[-2])
            items.append({
                "path": p,
                "img": RESULT_DIR / f"{p.stem}.jpg",
                "data": data,
                "model_id": mid,
                "label": data.get("model_label", mid),
            })
        return base, items
    return None


def get_infer_ms(data: dict):
    for key in ("forward_ms", "inference_ms"):
        v = data.get(key)
        if v is not None:
            return float(v)
    return None


def pick_detection_samples(n: int = 3):
    records = []
    for p in RESULT_DIR.glob("*_result.json"):
        if "_model" in p.stem:
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        dets = data.get("detections") or []
        if not dets:
            continue
        top_conf = max(d.get("confidence", 0) for d in dets)
        top_cls = max(dets, key=lambda d: d.get("confidence", 0)).get("class_cn", "")
        records.append((top_conf, top_cls, p))
    records.sort(key=lambda x: -x[0])
    seen_cls, picked = set(), []
    for conf, cls, p in records:
        if cls not in seen_cls:
            picked.append(p)
            seen_cls.add(cls)
        if len(picked) >= n:
            break
    if len(picked) < n:
        for conf, cls, p in records:
            if p not in picked:
                picked.append(p)
            if len(picked) >= n:
                break
    return picked


PRINCIPLE_DIR = ROOT / "static" / "img" / "principles"
PRINCIPLE_SRC_DIR = ROOT / "图片"

PRINCIPLE_STATIC = {
    "yolo11": PRINCIPLE_DIR / "fig01_yolo11.png",
    "bifpn": PRINCIPLE_DIR / "fig02_bifpn.png",
    "msdc": PRINCIPLE_DIR / "fig03_msdc.png",
    "cga": PRINCIPLE_DIR / "fig04_cga.png",
    "sga": PRINCIPLE_DIR / "fig05_sga.png",
    "grb": PRINCIPLE_DIR / "fig06_grb.png",
    "seg_flow": PRINCIPLE_DIR / "fig07_seg_flow.png",
    "system": PRINCIPLE_DIR / "fig15_system.png",
    # 平台页面截图（来自 图片/ 目录，仅保留 8 张）
    "platform_home": PRINCIPLE_SRC_DIR / "首页.png",
    "platform_detect": PRINCIPLE_SRC_DIR / "病害检测.png",
    "platform_realtime": PRINCIPLE_SRC_DIR / "实时监测.png",
    "platform_analysis": PRINCIPLE_SRC_DIR / "病害分析.png",
    "platform_model_info": PRINCIPLE_SRC_DIR / "模型信息.png",
    "platform_report_gen": PRINCIPLE_SRC_DIR / "报告生成.png",
    "platform_auth": PRINCIPLE_SRC_DIR / "注册登录.png",
    "platform_latency": PRINCIPLE_SRC_DIR / "耗时.png",
}


def show_principle_diagram(key: str, caption: str = "", width: int = 920):
    from IPython.display import Image as IPImage

    path = PRINCIPLE_STATIC.get(key)
    if path is None:
        raise KeyError(f"未知图片 key: {key!r}")
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}\n请确认 {PRINCIPLE_SRC_DIR} 下文件齐全。")
    if caption:
        display(HTML(f'<div style="text-align:center;font-size:{FIG_TITLE_FONT}pt;font-weight:bold;margin:0.6em auto;">{caption}</div>'))
    display(IPImage(filename=str(path.resolve()), width=width))


# (key, 图题, 功能介绍)
PLATFORM_PAGES = [
    (
        "platform_home",
        "图 5  平台首页",
        "系统入口与数据概览：展示近 30 日检测次数、病害总数、平均耗时与模型使用分布，"
        "并提供各功能模块快捷入口。",
    ),
    (
        "platform_detect",
        "图 6  病害检测页面",
        "核心检测功能页：支持上传桥梁表观图像，选择消融实验模型（model1~model8），"
        "输出检测框、实例掩膜及裂缝/剥落等病害的长度、宽度等工程量化参数。",
    ),
    (
        "platform_realtime",
        "图 7  实时监测页面",
        "接入摄像头或视频流进行连续推理，适用于现场动态巡检场景，"
        "可实时叠加掩膜与量化结果，并记录监测事件。",
    ),
    (
        "platform_analysis",
        "图 8  病害分析页面",
        "对累积检测数据进行多维度统计分析，包括检测趋势、模型使用占比"
        "及各类病害分布，为养护决策提供数据支撑。",
    ),
    (
        "platform_model_info",
        "图 9  模型信息页面",
        "展示 8 组消融实验模型的 Box/Mask 精度指标对比、当前模型摘要"
        "及训练曲线（mAP 与损失），便于评估各改进模块效果。",
    ),
    (
        "platform_report_gen",
        "图 10  报告生成页面",
        "根据选定检测记录自动生成结构化巡检报告，"
        "支持 Word / PDF / Markdown 预览与导出。",
    ),
    (
        "platform_auth",
        "图 11  注册登录页面",
        "用户注册与登录入口，注册后可保存检测记录到账号历史，"
        "实现多用户隔离与个性化数据管理。",
    ),
    (
        "platform_latency",
        "图 12  推理耗时统计",
        "展示平台推理耗时分布与统计指标，反映各模型在实际部署中的"
        "响应速度与稳定性，辅助模型选型。",
    ),
]


def show_all_platform_pages(width: int = 960):
    """依次展示平台各功能页面截图及文字介绍。"""
    display(Markdown("### 平台页面展示（截图来源：`图片/` 目录）"))
    for key, caption, intro in PLATFORM_PAGES:
        display(HTML(f'<div style="font-size:{FIG_TITLE_FONT}pt;font-weight:bold;margin:0.8em 0 0.3em;">{caption}</div><div style="font-size:11pt;margin:0 0 0.6em;">{intro}</div>'))
        show_principle_diagram(key, caption="", width=width)
        display(HTML("<hr style='margin:1.2em auto;width:80%;'/>"))


print("项目根目录:", ROOT)
print("DATA_DIR:", DATA_DIR, "存在:", DATA_DIR.is_dir())
print("RESULT_DIR:", RESULT_DIR)
print("图片目录:", PRINCIPLE_SRC_DIR, "存在:", PRINCIPLE_SRC_DIR.exists())
print("Python:", sys.version.split()[0])
print("操作系统:", platform.platform())
print("matplotlib 中文字体:", _CJK_FONT or "未检测到（图表中文可能显示为方框）")
platform_ok = {k: v.exists() for k, v in PRINCIPLE_STATIC.items() if k.startswith("platform_")}
print("平台截图检查:", platform_ok)
