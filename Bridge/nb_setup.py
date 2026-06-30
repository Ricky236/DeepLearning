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
from IPython.display import HTML, Image as IPyImage, Markdown, display
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


def figure_caption(no: int, title: str) -> str:
    return f"图 {no}  {title}"


def center_markdown(*lines: str) -> str:
    """Build centered Markdown block (Jupyter renders <div align=\"center\">)."""
    body = "\n\n".join(line for line in lines if line)
    return f'<div align="center">\n\n{body}\n\n</div>'


def display_figure_caption(no: int, title: str) -> None:
    """Display figure number + title as centered Markdown below a figure."""
    display(Markdown(center_markdown(f"**{figure_caption(no, title)}**")))


def display_markdown_center(text: str) -> None:
    display(Markdown(center_markdown(text)))


def _register_fig_caption(fig, no: int, title: str) -> None:
    fig._nb_fig_no = no
    fig._nb_fig_caption = title


def set_figure_title(ax, no: int, title: str, **kwargs):
    """Register figure caption (centered Markdown below figure; not on the axes)."""
    _register_fig_caption(ax.figure, no, title)


def set_figure_suptitle(fig, no: int, title: str, **kwargs):
    """Register figure caption (centered Markdown below figure; not as suptitle)."""
    _register_fig_caption(fig, no, title)


def finalize_figure(fig=None):
    if fig is None:
        fig = plt.gcf()
    if fig._suptitle is not None:
        fig.suptitle("")
    _apply_cjk_to_figure(fig)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*Glyph.*missing from font.*")
        warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
        fig.tight_layout()
    plt.show()
    no = getattr(fig, "_nb_fig_no", None)
    cap = getattr(fig, "_nb_fig_caption", None)
    if no is not None and cap:
        display_figure_caption(no, cap)


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
if not DATA_DIR.is_dir():
    for candidate in [ROOT.parent / "Bridge" / "data", Path.cwd() / "data"]:
        if candidate.is_dir():
            DATA_DIR = candidate
            break
DATA_SPLITS = ["train", "valid", "test"]
CLASS_IDS_CN = ["裂缝", "钢筋外露", "剥落", "破损", "白华"]
_SEG_COLORS = ["#ef4444", "#3b82f6", "#facc15", "#8b5a2b", "#a855f7"]
DATASET_STATS_CACHE = ROOT / "dataset_stats_cache.json"


def _data_labels_available() -> bool:
    return any((DATA_DIR / split / "labels").is_dir() for split in DATA_SPLITS)


