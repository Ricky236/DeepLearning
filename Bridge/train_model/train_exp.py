from __future__ import annotations

import argparse
from pathlib import Path

from register_modules import register_ultralytics_modules

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = Path("misu_yolo") / "data_ultralytics.yaml"
EXPERIMENT_CFGS = {
    "baseline": Path("configs") / "baseline.yaml",
    "exp1": Path("configs") / "exp1_p2.yaml",
    "exp2": Path("configs") / "exp2_bifpn.yaml",
    "exp3": Path("configs") / "exp3_msdc.yaml",
    "exp4": Path("configs") / "exp4_cga.yaml",
    "exp5": Path("configs") / "exp5_sga.yaml",
    "exp6": Path("configs") / "exp6_grb.yaml",
    "exp7": Path("configs") / "exp7_full.yaml",
}


def resolve_cfg(exp: str | None, cfg: str | None) -> Path:
    if cfg:
        return Path(cfg)
    if exp is None:
        raise ValueError("必须传入 --exp 或 --cfg 其中之一。")
    key = exp.lower()
    if key not in EXPERIMENT_CFGS:
        raise ValueError(f"未知实验名: {exp}，可选值: {', '.join(EXPERIMENT_CFGS)}")
    return EXPERIMENT_CFGS[key]


def main():
    parser = argparse.ArgumentParser(description="YOLO11n-seg 消融实验训练入口")
    parser.add_argument("--exp", type=str, default=None, help="baseline / exp1 / ... / exp7")
    parser.add_argument("--cfg", type=str, default=None, help="直接指定模型 YAML，优先级高于 --exp")
    parser.add_argument("--data", type=str, default=str(DEFAULT_DATA))
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--project", type=str, default=str(Path("runs") / "ablation"))
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--lr0", type=float, default=0.001)
    parser.add_argument("--patience", type=int, default=50)
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("--amp", action="store_true")
    args = parser.parse_args()

    register_ultralytics_modules()
    cfg_path = resolve_cfg(args.exp, args.cfg)
    exp_key = args.exp.lower() if args.exp else cfg_path.stem.lower()
    run_name = args.name or exp_key

    from ultralytics import YOLO

                                         
    p2_exps = {"exp1", "exp2", "exp3", "exp4", "exp5", "exp6", "exp7"}
    mask_ratio = 2 if exp_key in p2_exps else 4

    print(f"[INFO] cfg        : {cfg_path}")
    print(f"[INFO] data       : {args.data}")
    print(f"[INFO] name       : {run_name}")
    print(f"[INFO] mask_ratio : {mask_ratio}")

    model = YOLO(str(cfg_path))
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=run_name,
        lr0=args.lr0,
        patience=args.patience,
        cache=args.cache,
        amp=args.amp,
        optimizer="AdamW",
        mask_ratio=mask_ratio,
        close_mosaic=10,
    )


if __name__ == "__main__":
    main()