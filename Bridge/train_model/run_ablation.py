from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

EXPERIMENTS = ["baseline", "exp1", "exp2", "exp3", "exp4", "exp5", "exp6", "exp7"]


def main():
    parser = argparse.ArgumentParser(description="顺序运行 YOLO11n-seg 消融实验")
    parser.add_argument("--data", type=str, default=str(Path("misu_yolo") / "data_ultralytics.yaml"))
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=20)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--start", type=str, default="baseline", help="从哪个实验开始")
    parser.add_argument("--stop", type=str, default="exp7", help="在哪个实验结束")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    start_idx = EXPERIMENTS.index(args.start.lower())
    stop_idx = EXPERIMENTS.index(args.stop.lower())
    selected = EXPERIMENTS[start_idx: stop_idx + 1]

    for exp in selected:
        cmd = [
            sys.executable,
            "train_exp.py",
            "--exp",
            exp,
            "--data",
            args.data,
            "--epochs",
            str(args.epochs),
            "--imgsz",
            str(args.imgsz),
            "--batch",
            str(args.batch),
            "--device",
            args.device,
            "--workers",
            str(args.workers),
            "--name",
            exp,
        ]
        print("[RUN]", " ".join(cmd))
        if not args.dry_run:
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