def _load_dataset_cache() -> dict | None:
    if not DATASET_STATS_CACHE.is_file():
        return None
    try:
        return json.loads(DATASET_STATS_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_dataset_cache(
    split_stats: dict,
    class_counter: dict[str, int],
    correlation_train: dict | None = None,
) -> None:
    payload = {
        "description": "Auto-generated from data/; committed for GitHub notebook display",
        "split_stats": split_stats,
        "class_counter": class_counter,
        "correlation_train": correlation_train,
    }
    DATASET_STATS_CACHE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _compute_dataset_stats_live(
    splits: tuple[str, ...] = ("train", "valid", "test"),
) -> tuple[dict, dict[str, int]]:
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


def compute_dataset_stats(splits: tuple[str, ...] = ("train", "valid", "test")) -> tuple[dict, dict[str, int]]:
    """Return per-split stats from dataset_stats_cache.json (no data/ scan)."""
    cache = _load_dataset_cache()
    if cache and cache.get("split_stats") and cache.get("class_counter"):
        return cache["split_stats"], cache["class_counter"]
    if _data_labels_available():
        split_stats, class_counter = _compute_dataset_stats_live(splits)
        if split_stats:
            corr = _compute_correlation_live("train")
            _save_dataset_cache(
                split_stats,
                class_counter,
                corr.to_dict() if corr is not None else None,
            )
            return split_stats, class_counter
    print("[dataset] 未找到 dataset_stats_cache.json，且 data/ 不可用")
    return {}, {}


def _compute_correlation_live(split: str = "train") -> pd.DataFrame | None:
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


def _label_image_path(label_path: Path) -> Path | None:
    """Map a label file under data/{split}/labels to its image in images/."""
    stem = label_path.stem
    img_dir = label_path.parent.parent / "images"
    if not img_dir.is_dir():
        return None
    for ext in (".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"):
        direct = img_dir / f"{stem}{ext}"
        if direct.is_file():
            return direct
    # case-insensitive / nested search
    for p in img_dir.rglob("*"):
        if p.is_file() and p.stem.lower() == stem.lower() and p.suffix.lower() in {
            ".jpg", ".jpeg", ".png"
        }:
            return p
    return None


def parse_yolo_seg_label(text: str) -> list[tuple[int, list[float]]]:
    """Parse YOLO label lines (bbox: 5 fields, seg: 3+ fields)."""
    instances: list[tuple[int, list[float]]] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        cid = int(float(parts[0]))
        if cid >= len(CLASS_IDS_CN):
            continue
        instances.append((cid, [float(x) for x in parts[1:]]))
    return instances


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
    from matplotlib.patches import Polygon, Rectangle

    img = np.array(Image.open(img_path).convert("RGB"))
    h, w = img.shape[:2]
    ax.imshow(img)
    for cid, coords in parse_yolo_seg_label(label_path.read_text(encoding="utf-8", errors="ignore")):
        if highlight_cid is not None and cid != highlight_cid:
            continue
        color = _SEG_COLORS[cid]
        if len(coords) == 4:
            cx, cy, bw, bh = coords
            x0 = (cx - bw / 2) * w
            y0 = (cy - bh / 2) * h
            ax.add_patch(
                Rectangle(
                    (x0, y0), bw * w, bh * h,
                    fill=True,
                    facecolor=(*mpl.colors.to_rgb(color), 0.25),
                    edgecolor=color,
                    linewidth=2,
                )
            )
        else:
            pts = np.array(coords, dtype=float).reshape(-1, 2)
            pts[:, 0] *= w
            pts[:, 1] *= h
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


def _cached_samples_preview() -> list[dict]:
    """Load committed preview images for §4.2.1 (samples_preview/)."""
    cache = _load_dataset_cache() or {}
    previews = cache.get("samples_preview") or []
    out: list[dict] = []
    for item in previews:
        rel = item.get("image", "")
        path = ROOT / rel
        if path.is_file():
            out.append(item)
    return sorted(out, key=lambda x: int(x.get("class_id", 0)))


def show_dataset_samples(split: str = "train", fig_no: int | None = 1, fig_caption: str = "数据集样本：五类病害分割标注示意"):
    previews = _cached_samples_preview()
    if not previews:
        print("未找到 samples_preview/ 缓存图片，请确认 dataset_stats_cache.json 与 samples_preview/ 已提交。")
        return
    ncols = min(3, len(previews))
    nrows = (len(previews) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    axes = np.array(axes).reshape(-1)
    sub_fp = cjk_font(FIG_TITLE_FONT)
    for ax, item in zip(axes, previews):
        ax.imshow(Image.open(ROOT / item["image"]))
        title = item.get("class_cn", "")
        if sub_fp is not None:
            ax.set_title(title, fontproperties=sub_fp, ha="center")
        else:
            ax.set_title(title, fontsize=FIG_TITLE_FONT, ha="center")
        ax.axis("off")
    for ax in axes[len(previews):]:
        ax.axis("off")
    if fig_no is not None and fig_caption:
        _register_fig_caption(fig, fig_no, fig_caption)
    finalize_figure(fig)


def dataset_class_correlation(split: str = "train") -> pd.DataFrame | None:
    """Pearson correlation matrix from dataset_stats_cache.json."""
    cache = _load_dataset_cache()
    corr_data = (cache or {}).get("correlation_train")
    if corr_data:
        return pd.DataFrame(corr_data)
    if _data_labels_available():
        corr = _compute_correlation_live(split)
        if corr is not None:
            return corr
    return None


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
    wedges, texts, autotexts = axes[1].pie(
        values,
        labels=labels,
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        colors=colors,
        startangle=90,
        textprops={"fontsize": 9},
    )
    label_fp = cjk_font(9)
    if label_fp is not None:
        for t in texts + autotexts:
            t.set_fontproperties(label_fp)
    axes[1].set_title("全数据集类别占比")

    _register_fig_caption(fig, fig_no, fig_caption)
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
    _register_fig_caption(fig, fig_no, title)
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
    if fig_no is not None and fig_caption:
        _register_fig_caption(fig, fig_no, fig_caption)
    finalize_figure(fig)


def _pick_viz_sample_image() -> tuple[Path | None, np.ndarray]:
    """Pick a bridge image from data/train for module visualization."""
    samples = pick_dataset_samples(split="train", n_per_class=1)
    if samples:
        img_path = samples[0][0]
        return img_path, np.array(Image.open(img_path).convert("RGB"))
    uploads = sorted((ROOT / "uploads").glob("*.*"))
    if uploads:
        return uploads[0], np.array(Image.open(uploads[0]).convert("RGB"))
    return None, np.zeros((320, 320, 3), dtype=np.uint8)


def _activation_heatmap(feat: "torch.Tensor", up_to: tuple[int, int] | None = None) -> np.ndarray:
  import torch
  f = feat.detach().float().cpu()
  if f.dim() == 4:
      f = f[0]
  hm = f.mean(0).numpy()
  hm = (hm - hm.min()) / (hm.max() - hm.min() + 1e-8)
  if up_to is not None:
      hm_img = Image.fromarray((hm * 255).astype(np.uint8)).resize(up_to, Image.BILINEAR)
      hm = np.array(hm_img) / 255.0
  return hm


def _overlay_heatmap(ax, img_rgb: np.ndarray, heatmap: np.ndarray, alpha: float = 0.45):
    ax.imshow(img_rgb)
    ax.imshow(heatmap, cmap="jet", alpha=alpha)
    ax.axis("off")


def _load_backbone_and_tensor(img_rgb: np.ndarray, size: int = 384):
  import torch
  import torch.nn as nn
  import torchvision.models as tvm

  weights = tvm.ResNet18_Weights.IMAGENET1K_V1
  mean = torch.tensor(weights.transforms().mean).view(1, 3, 1, 1)
  std = torch.tensor(weights.transforms().std).view(1, 3, 1, 1)
  img = Image.fromarray(img_rgb).resize((size, size), Image.BILINEAR)
  x = torch.from_numpy(np.array(img)).permute(2, 0, 1).float() / 255.0
  x = (x.unsqueeze(0) - mean) / std

  backbone = tvm.resnet18(weights=weights)
  backbone.eval()
  activations: dict[str, torch.Tensor] = {}

  def _hook(name):
      def fn(_m, _inp, out):
          activations[name] = out
      return fn

  backbone.layer1.register_forward_hook(_hook("layer1"))
  backbone.layer2.register_forward_hook(_hook("layer2"))
  backbone.layer3.register_forward_hook(_hook("layer3"))
  backbone.layer4.register_forward_hook(_hook("layer4"))
  with torch.no_grad():
      backbone(x)
  return x, activations, backbone


def show_feature_maps(fig_no: int = 26, fig_caption: str = "骨干网络多尺度特征图与 MSDC 分支响应"):
    """Visualize shallow/mid/deep backbone activations and MSDC branch outputs."""
    import torch
    import torch.nn.functional as F

    sys.path.insert(0, str(TRAIN_DIR))
    from modules.msdc import MSDC

    _, img_rgb = _pick_viz_sample_image()
    display_size = (img_rgb.shape[1], img_rgb.shape[0])
    _, activations, _ = _load_backbone_and_tensor(img_rgb)

    with torch.no_grad():
      msdc_out = MSDC()(activations["layer3"])

    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    titles = [
        "原图",
        "浅层特征 layer1",
        "中层特征 layer2",
        "深层特征 layer3",
        "更深层 layer4",
        "MSDC 融合输出",
    ]
    items = [
        img_rgb,
        activations["layer1"],
        activations["layer2"],
        activations["layer3"],
        activations["layer4"],
        msdc_out,
    ]
    sub_fp = cjk_font(FIG_TITLE_FONT)
    for ax, title, item in zip(axes.ravel(), titles, items):
        if isinstance(item, np.ndarray):
            ax.imshow(item)
        else:
            hm = _activation_heatmap(item, up_to=display_size)
            _overlay_heatmap(ax, Image.fromarray(img_rgb).resize(display_size, Image.BILINEAR), hm)
        if sub_fp is not None:
            ax.set_title(title, fontproperties=sub_fp)
        else:
            ax.set_title(title, fontsize=FIG_TITLE_FONT)
        ax.axis("off")

    _register_fig_caption(fig, fig_no, fig_caption)
    finalize_figure(fig)


def show_conv_kernels(fig_no: int = 27, fig_caption: str = "SGA 空间注意力卷积核与 MSDC 分支权重"):
    """Visualize SGA 7x7 conv kernels and MSDC softmax branch weights."""
    import torch

    sys.path.insert(0, str(TRAIN_DIR))
    from modules.attention import SGA
    from modules.msdc import MSDC

    sga = SGA(7)
    w = sga.conv.weight.detach().cpu().numpy()[0]  # (2, 7, 7)
    msdc = MSDC()
    branch_w = torch.softmax(msdc.w, dim=0).detach().cpu().numpy()

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    sub_fp = cjk_font(FIG_TITLE_FONT)
    kernels = [("Avg 分支卷积核", w[0]), ("Max 分支卷积核", w[1])]
    for ax, (title, k) in zip(axes[:2], kernels):
        im = ax.imshow(k, cmap="coolwarm")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        if sub_fp is not None:
            ax.set_title(title, fontproperties=sub_fp)
        else:
            ax.set_title(title, fontsize=FIG_TITLE_FONT)
        ax.set_xticks(range(7))
        ax.set_yticks(range(7))

    labels = ["AvgPool3", "AvgPool5", "MaxPool5"]
    colors = ["#3b82f6", "#22c55e", "#ef4444"]
    axes[2].bar(labels, branch_w, color=colors)
    axes[2].set_ylim(0, 1)
    axes[2].set_ylabel("Softmax 权重")
    if sub_fp is not None:
        axes[2].set_title("MSDC 多尺度分支权重", fontproperties=sub_fp)
    else:
        axes[2].set_title("MSDC 多尺度分支权重", fontsize=FIG_TITLE_FONT)

    _register_fig_caption(fig, fig_no, fig_caption)
    finalize_figure(fig)


def _cga_gate(x: "torch.Tensor", cga) -> "torch.Tensor":
  import torch
  stat = cga.pool(x)
  stat = stat / (stat.abs().mean(dim=1, keepdim=True) + 1e-6)
  return torch.sigmoid(cga.alpha * stat + cga.beta)


def _sga_map(x: "torch.Tensor", sga) -> "torch.Tensor":
  import torch
  avg = torch.mean(x, dim=1, keepdim=True)
  mx, _ = torch.max(x, dim=1, keepdim=True)
  return sga.sigmoid(sga.conv(torch.cat([avg, mx], dim=1)))


def show_attention_weights(fig_no: int = 28, fig_caption: str = "CGA 通道注意力与 SGA 空间注意力权重"):
    """Visualize CGA channel gates and SGA spatial attention overlaid on sample image."""
    import torch

    sys.path.insert(0, str(TRAIN_DIR))
    from modules.attention import CGA, SGA

    _, img_rgb = _pick_viz_sample_image()
    display_size = (img_rgb.shape[1], img_rgb.shape[0])
    _, activations, _ = _load_backbone_and_tensor(img_rgb)
    feat = activations["layer3"]
    cga, sga = CGA(), SGA(7)
    with torch.no_grad():
        gate = _cga_gate(feat, cga)[0, :, 0, 0].cpu().numpy()
        spatial = _sga_map(feat, sga)[0, 0].cpu().numpy()
    spatial = (spatial - spatial.min()) / (spatial.max() - spatial.min() + 1e-8)
    spatial_up = np.array(Image.fromarray((spatial * 255).astype(np.uint8)).resize(display_size, Image.BILINEAR)) / 255.0

    top_k = min(16, len(gate))
    top_idx = np.argsort(gate)[-top_k:][::-1]

    fig = plt.figure(figsize=(12, 5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    sub_fp = cjk_font(FIG_TITLE_FONT)

    ax0.barh([f"ch-{i}" for i in top_idx[::-1]], gate[top_idx][::-1], color="#8b5cf6")
    ax0.set_xlabel("通道门控权重")
    ax0.set_xlim(0, 1)
    if sub_fp is not None:
        ax0.set_title("CGA 通道注意力（Top-16）", fontproperties=sub_fp)
    else:
        ax0.set_title("CGA 通道注意力（Top-16）", fontsize=FIG_TITLE_FONT)

    img_show = np.array(Image.fromarray(img_rgb).resize(display_size, Image.BILINEAR))
    ax1.imshow(img_show)
    ax1.imshow(spatial_up, cmap="inferno", alpha=0.5)
    ax1.axis("off")
    if sub_fp is not None:
        ax1.set_title("SGA 空间注意力叠加原图", fontproperties=sub_fp)
    else:
        ax1.set_title("SGA 空间注意力叠加原图", fontsize=FIG_TITLE_FONT)

    _register_fig_caption(fig, fig_no, fig_caption)
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


def _resolve_notebook_dir() -> Path:
    """Directory of the active .ipynb (for Markdown image paths on GitHub/local)."""
    cwd = Path.cwd().resolve()
    root = ROOT.resolve()
    if cwd == root:
        return root
    if cwd == root.parent and (cwd / "Bridge" / "app.py").exists():
        return cwd
    if (cwd / "Bridge" / "app.py").exists() and any(cwd.glob("课程设计*.ipynb")):
        return cwd
    if (cwd / "app.py").exists():
        return cwd
    return cwd


NOTEBOOK_DIR = _resolve_notebook_dir()


def _repo_image_rel(path: Path) -> str:
    """Markdown img src relative to the notebook directory."""
    img = path.resolve()
    nb_dir = NOTEBOOK_DIR.resolve()
    try:
        return img.relative_to(nb_dir).as_posix()
    except ValueError:
        pass
    try:
        return img.relative_to(ROOT.parent.resolve()).as_posix()
    except ValueError:
        pass
    try:
        return img.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _display_repo_image(path: Path, width: int = 960) -> None:
    """Show repo images: Bridge notebook uses Markdown relative paths; root notebook embeds bytes."""
    if not path.is_file():
        raise FileNotFoundError(f"图片不存在: {path}")
    rel = _repo_image_rel(path)
    if NOTEBOOK_DIR.resolve() == ROOT.resolve():
        # Bridge/课程设计*.ipynb — GitHub resolves ![](relative/path) against the .ipynb location.
        display(Markdown(f"![{path.stem}]({rel})"))
    else:
        display(IPyImage(filename=str(path.resolve()), embed=True, width=width))


def show_principle_diagram(
    key: str,
    caption: str = "",
    fig_no: int | None = None,
    title: str = "",
    width: int = 920,
):
    path = PRINCIPLE_STATIC.get(key)
    if path is None:
        raise KeyError(f"未知图片 key: {key!r}")
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}\n请确认 {PRINCIPLE_SRC_DIR} 下文件齐全。")
    _display_repo_image(path, width=width)
    if fig_no is not None and title:
        display_figure_caption(fig_no, title)
    elif caption.strip():
        display(Markdown(center_markdown(f"**{caption.strip()}**")))


# (key, 图号, 图题, 功能介绍)
PLATFORM_PAGES = [
    (
        "platform_home",
        5,
        "平台首页",
        "系统入口与数据概览：展示近 30 日检测次数、病害总数、平均耗时与模型使用分布，"
        "并提供各功能模块快捷入口。",
    ),
    (
        "platform_detect",
        6,
        "病害检测页面",
        "核心检测功能页：支持上传桥梁表观图像，选择消融实验模型（model1~model8），"
        "输出检测框、实例掩膜及裂缝/剥落等病害的长度、宽度等工程量化参数。",
    ),
    (
        "platform_realtime",
        7,
        "实时监测页面",
        "接入摄像头或视频流进行连续推理，适用于现场动态巡检场景，"
        "可实时叠加掩膜与量化结果，并记录监测事件。",
    ),
    (
        "platform_analysis",
        8,
        "病害分析页面",
        "对累积检测数据进行多维度统计分析，包括检测趋势、模型使用占比"
        "及各类病害分布，为养护决策提供数据支撑。",
    ),
    (
        "platform_model_info",
        9,
        "模型信息页面",
        "展示 8 组消融实验模型的 Box/Mask 精度指标对比、当前模型摘要"
        "及训练曲线（mAP 与损失），便于评估各改进模块效果。",
    ),
    (
        "platform_report_gen",
        10,
        "报告生成页面",
        "根据选定检测记录自动生成结构化巡检报告，"
        "支持 Word / PDF / Markdown 预览与导出。",
    ),
    (
        "platform_auth",
        11,
        "注册登录页面",
        "用户注册与登录入口，注册后可保存检测记录到账号历史，"
        "实现多用户隔离与个性化数据管理。",
    ),
    (
        "platform_latency",
        12,
        "推理耗时统计",
        "展示平台推理耗时分布与统计指标，反映各模型在实际部署中的"
        "响应速度与稳定性，辅助模型选型。",
    ),
]


def show_all_platform_pages(width: int = 960):
    """依次展示平台各功能页面截图及文字介绍。"""
    display(Markdown(center_markdown("### 平台页面展示（截图来源：`图片/` 目录）")))
    for key, no, fig_title, intro in PLATFORM_PAGES:
        show_principle_diagram(key, width=width)
        display(Markdown(center_markdown(f"**{figure_caption(no, fig_title)}**", intro)))
        display(Markdown(center_markdown("---")))


print("项目根目录:", ROOT)
print("Notebook 目录:", NOTEBOOK_DIR)
print("DATA_DIR:", DATA_DIR, "存在:", DATA_DIR.is_dir())
print("RESULT_DIR:", RESULT_DIR)
print("图片目录:", PRINCIPLE_SRC_DIR, "存在:", PRINCIPLE_SRC_DIR.exists())
print("Python:", sys.version.split()[0])
print("操作系统:", platform.platform())
print("matplotlib 中文字体:", _CJK_FONT or "未检测到（图表中文可能显示为方框）")
platform_ok = {k: v.exists() for k, v in PRINCIPLE_STATIC.items() if k.startswith("platform_")}
print("平台截图检查:", platform_ok)
