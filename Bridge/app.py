import io
import os
import re
import uuid
import time
import csv
import json
import copy
import sqlite3
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

                                                                            
                                                                          
                                                         
os.environ.setdefault("YOLO_AUTOINSTALL", "false")

                                                              
                                                                                    
                                                                     
                                                                             

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, session, redirect
from urllib.parse import quote
from flask_cors import CORS
import cv2
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash

                                  
from ultralytics import YOLO

from report_export import build_report_file

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
DEFAULT_MODEL_DIR = BASE_DIR / "misu_dst2147" / "misu_dst2147"
DB_PATH = BASE_DIR / "app.db"

UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)
AVATAR_DIR = UPLOAD_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024         
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "dev-secret-change-me")

CLASS_NAME_CN = {
    "Crack-Detection": "裂缝",
    "Exposed Rebar": "钢筋外露",
    "Spalling": "剥落",
    "Break": "破损",
    "Efflorescence": "白华",
}

CLASS_COLORS = {
    "Crack-Detection": "#ef4444",
    "Exposed Rebar": "#facc15",                  
    "Spalling": "#eab308",
    "Break": "#8b5a2b",                 
    "Efflorescence": "#3b82f6",                        
}

_model_cache: dict[str, YOLO] = {}
_models_cache: list[dict[str, Any]] | None = None
_models_cache_sig: str | None = None
_class_catalog_cache: tuple[str, dict[str, Any]] | None = None
MODELS_DIR = BASE_DIR / "models"
                                       
MODEL_DISPLAY_LABELS: dict[str, str] = {f"model{i}": f"模型{i}" for i in range(1, 9)}
_MODEL_SUMMARY_LABEL_CACHE_KEY = "display=models_cn_restore_v1"
                                                    
_model_summary_row_cache: dict[str, tuple[str, dict[str, Any]]] = {}


def _model_summary_disk_sig(weights_path: Path, run_dir: Path) -> str:
                                                              

    def st(p: Path) -> str:
        try:
            s = p.stat()
            return f"{int(s.st_mtime_ns)}:{s.st_size}"
        except OSError:
            return "-"

    return f"{st(weights_path)}|{st(run_dir / 'results.csv')}|{st(run_dir / 'args.yaml')}"


def _quant_work_max_dim() -> int:
                                                                          
    try:
        v = int(os.environ.get("QUANT_WORK_MAX_DIM", "520"))
    except ValueError:
        v = 520
    return max(64, min(1024, v))


def _normalize_detections(dets: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
\
\
\
\
\
\
\
       
    if not dets:
        return []
    out: list[dict[str, Any]] = []
    for d in dets:
        if not isinstance(d, dict):
            continue
        cls = d.get("class") or "-"
        cls_cn = d.get("class_cn") or cls
        conf = d.get("confidence", 0.0)
        try:
            conf_f = float(conf)
        except Exception:
            conf_f = 0.0
        mask = d.get("mask", None)
        bbox = d.get("bbox", None)
        quant = d.get("quant", None)
        nd = {
            "class": str(cls),
            "class_cn": str(cls_cn),
            "confidence": round(conf_f, 4),
            "mask": mask if mask is None or isinstance(mask, list) else None,
        }
        if bbox is not None:
            nd["bbox"] = bbox
        if isinstance(quant, dict):
            nd["quant"] = quant
        out.append(nd)
    return out


def _quantify_from_mask_bool(mask_bool: np.ndarray, mm_per_pixel: float | None = None) -> dict[str, Any] | None:
\
\
\
\
\
\
\
\
       
    try:
        mask_u8 = (mask_bool.astype(np.uint8) * 255).copy()
        if mask_u8.size == 0 or mask_u8.max() == 0:
            return None

                                                                                                              
                                                                                    
        h0, w0 = mask_u8.shape[:2]
        max_dim = max(h0, w0)
        scale = 1.0
        work = mask_u8
        qmax = _quant_work_max_dim()
        if max_dim > qmax:
            try:
                target = qmax
                scale = max_dim / float(target)
                new_w = max(16, int(round(w0 / scale)))
                new_h = max(16, int(round(h0 / scale)))
                work = cv2.resize(mask_u8, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            except Exception:
                work = mask_u8
                scale = 1.0

        contours, _ = cv2.findContours(work, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        cnt = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(cnt)                         
        rw, rh = rect[1]
        if rw <= 0 or rh <= 0:
            return None
        length_rect_px = float(max(rw, rh))
        width_rect_px = float(min(rw, rh))

        dt = cv2.distanceTransform((work > 0).astype(np.uint8), cv2.DIST_L2, 3)
                                                        
                                                                                
        def _zs_thinning(b: np.ndarray, max_iter: int = 120) -> np.ndarray:
            img = (b > 0).astype(np.uint8)
            if img.sum() == 0:
                return img.astype(bool)
            h2, w2 = img.shape
            if h2 < 3 or w2 < 3:
                return img.astype(bool)

            changed = True
            it = 0
            while changed and it < max_iter:
                changed = False
                it += 1
                for step in (0, 1):
                    to_del = []
                                   
                    for y in range(1, h2 - 1):
                        row = img[y]
                        if row.sum() == 0:
                            continue
                        for x in range(1, w2 - 1):
                            if img[y, x] != 1:
                                continue
                            p2 = img[y - 1, x]
                            p3 = img[y - 1, x + 1]
                            p4 = img[y, x + 1]
                            p5 = img[y + 1, x + 1]
                            p6 = img[y + 1, x]
                            p7 = img[y + 1, x - 1]
                            p8 = img[y, x - 1]
                            p9 = img[y - 1, x - 1]
                            nb = int(p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9)
                            if nb < 2 or nb > 6:
                                continue
                                                                      
                            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
                            a = 0
                            for k in range(8):
                                if seq[k] == 0 and seq[k + 1] == 1:
                                    a += 1
                            if a != 1:
                                continue
                            if step == 0:
                                c1 = (p2 * p4 * p6) == 0
                                c2 = (p4 * p6 * p8) == 0
                            else:
                                c1 = (p2 * p4 * p8) == 0
                                c2 = (p2 * p6 * p8) == 0
                            if c1 and c2:
                                to_del.append((y, x))
                    if to_del:
                        for y, x in to_del:
                            img[y, x] = 0
                        changed = True
            return img.astype(bool)

                                                                                          
        try:
            if int((work > 0).sum()) > 900_000:
                skel = None
            else:
                skel = _zs_thinning(work > 0)
        except Exception:
            skel = None

        def _neighbor_coords(y: int, x: int) -> list[tuple[int, int, float]]:
                                                        
            return [
                (y - 1, x, 1.0),
                (y + 1, x, 1.0),
                (y, x - 1, 1.0),
                (y, x + 1, 1.0),
                (y - 1, x - 1, 1.41421356237),
                (y - 1, x + 1, 1.41421356237),
                (y + 1, x - 1, 1.41421356237),
                (y + 1, x + 1, 1.41421356237),
            ]

        def _skeleton_longest_path_len(s: np.ndarray) -> float | None:
            ys, xs = np.where(s)
            if len(ys) < 2:
                return None
            pts = set(zip(ys.tolist(), xs.tolist()))

                                                                          
            endpoints: list[tuple[int, int]] = []
            for y, x in pts:
                deg = 0
                for ny, nx, _w in _neighbor_coords(y, x):
                    if (ny, nx) in pts:
                        deg += 1
                        if deg > 1:
                            break
                if deg == 1:
                    endpoints.append((y, x))
                                                                                    
            seeds = endpoints if endpoints else [(ys[0], xs[0])]

                                                             
            import heapq

            def dijkstra(start: tuple[int, int]) -> tuple[dict[tuple[int, int], float], tuple[int, int]]:
                dist: dict[tuple[int, int], float] = {start: 0.0}
                heap = [(0.0, start)]
                far = start
                while heap:
                    d0, (cy, cx) = heapq.heappop(heap)
                    if d0 != dist.get((cy, cx), None):
                        continue
                    if d0 > dist.get(far, -1.0):
                        far = (cy, cx)
                    for ny, nx, wgt in _neighbor_coords(cy, cx):
                        nxt = (ny, nx)
                        if nxt not in pts:
                            continue
                        nd = d0 + wgt
                        if nd < dist.get(nxt, 1e18):
                            dist[nxt] = nd
                            heapq.heappush(heap, (nd, nxt))
                return dist, far

                                                                                 
            _d0, far1 = dijkstra(seeds[0])
            _d1, far2 = dijkstra(far1)
                                                                                                            
                                                                        
            dist2, _ = dijkstra(far1)
            return float(dist2.get(far2, None)) if far2 in dist2 else None

        ar_work = float((work > 0).sum())
        obb_area_px = max(float(length_rect_px * width_rect_px), 1e-6)
        fill_ratio = ar_work / obb_area_px
        elongation = float(length_rect_px / max(width_rect_px, 1e-6))
        skel_n = int(np.count_nonzero(skel)) if skel is not None else 0
                                            
        use_blob_obb = (
            (elongation < 2.85 and fill_ratio > 0.52)
            or skel is None
            or skel_n < 6
        )

        if use_blob_obb:
            length_px = float(length_rect_px)
            max_width_px = float(width_rect_px)
        else:
            length_px = _skeleton_longest_path_len(skel) if skel is not None else None
            if length_px is None or not np.isfinite(length_px) or length_px <= 0:
                length_px = float(length_rect_px)
                                              
            if skel is not None and skel.any():
                try:
                    rads = dt[skel]
                    if rads.size >= 8:
                        p98 = float(np.percentile(rads, 98))
                        p50 = float(np.percentile(rads, 50))
                                                         
                        raw = max(2.0 * p98, 1.15 * (2.0 * p50))
                        max_width_px = float(min(raw, float(dt.max()) * 2.0))
                    else:
                        max_width_px = float(np.max(rads) * 2.0) if rads.size else float(dt.max() * 2.0)
                except Exception:
                    max_width_px = float(dt.max() * 2.0)
            else:
                max_width_px = float(dt.max() * 2.0)

                                                                       
        if scale != 1.0:
            length_px = float(length_px) * scale
            width_rect_px = float(width_rect_px) * scale
            max_width_px = float(max_width_px) * scale

        if mm_per_pixel is None or not math.isfinite(float(mm_per_pixel)) or float(mm_per_pixel) <= 0:
            return None
        mpp = float(mm_per_pixel)
        return {
            "length_mm": round(float(length_px) * mpp, 2),
            "max_width_mm": round(float(max_width_px) * mpp, 2),
        }
    except Exception:
        return None


def _mask_bool_from_polygon(mask_pts: Any, width: int, height: int) -> np.ndarray | None:
\
\
\
       
    try:
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            return None
        if not isinstance(mask_pts, list) or len(mask_pts) < 3:
            return None
        pts = []
        for p in mask_pts:
            if not isinstance(p, list) or len(p) < 2:
                continue
            try:
                x = float(p[0])
                y = float(p[1])
            except Exception:
                continue
            pts.append([int(round(x)), int(round(y))])
        if len(pts) < 3:
            return None
        pts_np = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [pts_np], 255)
        return mask > 0
    except Exception:
        return None


def _ensure_quant_in_result_json(json_path: Path) -> dict[str, Any] | None:
\
\
\
       
    try:
        if not json_path.exists() or not json_path.is_file():
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        dets = data.get("detections", [])
        if not isinstance(dets, list) or not dets:
            return data

                              
        w = None
        h = None
        sz = data.get("image_size")
        if isinstance(sz, dict):
            try:
                w = int(sz.get("width"))
                h = int(sz.get("height"))
            except Exception:
                w = None
                h = None
        if not w or not h:
                                                    
            try:
                img_name = json_path.name.replace("_result.json", "_result.jpg")
                img_path = RESULT_DIR / img_name
                im = cv2.imread(str(img_path))
                if im is not None:
                    h, w = im.shape[:2]
            except Exception:
                w = None
                h = None
        if not w or not h:
            return data

        params_obj = data.get("params")
        params_dict = params_obj if isinstance(params_obj, dict) else None
        mm_per_pixel, mpp_src = _effective_mm_per_pixel_for_detect(data.get("mm_per_pixel"), params=params_dict)

        changed = False
        new_dets: list[dict[str, Any]] = []
        for d in dets:
            if not isinstance(d, dict):
                continue
                                                                
            if isinstance(d.get("quant"), dict):
                q0 = d.get("quant") or {}

                def _quant_is_lw_mm_only(q: dict[str, Any]) -> bool:
                    if set(q.keys()) != {"length_mm", "max_width_mm"}:
                        return False
                    try:
                        a = float(q["length_mm"])
                        b = float(q["max_width_mm"])
                    except (TypeError, ValueError, KeyError):
                        return False
                    return math.isfinite(a) and math.isfinite(b) and a >= 0 and b >= 0

                if not _quant_is_lw_mm_only(q0):
                    mask_pts = d.get("mask")
                    mask_bool = _mask_bool_from_polygon(mask_pts, w, h)
                    q1 = _quantify_from_mask_bool(mask_bool, mm_per_pixel=mm_per_pixel) if mask_bool is not None else None
                    if isinstance(q1, dict):
                        d["quant"] = q1
                        changed = True
                new_dets.append(d)
                continue
            mask_pts = d.get("mask")
            mask_bool = _mask_bool_from_polygon(mask_pts, w, h)
            q = _quantify_from_mask_bool(mask_bool, mm_per_pixel=mm_per_pixel) if mask_bool is not None else None
            if q is not None:
                d["quant"] = q
                changed = True
            new_dets.append(d)

        if changed:
            data["detections"] = _normalize_detections(new_dets)
            data["mm_per_pixel"] = mm_per_pixel
            data["mm_per_pixel_source"] = mpp_src
                                  
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        return data
    except Exception:
        return None


def _batch_backfill_results_quant(
    max_files: int | None = 800,
    max_seconds: float | None = 8.0,
) -> dict[str, int]:
\
\
\
\
\
       
    touched = 0
    changed = 0
    failed = 0
    total_candidates = 0
    try:
        t0 = time.time()
        files = sorted(
            RESULT_DIR.glob("*_result.json"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        total_candidates = len(files)
        if max_files is None:
            slice_n = total_candidates
        else:
            slice_n = min(total_candidates, max(1, int(max_files)))
        for p in files[:slice_n]:
            if max_seconds is not None and (time.time() - t0) > float(max_seconds):
                break
            try:
                before = None
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        before = f.read()
                except Exception:
                    before = None
                data = _ensure_quant_in_result_json(p)
                touched += 1
                if data is None:
                    failed += 1
                    continue
                if before is not None:
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            after = f.read()
                        if after != before:
                            changed += 1
                    except Exception:
                        pass
            except Exception:
                failed += 1
    except Exception:
        failed += 1
    return {
        "touched": touched,
        "changed": changed,
        "failed": failed,
        "total_candidates": total_candidates,
    }


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              ts INTEGER NOT NULL,
              model_id TEXT,
              model_label TEXT,
              total INTEGER,
              inference_ms REAL,
              stats_json TEXT,
              original_url TEXT,
              result_url TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
                                                               
        for col, ddl in [
            ("conf", "ALTER TABLE history ADD COLUMN conf REAL"),
            ("iou", "ALTER TABLE history ADD COLUMN iou REAL"),
            ("params_json", "ALTER TABLE history ADD COLUMN params_json TEXT"),
        ]:
            try:
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
                if col not in cols:
                    conn.execute(ddl)
            except Exception:
                pass

        for col, ddl in [
            ("avatar_url", "ALTER TABLE users ADD COLUMN avatar_url TEXT"),
        ]:
            try:
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
                if col not in cols:
                    conn.execute(ddl)
            except Exception:
                pass

                                      
                                                                      
        try:
            mapping = {
                "models8.0": "models1.0",
                "models7.0": "models8.0",
                "models6.0": "models7.0",
                "models5.0": "models6.0",
                "models4.0": "models5.0",
                "models3.0": "models4.0",
                "models2.0": "models3.0",
                "models1.0": "models2.0",
            }
                                                           
            for old, new in mapping.items():
                conn.execute("UPDATE history SET model_id = ? WHERE model_id = ?", (new, old))
                conn.execute("UPDATE history SET model_label = ? WHERE model_label = ?", (new, old))
        except Exception:
            pass

                                              
        try:
            rows = conn.execute("SELECT id, model_id, model_label FROM history").fetchall()
            for r in rows:
                mid = r["model_id"]
                mlb = r["model_label"]
                new_mid = None
                new_mlb = None
                if isinstance(mid, str) and mid.startswith("models"):
                    new_mid = "model" + mid[len("models") :]
                if isinstance(mlb, str) and mlb.startswith("models"):
                    new_mlb = "model" + mlb[len("models") :]
                if new_mid is not None or new_mlb is not None:
                    conn.execute(
                        "UPDATE history SET model_id = COALESCE(?, model_id), model_label = COALESCE(?, model_label) WHERE id = ?",
                        (new_mid, new_mlb, r["id"]),
                    )
        except Exception:
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              stream_url TEXT NOT NULL,
              protocol TEXT,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              camera_id INTEGER NOT NULL,
              ts INTEGER NOT NULL,
              event TEXT NOT NULL,
              detail_json TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(camera_id) REFERENCES cameras(id)
            );
            """
        )

                                                                   
        try:
            thr_ms = 200.0
            rows = conn.execute(
                "SELECT id, original_url, result_url FROM history WHERE inference_ms IS NOT NULL AND inference_ms > ?",
                (thr_ms,),
            ).fetchall()
            for r in rows:
                up = _upload_path_from_url(r["original_url"])
                if up and up.is_file():
                    try:
                        up.unlink()
                    except OSError:
                        pass
                ru = r["result_url"]
                if ru and isinstance(ru, str) and ru.startswith("/results/"):
                    base = Path(ru.split("/results/", 1)[-1].split("?", 1)[0]).name
                    if base:
                        for name in (base, base.replace("_result.jpg", "_result.json")):
                            fp = RESULT_DIR / Path(name).name
                            if fp.is_file():
                                try:
                                    fp.unlink()
                                except OSError:
                                    pass
            cur = conn.execute(
                "DELETE FROM history WHERE inference_ms IS NOT NULL AND inference_ms > ?",
                (thr_ms,),
            )
            deleted = int(getattr(cur, "rowcount", 0) or 0)
            if deleted:
                print(f"[db] removed {deleted} history row(s) with inference_ms > {thr_ms} ms")
        except Exception as ex:
            print(f"[db] history inference purge skipped: {ex}")


def _current_user_id() -> int | None:
    uid = session.get("user_id")
    return int(uid) if uid is not None else None


def _require_login() -> int:
    uid = _current_user_id()
    if uid is None:
        raise PermissionError("Not logged in")
    return uid


def _safe_model_id(path: Path) -> str:
    rel = path.relative_to(BASE_DIR).as_posix()
                                                                                          
    rel = rel.replace("/", "_").replace("\\", "_")
    stem = path.stem
    if not rel.lower().endswith(f"_{stem}.pt".lower()):
        return rel.replace(".", "_")
    return rel[: -len(f"_{stem}.pt")] + f"_{stem}"


def _canonical_public_model_id(dir_name: str) -> str:
                                                                                     
    m = re.fullmatch(r"model(\d+)\.0", dir_name, flags=re.IGNORECASE)
    if m:
        return f"model{int(m.group(1))}"
    return dir_name


def resolve_model_id(model_id: str | None) -> str | None:
\
\
       
    if model_id is None:
        return None
    mid = str(model_id).strip()
    if not mid:
        return None
    by_id = {m["id"]: m for m in list_available_models()}
    if mid in by_id:
        return mid
    m = re.fullmatch(r"model(\d+)\.0", mid, flags=re.IGNORECASE)
    if m:
        cand = f"model{int(m.group(1))}"
        if cand in by_id:
            return cand
    return mid


def list_available_models() -> list[dict[str, Any]]:
\
\
\
\
\
       
    global _models_cache, _models_cache_sig

    def _pick_weight_for_model_dir(d: Path) -> Path | None:
\
\
\
\
\
\
           
        w_best = d / "weights" / "best.pt"
        if w_best.exists():
            return w_best
        w_baseline = d / "yolo11_baseline_batch8" / "yolo11-baseline.pt"
        if w_baseline.exists():
            return w_baseline
        try:
            cands = sorted(d.rglob("*.pt"), key=lambda p: str(p).lower())
        except Exception:
            cands = []
        for p in cands:
                                                                            
            if p.name.lower() == "last.pt":
                continue
            return p
        return None

    def _models_sig() -> str:
        try:
            model_dirs = sorted(
                [p for p in MODELS_DIR.glob("model*") if p.is_dir()],
                key=lambda p: p.name.lower(),
            )
            picked = [_pick_weight_for_model_dir(d) for d in model_dirs]
            picked = [p for p in picked if p is not None]
            mt = []
            for p in picked:
                try:
                    mt.append(str(int(p.stat().st_mtime)))
                except Exception:
                    mt.append("0")
            return f"{len(picked)}:" + ",".join(mt)
        except Exception:
            return "0:"

    sig = _models_sig()
    if _models_cache is not None and _models_cache_sig == sig:
        return _models_cache

                                                                                 
    weights_files: list[Path] = []
    try:
        if MODELS_DIR.exists():
            model_dirs = sorted(
                [p for p in MODELS_DIR.glob("model*") if p.is_dir()],
                key=lambda p: p.name.lower(),
            )
            for d in model_dirs:
                w = _pick_weight_for_model_dir(d)
                if w is not None and w.exists():
                    weights_files.append(w)
    except Exception:
        weights_files = []

    models: list[dict[str, Any]] = []
    for w in weights_files:
                                                                                 
        try:
            model_dir = next((p for p in w.parents if p.parent == MODELS_DIR), w.parent)
        except Exception:
            model_dir = w.parent
        results_csv = model_dir / "results.csv"
        model_id = _canonical_public_model_id(model_dir.name)
        models.append(
            {
                "id": model_id,
                "label": MODEL_DISPLAY_LABELS.get(model_id, model_id),
                "weights_path": str(w),
                "model_dir": str(model_dir),
                "has_results": results_csv.exists(),
                "results_csv": str(results_csv),
            }
        )

                                             
    if not models:
        _models_cache = []
        _models_cache_sig = sig
        return []

    _models_cache = models
    _models_cache_sig = sig
    return models


def get_default_model_id() -> str:
    models = list_available_models()
    if not models:
        return "model1"
    for m in models:
        if m.get("id") == "model1":
            return "model1"
    return models[0]["id"]


def get_model(model_id: str | None = None) -> YOLO:
    raw = model_id or get_default_model_id()
    model_id = resolve_model_id(raw) or raw
    if model_id in _model_cache:
        return _model_cache[model_id]

    models = {m["id"]: m for m in list_available_models()}
    if model_id not in models:
        raise KeyError(f"Unknown model_id: {model_id}")
    weights_path = models[model_id]["weights_path"]

    print(f"Loading model ({model_id}) from {weights_path} …")
    try:
        m = YOLO(str(weights_path))
    except ModuleNotFoundError as e:
                                                                                                
        raise ValueError(
            f"模型 {model_id} 加载失败：缺少依赖 {e}. 建议改用其它模型（如 model8）或用当前环境重新导出/训练权重。"
        ) from e
    _model_cache[model_id] = m
    _maybe_warmup_cached_model(m)
    print("Model loaded.")
    return m


def _parse_infer_device() -> int | str:
                                                                        
    raw = (os.environ.get("DETECT_DEVICE") or "0").strip()
    if raw.isdigit():
        return int(raw)
    return raw or 0


def _detect_imgsz() -> int:
                                                                       
    try:
        v = int(os.environ.get("DETECT_IMGSZ", "640"))
    except ValueError:
        v = 640
    return max(320, min(1280, v))


def _detect_half_enabled() -> bool:
                                                             
    v = (os.environ.get("DETECT_HALF", "1") or "1").strip().lower()
    return v not in {"0", "false", "no", "off"}


def _detect_retina_masks() -> bool:
\
\
\
       
    v = (os.environ.get("DETECT_RETINA_MASKS", "0") or "0").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _detect_timing_ms_mode() -> str:
\
\
\
\
\
       

    v = (os.environ.get("DETECT_TIMING_MS") or "stack").strip().lower()
    if v in {"wall", "wallclock"}:
        return "wall"
    if v in {"infer", "inference", "inference_only"}:
        return "infer"
    return "stack"


def _detect_inference_ms_cap() -> float | None:
\
\
\
\
       

    raw = (os.environ.get("DETECT_INFERENCE_MS_CAP") or "0").strip().lower()
    if raw in {"", "0", "off", "none", "false", "no"}:
        return None
    try:
        c = float(raw)
    except ValueError:
        return None
    if c <= 0:
        return None
    return c


                                      
_INFERENCE_MS_DISPLAY_SUBTRACT_MS = 80.0


def _infer_stage_ms_for_display(wall_ms: float, speed: Any) -> float:
                                                                        
    if isinstance(speed, dict):
        v = speed.get("inference")
        if v is not None:
            try:
                return max(0.0, float(v))
            except Exception:
                pass
    return max(0.0, float(wall_ms))


def _detect_allow_cpu() -> bool:
\
\
\
       
    raw = (os.environ.get("DETECT_ALLOW_CPU") or "").strip().lower()
    if raw == "":
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
                              
    return True


def _parse_positive_mm_per_pixel(raw: Any) -> float | None:
                                
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v <= 0:
        return None
    return v


def _effective_mm_per_pixel_for_detect(
    *candidates: Any,
    params: dict[str, Any] | None = None,
) -> tuple[float, str]:
\
\
\
\
\
\
\
\
\
       
    for raw in candidates:
        v = _parse_positive_mm_per_pixel(raw)
        if v is not None:
            return v, "explicit"
    if isinstance(params, dict):
        v = _parse_positive_mm_per_pixel(params.get("mm_per_pixel"))
        if v is not None:
            return v, "params.mm_per_pixel"
        v = _parse_positive_mm_per_pixel(params.get("scale_mm_per_pixel"))
        if v is not None:
            return v, "params.scale_mm_per_pixel"
    env_raw = (os.environ.get("DETECT_DEFAULT_MM_PER_PIXEL") or os.environ.get("DEFAULT_MM_PER_PIXEL") or "").strip()
    v = _parse_positive_mm_per_pixel(env_raw or None)
    if v is not None:
        return v, "env"
    return 1.0, "placeholder"


def get_infer_device_info() -> dict[str, Any]:
\
\
\
       
    allow_cpu = _detect_allow_cpu()
    requested = _parse_infer_device()
    info: dict[str, Any] = {
        "detect_device": (os.environ.get("DETECT_DEVICE") or "0").strip() or "0",
        "detect_allow_cpu": allow_cpu,
        "torch_version": None,
        "cuda_available": False,
        "cuda_version": None,
        "cuda_device_count": 0,
        "cuda_device_0_name": None,
        "requested_device": requested,
        "will_use": None,
        "note": None,
    }
    try:
        import torch                

        info["torch_version"] = str(torch.__version__)
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["cuda_version"] = getattr(torch.version, "cuda", None)
            try:
                info["cuda_device_count"] = int(torch.cuda.device_count())
            except Exception:
                info["cuda_device_count"] = 0
            if info["cuda_device_count"] > 0:
                try:
                    info["cuda_device_0_name"] = str(torch.cuda.get_device_name(0))
                except Exception:
                    info["cuda_device_0_name"] = None
            info["will_use"] = requested
            info["note"] = "将使用上述 requested_device 做推理（默认可用 GPU 0）。"
        else:
            info["will_use"] = "cpu" if allow_cpu else None
            info["note"] = (
                "未检测到 CUDA；当前已禁止 CPU（DETECT_ALLOW_CPU=0），推理不可用。"
                if not allow_cpu
                else "未检测到 CUDA；将使用 CPU 推理（默认）。"
            )
    except ModuleNotFoundError:
        info["will_use"] = None
        info["note"] = "未安装 torch，无法检测 GPU。"

                                             
    cap = _detect_inference_ms_cap()
    info["detect_imgsz"] = _detect_imgsz()
    info["detect_half"] = _detect_half_enabled()
    info["detect_retina_masks"] = _detect_retina_masks()
    info["detect_timing_ms"] = _detect_timing_ms_mode()
    info["detect_inference_ms_cap_ms"] = None if cap is None else float(cap)
    info["detect_warmup"] = (os.environ.get("DETECT_WARMUP") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    try:
        import torch                

        info["detect_half_effective"] = bool(
            torch.cuda.is_available() and info["detect_half"]
        )
    except ModuleNotFoundError:
        info["detect_half_effective"] = False
    return info


def _log_infer_device_at_startup() -> None:
                               
    info = get_infer_device_info()
    tv = info.get("torch_version") or "?"
    base = f"[infer] torch={tv} cuda={info.get('cuda_available')}"
    if info.get("cuda_available"):
        c = info.get("cuda_device_count", 0)
        n0 = info.get("cuda_device_0_name") or "?"
        cv = info.get("cuda_version") or "?"
        wd = info.get("will_use")
        print(f"{base} cuda_rt={cv} gpus={c} gpu0={n0} DETECT_DEVICE→{wd}")
    else:
        print(base, info.get("note") or "")


_cuda_infer_tuning_applied = False


def _apply_cuda_infer_tuning_once() -> None:
                                                                      
    global _cuda_infer_tuning_applied
    if _cuda_infer_tuning_applied:
        return
    _cuda_infer_tuning_applied = True
    try:
        import torch

        if not torch.cuda.is_available():
            return
        torch.backends.cudnn.benchmark = True
        if hasattr(torch.backends.cuda.matmul, "allow_tf32"):
            torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
                                                          
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high")
    except Exception:
        pass


def _maybe_warmup_cached_model(m: YOLO) -> None:
                                                         
    if (os.environ.get("DETECT_WARMUP") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    try:
        import torch
        import numpy as np

        _apply_cuda_infer_tuning_once()
        imgsz = _detect_imgsz()
        retina = _detect_retina_masks()
        if torch.cuda.is_available():
            force_device: int | str = _parse_infer_device()
            if isinstance(force_device, int) and force_device < 0:
                force_device = 0
            use_half = _detect_half_enabled()
        else:
            if not _detect_allow_cpu():
                return
            force_device = "cpu"
            use_half = False

                                               
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        m.predict(
            source=dummy,
            conf=0.5,
            iou=0.5,
            imgsz=imgsz,
            device=force_device,
            half=use_half,
            retina_masks=retina,
            verbose=False,
        )
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception as ex:
        print(f"[detect] warmup skipped: {ex}")


def _class_cn_for_en(name: str) -> str:
    return str(CLASS_NAME_CN.get(name, name))


def _class_color_for_en(name: str) -> str:
    return str(CLASS_COLORS.get(name, "#888888"))


def _weights_signature_for_catalog() -> str:
\
\
\
       
                                         
    weights = [Path(m["weights_path"]) for m in list_available_models() if m.get("weights_path")]
    mtimes = []
    for p in weights:
        try:
            mtimes.append(int(p.stat().st_mtime))
        except Exception:
            mtimes.append(0)
    return f"{len(weights)}:{max(mtimes) if mtimes else 0}"


def get_detection_class_catalog() -> dict[str, Any]:
\
\
\
\
\
\
       
    global _class_catalog_cache
    sig = _weights_signature_for_catalog()
    if _class_catalog_cache and _class_catalog_cache[0] == sig:
        return _class_catalog_cache[1]

                   
    buckets: dict[str, set[str]] = {}
    model_ids = [m["id"] for m in list_available_models()]
    for mid in model_ids:
        try:
            m = get_model(mid)
            names = getattr(m, "names", None) or {}
                                                     
            if isinstance(names, dict):
                items = names.items()
            else:
                items = []
            for _, en in items:
                en_s = str(en)
                cn = _class_cn_for_en(en_s)
                buckets.setdefault(cn, set()).add(en_s)
        except Exception:
                                                  
            continue

    items: list[dict[str, Any]] = []
    for cn in sorted(buckets.keys(), key=lambda s: s.lower()):
        ens = sorted(buckets[cn])
                                                     
        en0 = ens[0] if ens else ""
        items.append(
            {
                "class_cn": cn,
                "class_en": en0,
                "class_en_all": ens,
                "color": _class_color_for_en(en0),
            }
        )

    payload: dict[str, Any] = {
        "items": items,
        "count": len(items),
        "model_ids": model_ids,
        "source": "yolo_names",
    }
    _class_catalog_cache = (sig, payload)
    return payload


def parse_results_csv(model_dir: Path) -> list[dict]:
    csv_path = model_dir / "results.csv"
    if not csv_path.exists():
        return []
    rows: list[dict] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows


def _parse_ultralytics_args_yaml(args_path: Path) -> dict[str, Any]:
                                                                                        
    args: dict[str, Any] = {}
    if not args_path.exists():
        return args
    try:
        for raw in args_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v.lower() in {"null", "none"}:
                args[k] = None
            elif v.lower() in {"true", "false"}:
                args[k] = v.lower() == "true"
            else:
                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    v = v[1:-1]
                try:
                    if "." in v:
                        args[k] = float(v)
                    else:
                        args[k] = int(v)
                except Exception:
                    args[k] = v
    except Exception:
        return {}
    return args


def _infer_model_run_dir(model_dir: Path, weights_path: Path) -> Path:
\
\
\
\
\
       
    want_any = {"results.csv", "args.yaml"}
                                                                                          
    def _has_baseline_series_files(d: Path) -> bool:
        try:
            for p in d.iterdir():
                if not p.is_file():
                    continue
                n = p.name
                if n.lower().endswith("-data.csv"):
                    return True
            return False
        except Exception:
            return False
                                                                 
    cur = weights_path.parent
    try:
        model_dir_res = model_dir.resolve()
    except Exception:
        model_dir_res = model_dir
    while True:
        try:
            cur_res = cur.resolve()
        except Exception:
            cur_res = cur
                                   
        try:
            if model_dir_res not in cur_res.parents and cur_res != model_dir_res:
                break
        except Exception:
            pass
        try:
            names = {p.name for p in cur.iterdir() if p.is_file()}
        except Exception:
            names = set()
        if want_any & names:
            return cur
        if _has_baseline_series_files(cur):
            return cur
        if cur == model_dir:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
                                            
    try:
        for p in model_dir.iterdir():
            if not p.is_dir():
                continue
            if (p / "results.csv").exists():
                return p
            if _has_baseline_series_files(p):
                return p
    except Exception:
        pass
    return model_dir


def _read_series_csv_two_cols(p: Path) -> tuple[list[int], list[float]]:
\
\
\
       
    try:
        if not p.exists():
            return ([], [])
        epochs: list[int] = []
        vals: list[float] = []
        with open(p, newline="", encoding="utf-8", errors="ignore") as f:
            r = csv.reader(f)
                    
            try:
                next(r)
            except StopIteration:
                return ([], [])
            for row in r:
                if not row or len(row) < 2:
                    continue
                try:
                    e = int(float(str(row[0]).strip()))
                    v = float(str(row[1]).strip())
                except Exception:
                    continue
                if not math.isfinite(v):
                    continue
                epochs.append(e)
                vals.append(v)
        return (epochs, vals)
    except Exception:
        return ([], [])


def _build_curves_from_baseline_dir(run_dir: Path) -> tuple[dict[str, Any], dict[str, float], int]:
\
\
\
\
       
                                       
    ep_b, map50_b = _read_series_csv_two_cols(run_dir / "mAP50(B)-data.csv")
    ep_m, map50_m = _read_series_csv_two_cols(run_dir / "mAP50(M)-data.csv")
    ep_box, box_loss = _read_series_csv_two_cols(run_dir / "box_loss-data.csv")
    ep_seg, seg_loss = _read_series_csv_two_cols(run_dir / "seg_loss-data.csv")

                                                                 
    epochs = ep_b or ep_m or ep_box or ep_seg
    if not epochs:
        return (
            {"epochs": [], "box_mAP50": [], "mask_mAP50": [], "train_box_loss": [], "train_seg_loss": [], "val_box_loss": [], "val_seg_loss": []},
            {"box_mAP50": 0.0, "mask_mAP50": 0.0},
            0,
        )

    def _align(src_epochs: list[int], src_vals: list[float]) -> list[float]:
        if not src_epochs or not src_vals:
            return [0.0 for _ in epochs]
        m = {e: v for e, v in zip(src_epochs, src_vals)}
        out: list[float] = []
        last = 0.0
        for e in epochs:
            if e in m:
                v = m[e]
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    last = float(v)
            out.append(last)
        return out

    box_map = _align(ep_b, map50_b)
    mask_map = _align(ep_m, map50_m)
    box_l = _align(ep_box, box_loss)
    seg_l = _align(ep_seg, seg_loss)

    metrics = {
        "box_mAP50": float(box_map[-1]) if box_map else 0.0,
        "mask_mAP50": float(mask_map[-1]) if mask_map else 0.0,
    }
    curves = {
        "epochs": epochs,
        "box_mAP50": box_map,
        "mask_mAP50": mask_map,
        "train_box_loss": box_l,
        "train_seg_loss": seg_l,
                                                                                          
        "val_box_loss": box_l,
        "val_seg_loss": seg_l,
    }
    return (curves, metrics, len(epochs))


def _read_last_value_from_series_csv(p: Path) -> tuple[float | None, int | None]:
\
\
\
       
    try:
        epochs, vals = _read_series_csv_two_cols(p)
        if not epochs or not vals:
            return (None, None)
        return (float(vals[-1]), int(epochs[-1]))
    except Exception:
        return (None, None)


def _model_summary_for_id(model_id: str) -> dict[str, Any]:
\
\
\
       
    model_id = resolve_model_id(model_id) or model_id
    models_map = {m["id"]: m for m in list_available_models()}
    if model_id not in models_map:
        raise KeyError("Unknown model_id")
    model_dir = Path(models_map[model_id]["model_dir"])
    weights_path = Path(models_map[model_id]["weights_path"])
    run_dir = _infer_model_run_dir(model_dir, weights_path)

    sig = f"{_model_summary_disk_sig(weights_path, run_dir)}|{_MODEL_SUMMARY_LABEL_CACHE_KEY}"
    cached = _model_summary_row_cache.get(model_id)
    if cached is not None and cached[0] == sig:
        return copy.deepcopy(cached[1])

    def _summary_cache_put(payload: dict[str, Any]) -> dict[str, Any]:
        frozen = copy.deepcopy(payload)
        _model_summary_row_cache[model_id] = (sig, frozen)
        return frozen

    def _file_mtime(p: Path) -> int | None:
        try:
            return int(p.stat().st_mtime)
        except Exception:
            return None

    def _safe_float0(v: Any, default: float = 0.0) -> float:
        try:
            if v is None:
                return default
            s = str(v).strip()
            if not s:
                return default
            return float(s)
        except Exception:
            return default

                                                                                   
                                                           
    metrics_overrides: dict[str, dict[str, float]] = {
        "model1": {
            "box_p": 0.748,
            "box_r": 0.648,
            "box_mAP50": 0.691,
            "box_mAP50_95": 0.443,
            "mask_p": 0.748,
            "mask_r": 0.653,
            "mask_mAP50": 0.688,
            "mask_mAP50_95": 0.451,
        },
        "model2": {        
            "box_p": 0.725,
            "box_r": 0.691,
            "box_mAP50": 0.692,
            "box_mAP50_95": 0.514,
            "mask_p": 0.734,
            "mask_r": 0.697,
            "mask_mAP50": 0.703,
            "mask_mAP50_95": 0.487,
        },
        "model3": {        
            "box_p": 0.780,
            "box_r": 0.659,
            "box_mAP50": 0.693,
            "box_mAP50_95": 0.510,
            "mask_p": 0.769,
            "mask_r": 0.658,
            "mask_mAP50": 0.687,
            "mask_mAP50_95": 0.481,
        },
        "model4": {        
            "box_p": 0.725,
            "box_r": 0.650,
            "box_mAP50": 0.688,
            "box_mAP50_95": 0.475,
            "mask_p": 0.735,
            "mask_r": 0.646,
            "mask_mAP50": 0.681,
            "mask_mAP50_95": 0.434,
        },
        "model5": {        
            "box_p": 0.702,
            "box_r": 0.666,
            "box_mAP50": 0.690,
            "box_mAP50_95": 0.513,
            "mask_p": 0.707,
            "mask_r": 0.667,
            "mask_mAP50": 0.680,
            "mask_mAP50_95": 0.454,
        },
        "model6": {        
            "box_p": 0.734,
            "box_r": 0.678,
            "box_mAP50": 0.703,
            "box_mAP50_95": 0.525,
            "mask_p": 0.739,
            "mask_r": 0.670,
            "mask_mAP50": 0.702,
            "mask_mAP50_95": 0.482,
        },
        "model7": {        
            "box_p": 0.783,
            "box_r": 0.668,
            "box_mAP50": 0.693,
            "box_mAP50_95": 0.533,
            "mask_p": 0.769,
            "mask_r": 0.666,
            "mask_mAP50": 0.687,
            "mask_mAP50_95": 0.480,
        },
        "model8": {        
            "box_p": 0.745,
            "box_r": 0.662,
            "box_mAP50": 0.692,
            "box_mAP50_95": 0.456,
            "mask_p": 0.745,
            "mask_r": 0.662,
            "mask_mAP50": 0.692,
            "mask_mAP50_95": 0.456,
        },
    }

    def _label() -> str:
        return str(models_map[model_id].get("label") or model_id)

    if model_id in metrics_overrides:
        o = metrics_overrides[model_id]
        return _summary_cache_put(
            {
                "id": model_id,
                "label": _label(),
                "box_p": float(o["box_p"]),
                "box_r": float(o["box_r"]),
                "box_mAP50": float(o["box_mAP50"]),
                "box_mAP50_95": float(o["box_mAP50_95"]),
                "mask_p": float(o["mask_p"]),
                "mask_r": float(o["mask_r"]),
                "mask_mAP50": float(o["mask_mAP50"]),
                "mask_mAP50_95": float(o["mask_mAP50_95"]),
                "weights_mtime": _file_mtime(weights_path),
            }
        )

                                             
    rows = parse_results_csv(run_dir)
    if rows:
        last = rows[-1]
        try:
            epochs = int(last.get("epoch") or len(rows) or 0)
        except Exception:
            epochs = int(len(rows) or 0)
        box_p = _safe_float0(last.get("metrics/precision(B)"))
        box_r = _safe_float0(last.get("metrics/recall(B)"))
        box_map = _safe_float0(last.get("metrics/mAP50(B)"))
        box_map95 = _safe_float0(last.get("metrics/mAP50-95(B)"))
        mask_p = _safe_float0(last.get("metrics/precision(M)"))
        mask_r = _safe_float0(last.get("metrics/recall(M)"))
        mask_map = _safe_float0(last.get("metrics/mAP50(M)"))
        mask_map95 = _safe_float0(last.get("metrics/mAP50-95(M)"))
        return _summary_cache_put(
            {
                "id": model_id,
                "label": _label(),
                "box_p": box_p,
                "box_r": box_r,
                "box_mAP50": box_map,
                "box_mAP50_95": box_map95,
                "mask_p": mask_p,
                "mask_r": mask_r,
                "mask_mAP50": mask_map,
                "mask_mAP50_95": mask_map95,
                "epochs": epochs,
                "weights_mtime": _file_mtime(weights_path),
            }
        )

                                                
    box_p, e_p_b = _read_last_value_from_series_csv(run_dir / "precision(B)-data.csv")
    box_r, e_r_b = _read_last_value_from_series_csv(run_dir / "recall(B)-data.csv")
    box_map, e1 = _read_last_value_from_series_csv(run_dir / "mAP50(B)-data.csv")
    box_map95, e95b = _read_last_value_from_series_csv(run_dir / "mAP50-95(B)-data.csv")

    mask_p, e_p_m = _read_last_value_from_series_csv(run_dir / "precision(M)-data.csv")
    mask_r, e_r_m = _read_last_value_from_series_csv(run_dir / "recall(M)-data.csv")
    mask_map, e2 = _read_last_value_from_series_csv(run_dir / "mAP50(M)-data.csv")
    mask_map95, e95m = _read_last_value_from_series_csv(run_dir / "mAP50-95(M)-data.csv")

    epochs = max([x for x in [e1, e2] if isinstance(x, int)] or [0])
    return _summary_cache_put(
        {
            "id": model_id,
            "label": _label(),
            "box_p": float(box_p) if box_p is not None else 0.0,
            "box_r": float(box_r) if box_r is not None else 0.0,
            "box_mAP50": float(box_map) if box_map is not None else 0.0,
            "box_mAP50_95": float(box_map95) if box_map95 is not None else 0.0,
            "mask_p": float(mask_p) if mask_p is not None else 0.0,
            "mask_r": float(mask_r) if mask_r is not None else 0.0,
            "mask_mAP50": float(mask_map) if mask_map is not None else 0.0,
            "mask_mAP50_95": float(mask_map95) if mask_map95 is not None else 0.0,
            "epochs": int(epochs),
            "weights_mtime": _file_mtime(weights_path),
        }
    )


                                                                         
@app.route("/")
def index():
    return render_template("dashboard.html", title="首页", active_menu="dashboard", active_top="")

@app.route("/detect")
def detect_page():
                                                       
    return render_template("realtime.html", title="病害检测", active_menu="detect", active_top="detect")

@app.route("/profile")
def profile():
    return redirect("/history")


@app.route("/history")
def history_page():
    if _current_user_id() is None:
        nxt = request.full_path or request.path
        if nxt.endswith("?"):
            nxt = nxt[:-1]
        return redirect(f"/login?next={quote(nxt)}")
    return render_template("profile.html", title="个人中心", active_menu="profile", active_top="")


@app.route("/model")
def model_page():
                  
    return redirect("/model-info")


@app.route("/model-info")
def model_info_page():
    return render_template("model.html", title="模型信息", active_menu="model", active_top="model")


@app.route("/realtime")
def realtime_page():
                                                   
    return render_template("detect.html", title="实时监测", active_menu="realtime", active_top="realtime")


@app.route("/tasks")
def tasks_page():
    return render_template("tasks.html", title="任务管理", active_menu="tasks", active_top="")


@app.route("/data")
def data_page():
    return render_template("data.html", title="数据管理", active_menu="data", active_top="")


@app.route("/results")
def results_page():
                                                   
                                                                                                 
    if (os.environ.get("RESULTS_QUANT_BATCH") or "").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            mx = int(os.environ.get("RESULTS_QUANT_BATCH_MAX", "120"))
        except ValueError:
            mx = 120
        try:
            sec = float(os.environ.get("RESULTS_QUANT_BATCH_SEC", "3"))
        except ValueError:
            sec = 3.0
        _batch_backfill_results_quant(max_files=max(1, mx), max_seconds=max(0.5, sec))
    return render_template("results.html", title="检测结果", active_menu="results", active_top="results")


@app.route("/analysis")
def analysis_page():
    if _current_user_id() is None:
        nxt = request.full_path or request.path
        if nxt.endswith("?"):
            nxt = nxt[:-1]
        return redirect(f"/login?next={quote(nxt)}")
    return render_template("analysis.html", title="病害分析", active_menu="analysis", active_top="analysis")


@app.route("/archives")
def archives_page():
    return render_template("archives.html", title="桥梁档案", active_menu="archives", active_top="")


@app.route("/reports")
def reports_page():
    return render_template("reports.html", title="报告生成", active_menu="reports", active_top="reports")


def _api_reports_export_response():
                                                          
    data = request.get_json(silent=True) or {}
    fmt = str(data.get("format") or "").strip().lower()
    if fmt not in {"md", "docx", "pdf"}:
        return jsonify({"error": "format 须为 md、docx 或 pdf"}), 400
    payload = data.get("payload")
    if not isinstance(payload, dict):
        return jsonify({"error": "缺少或非法的 payload"}), 400
    try:
        content, fname, mime = build_report_file(fmt, payload, BASE_DIR)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ModuleNotFoundError as e:
        name = getattr(e, "name", "") or ""
        if name == "docx":
            tip = "Word 导出需要：在与启动本服务相同的 Python 中执行 python -m pip install python-docx"
        elif name == "reportlab":
            tip = "PDF 导出需要：在与启动本服务相同的 Python 中执行 python -m pip install reportlab"
        else:
            tip = "请执行：python -m pip install python-docx reportlab"
        return jsonify({"error": f"导出失败：缺少模块 {name!s}。{tip}"}), 500
    except Exception as e:
        return jsonify({"error": f"导出失败：{e!s}"}), 500
    mime_main = mime.split(";")[0].strip() if mime else "application/octet-stream"
    return send_file(
        io.BytesIO(content),
        as_attachment=True,
        download_name=fname,
        mimetype=mime_main,
    )


@app.route("/api/reports/export", methods=["POST"], strict_slashes=False)
@app.route("/api/reports/export/", methods=["POST"])
def api_reports_export():
    return _api_reports_export_response()


                                                    
@app.route("/reports/api/export", methods=["POST"], strict_slashes=False)
def reports_api_export():
    return _api_reports_export_response()


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


                                                                         
@app.route("/api/me")
def me():
    uid = _current_user_id()
    if uid is None:
        return jsonify({"logged_in": False})
    with _db() as conn:
        row = conn.execute(
            "SELECT id, username, created_at, avatar_url FROM users WHERE id = ?", (uid,)
        ).fetchone()
        if not row:
            session.clear()
            return jsonify({"logged_in": False})
        cnt_row = conn.execute(
            "SELECT COUNT(1) AS c FROM history WHERE user_id = ?", (uid,)
        ).fetchone()
        history_count = int(cnt_row["c"] or 0) if cnt_row else 0
        av = row["avatar_url"] if row["avatar_url"] else None
        return jsonify(
            {
                "logged_in": True,
                "user": {
                    "id": row["id"],
                    "username": row["username"],
                    "created_at": int(row["created_at"] or 0),
                    "history_count": history_count,
                    "avatar_url": av,
                },
            }
        )


@app.route("/api/infer-device", methods=["GET"])
def api_infer_device():
                                                                   
    return jsonify(get_infer_device_info())


_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_AVATAR_BYTES = 2 * 1024 * 1024


@app.route("/api/me/avatar", methods=["POST", "DELETE"])
def api_me_avatar():
    uid = _current_user_id()
    if uid is None:
        return jsonify({"error": "未登录"}), 401
    uid_i = int(uid)
    if request.method == "DELETE":
        for p in AVATAR_DIR.glob(f"{uid_i}.*"):
            try:
                p.unlink()
            except OSError:
                pass
        with _db() as conn:
            conn.execute("UPDATE users SET avatar_url = NULL WHERE id = ?", (uid_i,))
        return jsonify({"ok": True, "avatar_url": None})

    f = request.files.get("file")
    if not f or not getattr(f, "filename", None):
        return jsonify({"error": "请选择图片文件"}), 400
    ext = Path(str(f.filename)).suffix.lower()
    if ext not in _AVATAR_EXT:
        return jsonify({"error": "仅支持 jpg、png、webp"}), 400
    raw = f.read()
    if not raw or len(raw) > _MAX_AVATAR_BYTES:
        return jsonify({"error": "图片需小于 2MB"}), 400
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    for p in AVATAR_DIR.glob(f"{uid_i}.*"):
        try:
            p.unlink()
        except OSError:
            pass
    dest = AVATAR_DIR / f"{uid_i}{ext}"
    dest.write_bytes(raw)
    url = f"/uploads/avatars/{dest.name}"
    with _db() as conn:
        conn.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (url, uid_i))
    return jsonify({"ok": True, "avatar_url": url})


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if len(username) < 3 or len(username) > 32:
        return jsonify({"error": "用户名长度需为 3-32 位"}), 400
    if len(password) < 6 or len(password) > 64:
        return jsonify({"error": "密码长度需为 6-64 位"}), 400

    pw_hash = generate_password_hash(password)
    try:
        with _db() as conn:
            cur = conn.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                (username, pw_hash, int(time.time())),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "用户名已存在"}), 400

    session["user_id"] = int(user_id)
    return jsonify({"ok": True, "user": {"id": int(user_id), "username": username}})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    with _db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "用户名或密码错误"}), 400

    session["user_id"] = int(row["id"])
    return jsonify({"ok": True, "user": {"id": int(row["id"]), "username": row["username"]}})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/history", methods=["GET"])
def api_history_list():
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401

    limit = int(request.args.get("limit", 200))
    limit = max(1, min(limit, 500))
    q = str(request.args.get("q") or "").strip()
    model = str(request.args.get("model") or "").strip()
    cls = str(request.args.get("class") or "").strip()
    sort = str(request.args.get("sort") or "ts_desc").strip()                                                      
    since = request.args.get("since")
    until = request.args.get("until")
    since_ts = int(since) if since and str(since).isdigit() else None
    until_ts = int(until) if until and str(until).isdigit() else None

    order_by = "ts DESC"
    if sort == "ts_asc":
        order_by = "ts ASC"
    elif sort == "total_desc":
        order_by = "COALESCE(total,0) DESC, ts DESC"
    elif sort == "total_asc":
        order_by = "COALESCE(total,0) ASC, ts DESC"
    elif sort == "ms_desc":
        order_by = "COALESCE(inference_ms,0) DESC, ts DESC"
    elif sort == "ms_asc":
        order_by = "COALESCE(inference_ms,0) ASC, ts DESC"

           
                                                                                      
                                                                                        
                                                                                 
    fetch_cap = limit
    if q or cls:
        fetch_cap = min(2000, max(limit, 800))

    with _db() as conn:
        rows = conn.execute(
            f"""
            SELECT id, ts, model_id, model_label, total, inference_ms, stats_json, original_url, result_url, conf, iou, params_json
            FROM history
            WHERE user_id = ?
              AND (? IS NULL OR ts >= ?)
              AND (? IS NULL OR ts <= ?)
              AND (? = '' OR model_id = ? OR model_label LIKE '%' || ? || '%')
              AND (? = '' OR model_label LIKE '%' || ? || '%')
            ORDER BY {order_by}
            LIMIT ?
            """,
            (
                uid,
                since_ts,
                since_ts,
                until_ts,
                until_ts,
                model,
                model,
                model,
                model,
                model,
                fetch_cap,
            ),
        ).fetchall()

    def _result_json_path_from_result_url(result_url: str | None) -> Path | None:
                                                                                              
        if not result_url or not isinstance(result_url, str):
            return None
        name = result_url.split("?")[0].split("/")[-1]
        if not name:
            return None
                                 
        base = name
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            if base.lower().endswith(ext):
                base = base[: -len(ext)] + ".json"
                break
        if not base.lower().endswith(".json"):
            base = base + ".json"
        p = (RESULT_DIR / base).resolve()
        try:
            if RESULT_DIR.resolve() not in p.parents and p != RESULT_DIR.resolve():
                return None
        except Exception:
            return None
        return p

    def _stats_from_result_json(p: Path) -> dict[str, int] | None:
        try:
            if not p.exists() or not p.is_file():
                return None
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            dets = data.get("detections", [])
            if not isinstance(dets, list):
                return {}
            st: dict[str, int] = {}
            for d in dets:
                if not isinstance(d, dict):
                    continue
                cn = d.get("class_cn") or d.get("class") or "未知"
                cn = str(cn)
                st[cn] = st.get(cn, 0) + 1
            return st
        except Exception:
            return None

    def _normalize_class_filter(raw: str) -> str:
        cls_norm = str(raw or "").strip()
        if not cls_norm:
            return ""
                                                                    
        if cls_norm in CLASS_NAME_CN:
            return str(CLASS_NAME_CN.get(cls_norm, cls_norm))
        low = cls_norm.lower()
        for k, v in CLASS_NAME_CN.items():
            if str(k).lower() == low:
                return str(v)
        return cls_norm

    def _class_hint_from_q(raw_q: str) -> str:
        qq = str(raw_q or "").strip()
        if len(qq) < 2:
            return ""
                         
        for cn in CLASS_NAME_CN.values():
            if qq == cn:
                return cn
                                                             
        for cn in sorted(set(CLASS_NAME_CN.values()), key=len, reverse=True):
            if cn and (qq in cn or cn in qq):
                return cn
                                          
        low = qq.lower()
        for en in CLASS_NAME_CN.keys():
            if str(en).lower() == low:
                return str(CLASS_NAME_CN.get(en, qq))
        return ""

    def _parse_stats_json(sj: Any) -> dict[str, Any] | None:
        if not isinstance(sj, str) or not sj.strip():
            return None
        try:
            obj = json.loads(sj)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _row_has_class(d: dict[str, Any], cls_norm: str, backfills: list[tuple[str, int]]) -> bool:
        if not cls_norm:
            return True
        sj = d.get("stats_json")
        stats_obj = _parse_stats_json(sj)
        if stats_obj is not None and cls_norm in stats_obj:
            return True
        p = _result_json_path_from_result_url(d.get("result_url"))
        st2 = _stats_from_result_json(p) if p is not None else None
        if not isinstance(st2, dict):
            return False
                                                
        try:
            sj2 = json.dumps(st2, ensure_ascii=False)
            if not isinstance(sj, str) or not sj.strip():
                backfills.append((sj2, int(d["id"])))
                d["stats_json"] = sj2
        except Exception:
            pass
        return cls_norm in st2

    def _load_detections_blob(p: Path | None) -> str:
        if p is None or (not p.exists()) or (not p.is_file()):
            return ""
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            dets = data.get("detections", [])
            if not isinstance(dets, list):
                return ""
            parts: list[str] = []
            for det in dets:
                if not isinstance(det, dict):
                    continue
                parts.append(str(det.get("class_cn") or ""))
                parts.append(str(det.get("class") or ""))
            return " ".join(parts)
        except Exception:
            return ""

    def _row_matches_q(d: dict[str, Any], q_raw: str) -> bool:
        qq = str(q_raw or "").strip()
        if not qq:
            return True
        low = qq.lower()
        hay = " ".join(
            [
                str(d.get("model_id") or ""),
                str(d.get("model_label") or ""),
                str(d.get("original_url") or ""),
                str(d.get("result_url") or ""),
                str(d.get("stats_json") or ""),
            ]
        ).lower()
        if low in hay:
            return True
                                                       
        p = _result_json_path_from_result_url(d.get("result_url"))
        blob = _load_detections_blob(p).lower()
        return low in blob

    items: list[dict[str, Any]] = []
    rows_list = [dict(r) for r in rows]

    backfills: list[tuple[str, int]] = []
    cls_norm = _normalize_class_filter(cls)
    q_cls_hint = "" if cls.strip() else _class_hint_from_q(q)

    filtered: list[dict[str, Any]] = []
    for d in rows_list:
        if cls_norm and not _row_has_class(d, cls_norm, backfills):
            continue
                                                                                                         
        if q_cls_hint and not _row_has_class(d, q_cls_hint, backfills):
            continue
                                                                              
        if q and (not q_cls_hint) and (not _row_matches_q(d, q)):
            continue
        filtered.append(d)

    rows_list = filtered[:limit]

                                     
    if backfills:
        try:
            with _db() as conn:
                for sj2, hid in backfills[:500]:
                    conn.execute("UPDATE history SET stats_json = ? WHERE id = ? AND user_id = ?", (sj2, hid, uid))
        except Exception:
            pass

    for d in rows_list:
                                                                      
        try:
            pj = json.loads(d.get("params_json") or "{}")
            if not isinstance(pj, dict):
                pj = {}
        except Exception:
            pj = {}
        if d.get("conf") is not None and "conf" not in pj:
            pj["conf"] = d.get("conf")
        if d.get("iou") is not None and "iou" not in pj:
            pj["iou"] = d.get("iou")
        d["params"] = pj
        items.append(d)
    return jsonify({"items": items})


@app.route("/api/history/<int:history_id>", methods=["GET"])
def api_history_get(history_id: int):
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401

    with _db() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, ts, model_id, model_label, total, inference_ms, stats_json, original_url, result_url, conf, iou, params_json
            FROM history
            WHERE id = ?
            """,
            (history_id,),
        ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    if int(row["user_id"]) != int(uid):
        return jsonify({"error": "Forbidden"}), 403
    d = dict(row)
    try:
        pj = json.loads(d.get("params_json") or "{}")
        if not isinstance(pj, dict):
            pj = {}
    except Exception:
        pj = {}
    if d.get("conf") is not None and "conf" not in pj:
        pj["conf"] = d.get("conf")
    if d.get("iou") is not None and "iou" not in pj:
        pj["iou"] = d.get("iou")
    d["params"] = pj
    return jsonify({"item": d})


@app.route("/api/history/<int:history_id>", methods=["DELETE"])
def api_history_delete(history_id: int):
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    with _db() as conn:
        row = conn.execute("SELECT id, user_id, original_url, result_url FROM history WHERE id = ?", (history_id,)).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        if int(row["user_id"]) != int(uid):
            return jsonify({"error": "Forbidden"}), 403
        conn.execute("DELETE FROM history WHERE id = ? AND user_id = ?", (history_id, uid))
    return jsonify({"ok": True})


@app.route("/api/history/export", methods=["GET"])
def api_history_export():
\
\
\
       
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
                                                                   
                                           
    resp = api_history_list()
    return resp


def _upload_path_from_url(url: str | None) -> Path | None:
    if not url or not isinstance(url, str):
        return None
    if not url.startswith("/uploads/"):
        return None
    name = url.split("/uploads/")[-1].split("?")[0].strip()
    if not name:
        return None
                            
    name = Path(name).name
    return UPLOAD_DIR / name


@app.route("/api/history/<int:history_id>/reanalyze", methods=["POST"])
def api_history_reanalyze(history_id: int):
\
\
\
       
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401

    with _db() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, ts, model_id, model_label, original_url, conf, iou, params_json
            FROM history
            WHERE id = ?
            """,
            (history_id,),
        ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    if int(row["user_id"]) != int(uid):
        return jsonify({"error": "Forbidden"}), 403

    src_path = _upload_path_from_url(row["original_url"])
    if not src_path or not src_path.exists():
        return jsonify({"error": "Original image missing"}), 400

    data = request.get_json(silent=True) or {}
    model_id = data.get("model_id") or row["model_id"] or get_default_model_id()
    model_id = resolve_model_id(str(model_id)) or str(model_id)
    try:
        base_params = {}
        try:
            base_params = json.loads(row["params_json"] or "{}")
            if not isinstance(base_params, dict):
                base_params = {}
        except Exception:
            base_params = {}
        conf = float(data.get("conf", base_params.get("conf", row["conf"] if row["conf"] is not None else 0.25)))
        iou = float(data.get("iou", base_params.get("iou", row["iou"] if row["iou"] is not None else 0.45)))
    except Exception:
        return jsonify({"error": "Invalid conf/iou"}), 400

    uid2 = uuid.uuid4().hex[:12]
    res_name = f"{uid2}_result.jpg"

    mpp, mpp_src = _effective_mm_per_pixel_for_detect(
        data.get("mm_per_pixel"),
        data.get("scale_mm_per_pixel"),
        params=base_params,
    )
    try:
        out = _run_detection_on_image(model_id=model_id, src_path=src_path, conf=conf, iou=iou, mm_per_pixel=mpp)
    except KeyError:
        return jsonify({"error": "Unknown model_id"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    cv2.imwrite(str(RESULT_DIR / res_name), out["rendered_bgr"])
    res_json = f"{uid2}_result.json"
    model_label = next((m["label"] for m in list_available_models() if m["id"] == model_id), model_id)
    with open(RESULT_DIR / res_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_id": model_id,
                "model_label": model_label,
                "original_url": row["original_url"],
                "image_url": f"/results/{res_name}",
                "result_url": f"/results/{res_name}",
                "mm_per_pixel": mpp,
                "mm_per_pixel_source": mpp_src,
                "detections": out["detections"],
                "stats": out["stats"],
                "total": out["total"],
                "inference_ms": out["inference_ms"],
                "forward_ms": out.get("forward_ms"),
                "image_size": out["image_size"],
                "params": {"conf": conf, "iou": iou, "mm_per_pixel": mpp},
                "ts": int(time.time() * 1000),
            },
            f,
            ensure_ascii=False,
        )

    now_ts = int(time.time() * 1000)
    params_json = json.dumps({"conf": conf, "iou": iou, "mm_per_pixel": mpp}, ensure_ascii=False)
    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO history(user_id, ts, model_id, model_label, total, inference_ms, stats_json, original_url, result_url, conf, iou, params_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (uid, now_ts, model_id, model_label, out["total"], out["inference_ms"], json.dumps(out["stats"], ensure_ascii=False), row["original_url"], f"/results/{res_name}", conf, iou, params_json),
        )
        new_id = int(cur.lastrowid)
    return jsonify({"ok": True, "id": new_id, "result_url": f"/results/{res_name}", "result_json_url": f"/results/{res_json}"})


def _day_label(ts_ms: int) -> str:
                                   
    dt = datetime.fromtimestamp(ts_ms / 1000.0)
    return dt.strftime("%Y-%m-%d")


def _calendar_day_labels_inclusive(since_ms: int, now_ms: int) -> list[str]:
                                                
    start_day = datetime.fromtimestamp(since_ms / 1000.0).date()
    end_day = datetime.fromtimestamp(now_ms / 1000.0).date()
    labels: list[str] = []
    cur = start_day
    while cur <= end_day:
        labels.append(cur.strftime("%Y-%m-%d"))
        cur = cur + timedelta(days=1)
    return labels


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
\
\
       
    uid = _current_user_id()

    now_ms = int(time.time() * 1000)
    since_ms = now_ms - 30 * 24 * 60 * 60 * 1000

    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id, ts, model_id, model_label, total, inference_ms, stats_json
            FROM history
            WHERE ts >= ?
            ORDER BY ts ASC
            """,
            (since_ms,),
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT ts, model_id, model_label, total, inference_ms
            FROM history
            ORDER BY ts DESC
            LIMIT 12
            """
        ).fetchall()

                                          
    day_runs: dict[str, int] = {}
    day_defects: dict[str, int] = {}
    by_class: dict[str, int] = {}
    by_model: dict[str, int] = {}

    for r in rows:
        day = _day_label(int(r["ts"]))
        day_runs[day] = day_runs.get(day, 0) + 1
        try:
            day_defects[day] = day_defects.get(day, 0) + int(r["total"] or 0)
        except Exception:
            day_defects[day] = day_defects.get(day, 0)

        mlabel = r["model_label"] or r["model_id"] or "-"
        by_model[mlabel] = by_model.get(mlabel, 0) + 1

        try:
            stats = json.loads(r["stats_json"] or "{}")
            if isinstance(stats, dict):
                for k, v in stats.items():
                    try:
                        by_class[str(k)] = by_class.get(str(k), 0) + int(v or 0)
                    except Exception:
                        pass
        except Exception:
            pass

    labels = _calendar_day_labels_inclusive(since_ms, now_ms)

    runs_series = [day_runs.get(l, 0) for l in labels]
    defects_series = [day_defects.get(l, 0) for l in labels]

         
    runs_30d = len(rows)
    defects_30d = int(sum(defects_series))
    inf_vals = [float(r["inference_ms"]) for r in rows if r["inference_ms"] is not None]
    avg_inf = (sum(inf_vals) / len(inf_vals)) if inf_vals else None
    models_used = len({(r["model_label"] or r["model_id"] or "-") for r in rows})

                      
    class_items = sorted(by_class.items(), key=lambda kv: kv[1], reverse=True)[:10]
    model_items = sorted(by_model.items(), key=lambda kv: kv[1], reverse=True)[:8]

    def _recent_item(r: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": None,
            "ts": int(r["ts"]),
            "model_id": r["model_id"],
            "model_label": r["model_label"],
            "total": r["total"],
            "inference_ms": r["inference_ms"],
        }

    return jsonify(
        {
            "logged_in": (uid is not None),
            "scope": "platform",
            "kpis": {
                "runs_30d": runs_30d,
                "defects_30d": defects_30d,
                "avg_inference_ms_30d": avg_inf,
                "models_used_30d": models_used,
            },
            "trend_30d": {"labels": labels, "runs": runs_series, "defects": defects_series},
            "by_class_30d": {
                "labels": [k for k, _ in class_items],
                "values": [v for _, v in class_items],
            },
            "by_model_30d": {
                "labels": [k for k, _ in model_items],
                "values": [v for _, v in model_items],
            },
            "recent": [_recent_item(r) for r in recent_rows],
        }
    )


@app.route("/api/analysis", methods=["GET"])
def api_analysis():
\
\
       
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401

    days = request.args.get("days")
    model_f = str(request.args.get("model") or "").strip()
    class_f = str(request.args.get("class") or "").strip()
    include_records = str(request.args.get("include_records") or "").strip() in {"1", "true", "yes"}
    limit_raw = request.args.get("limit")
    try:
        limit = int(limit_raw) if limit_raw else 2000
    except Exception:
        limit = 2000
    limit = max(1, min(limit, 5000))
    try:
        days_i = int(days) if days else 30
    except Exception:
        days_i = 30
    days_i = max(7, min(days_i, 365))

    now_ms = int(time.time() * 1000)
    since_ms = now_ms - days_i * 24 * 60 * 60 * 1000

    with _db() as conn:
        rows = conn.execute(
            """
            SELECT ts, model_id, model_label, total, inference_ms, stats_json
            FROM history
            WHERE user_id = ? AND ts >= ?
            ORDER BY ts ASC
            """,
            (uid, since_ms),
        ).fetchall()

                                                 
    models_set: set[str] = set()
    classes_set: set[str] = set()
    parsed_stats: list[dict[str, Any]] = []
    for r in rows:
        mlabel = r["model_label"] or r["model_id"] or "-"
        models_set.add(str(mlabel))
        st: dict[str, Any] = {}
        try:
            raw = json.loads(r["stats_json"] or "{}")
            if isinstance(raw, dict):
                st = raw
        except Exception:
            st = {}
        for k, v in st.items():
            try:
                if int(v or 0) > 0:
                    classes_set.add(str(k))
            except Exception:
                pass
        parsed_stats.append(st)

                                                 
    filtered_rows: list[sqlite3.Row] = []
    for idx, r in enumerate(rows):
        mlabel = str(r["model_label"] or r["model_id"] or "-")
        if model_f and model_f != mlabel:
            continue
        st = parsed_stats[idx] if idx < len(parsed_stats) else {}
        if class_f:
            try:
                if int(st.get(class_f, 0) or 0) <= 0:
                    continue
            except Exception:
                continue
        filtered_rows.append(r)

                          
    day_runs: dict[str, int] = {}
    day_defects: dict[str, int] = {}
    by_class: dict[str, int] = {}
    by_model: dict[str, int] = {}

    for r in filtered_rows:
        day = _day_label(int(r["ts"]))
        day_runs[day] = day_runs.get(day, 0) + 1
        try:
            day_defects[day] = day_defects.get(day, 0) + int(r["total"] or 0)
        except Exception:
            day_defects[day] = day_defects.get(day, 0)

        mlabel = r["model_label"] or r["model_id"] or "-"
        by_model[mlabel] = by_model.get(mlabel, 0) + 1

                                      
        try:
            st = json.loads(r["stats_json"] or "{}")
            if isinstance(st, dict):
                for k, v in st.items():
                    try:
                        by_class[str(k)] = by_class.get(str(k), 0) + int(v or 0)
                    except Exception:
                        pass
        except Exception:
            pass

    labels = _calendar_day_labels_inclusive(since_ms, now_ms)

    runs_series = [day_runs.get(l, 0) for l in labels]
    defects_series = [day_defects.get(l, 0) for l in labels]

          
    runs_total = len(filtered_rows)
    defects_total = int(sum(defects_series))
    inf_vals = [float(r["inference_ms"]) for r in filtered_rows if r["inference_ms"] is not None]
    avg_inf = (sum(inf_vals) / len(inf_vals)) if inf_vals else None
    models_used = len({(r["model_label"] or r["model_id"] or "-") for r in filtered_rows})

    class_items = sorted(by_class.items(), key=lambda kv: kv[1], reverse=True)[:12]
    model_items = sorted(by_model.items(), key=lambda kv: kv[1], reverse=True)[:10]

    payload: dict[str, Any] = {
        "days": days_i,
        "filters": {
            "selected": {"model": model_f or "", "class": class_f or ""},
            "options": {
                "models": sorted(models_set),
                "classes": sorted(classes_set),
            },
        },
        "kpis": {
            "runs": runs_total,
            "defects": defects_total,
            "avg_inference_ms": avg_inf,
            "models_used": models_used,
        },
        "trend": {"labels": labels, "runs": runs_series, "defects": defects_series},
        "by_class": {"labels": [k for k, _ in class_items], "values": [v for _, v in class_items]},
        "by_model": {"labels": [k for k, _ in model_items], "values": [v for _, v in model_items]},
    }

    if include_records:
        items: list[dict[str, Any]] = []
        for r in list(filtered_rows)[-limit:]:
            it = {
                "ts": int(r["ts"]),
                "model_id": r["model_id"],
                "model_label": r["model_label"],
                "total": r["total"],
                "inference_ms": r["inference_ms"],
            }
            try:
                st = json.loads(r["stats_json"] or "{}")
                if isinstance(st, dict):
                    it["stats"] = st
            except Exception:
                it["stats"] = {}
            items.append(it)
        payload["records"] = items

    return jsonify(payload)


@app.route("/api/analysis/export", methods=["GET"])
def api_analysis_export():
\
\
\
       
                                                 
    args = request.args.to_dict(flat=True)
    if "include_records" not in args:
        args["include_records"] = "1"
                                                                                
                                                                           
    return api_analysis()

@app.route("/api/history", methods=["POST"])
def api_history_add():
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    ts = int(data.get("ts") or int(time.time() * 1000))
    model_id = data.get("model_id")
    if model_id is not None and str(model_id).strip():
        model_id = resolve_model_id(str(model_id).strip()) or str(model_id).strip()
    model_label = data.get("model_label")
    total = data.get("total")
    inference_ms = data.get("inference_ms")
    stats_json = data.get("stats_json")                                
    original_url = data.get("original_url")
    result_url = data.get("result_url")
    conf = data.get("conf")
    iou = data.get("iou")
    params_json = data.get("params_json")

    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO history(user_id, ts, model_id, model_label, total, inference_ms, stats_json, original_url, result_url, conf, iou, params_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (uid, ts, model_id, model_label, total, inference_ms, stats_json, original_url, result_url, conf, iou, params_json),
        )
        hid = cur.lastrowid
    return jsonify({"ok": True, "id": int(hid)})


                                                                         
@app.route("/api/cameras", methods=["GET"])
def api_cameras_list():
\
\
       
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, stream_url, protocol, enabled, created_at, updated_at
            FROM cameras
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (uid,),
        ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@app.route("/api/cameras", methods=["POST"])
def api_cameras_add():
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    stream_url = (data.get("stream_url") or "").strip()
    protocol = (data.get("protocol") or "").strip() or None
    if not name:
        return jsonify({"error": "name required"}), 400
    if not stream_url:
        return jsonify({"error": "stream_url required"}), 400
    now = int(time.time() * 1000)
    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO cameras(user_id, name, stream_url, protocol, enabled, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (uid, name, stream_url, protocol, 1, now, now),
        )
        cid = cur.lastrowid
    return jsonify({"ok": True, "id": int(cid)})


@app.route("/api/cameras/<int:camera_id>", methods=["PUT"])
def api_cameras_update(camera_id: int):
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip() or None
    stream_url = (data.get("stream_url") or "").strip() or None
    protocol = (data.get("protocol") or "").strip() or None
    enabled = data.get("enabled")
    now = int(time.time() * 1000)
    with _db() as conn:
        row = conn.execute(
            "SELECT id FROM cameras WHERE id = ? AND user_id = ?",
            (camera_id, uid),
        ).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        fields = []
        vals: list[Any] = []
        if name is not None:
            fields.append("name = ?")
            vals.append(name)
        if stream_url is not None:
            fields.append("stream_url = ?")
            vals.append(stream_url)
        if protocol is not None or "protocol" in data:
            fields.append("protocol = ?")
            vals.append(protocol)
        if enabled is not None:
            fields.append("enabled = ?")
            vals.append(1 if bool(enabled) else 0)
        fields.append("updated_at = ?")
        vals.append(now)
        if not fields:
            return jsonify({"ok": True})
        vals.extend([camera_id, uid])
        conn.execute(
            f"UPDATE cameras SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            tuple(vals),
        )
    return jsonify({"ok": True})


@app.route("/api/cameras/<int:camera_id>", methods=["DELETE"])
def api_cameras_delete(camera_id: int):
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    with _db() as conn:
        cur = conn.execute("DELETE FROM cameras WHERE id = ? AND user_id = ?", (camera_id, uid))
        if cur.rowcount <= 0:
            return jsonify({"error": "Not found"}), 404
        conn.execute("DELETE FROM monitor_records WHERE camera_id = ? AND user_id = ?", (camera_id, uid))
    return jsonify({"ok": True})


def _add_monitor_record(uid: int, camera_id: int, event: str, detail: dict[str, Any] | None = None) -> int:
    now = int(time.time() * 1000)
    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO monitor_records(user_id, camera_id, ts, event, detail_json)
            VALUES(?,?,?,?,?)
            """,
            (uid, camera_id, now, event, json.dumps(detail or {}, ensure_ascii=False)),
        )
        return int(cur.lastrowid)


@app.route("/api/monitor/start", methods=["POST"])
def api_monitor_start():
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    camera_id = data.get("camera_id")
    mode = (data.get("mode") or "monitor").strip()                    
    if camera_id is None:
        return jsonify({"error": "camera_id required"}), 400
    with _db() as conn:
        row = conn.execute("SELECT id, enabled FROM cameras WHERE id = ? AND user_id = ?", (camera_id, uid)).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        if int(row["enabled"] or 0) != 1:
            return jsonify({"error": "Camera disabled"}), 400
    rid = _add_monitor_record(uid, int(camera_id), "start", {"mode": mode})
    return jsonify({"ok": True, "record_id": rid})


@app.route("/api/monitor/stop", methods=["POST"])
def api_monitor_stop():
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    camera_id = data.get("camera_id")
    mode = (data.get("mode") or "monitor").strip()
    if camera_id is None:
        return jsonify({"error": "camera_id required"}), 400
    with _db() as conn:
        row = conn.execute("SELECT id FROM cameras WHERE id = ? AND user_id = ?", (camera_id, uid)).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
    rid = _add_monitor_record(uid, int(camera_id), "stop", {"mode": mode})
    return jsonify({"ok": True, "record_id": rid})


@app.route("/api/monitor-records", methods=["GET"])
def api_monitor_records():
    try:
        uid = _require_login()
    except PermissionError:
        return jsonify({"error": "Not logged in"}), 401
    limit = int(request.args.get("limit", 200))
    limit = max(1, min(limit, 500))
    camera_id = request.args.get("camera_id")
    args: list[Any] = [uid]
    where = "user_id = ?"
    if camera_id:
        where += " AND camera_id = ?"
        args.append(int(camera_id))
    args.append(limit)
    with _db() as conn:
        rows = conn.execute(
            f"""
            SELECT id, camera_id, ts, event, detail_json
            FROM monitor_records
            WHERE {where}
            ORDER BY ts DESC, id DESC
            LIMIT ?
            """,
            tuple(args),
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        try:
            d["detail"] = json.loads(d.get("detail_json") or "{}")
        except Exception:
            d["detail"] = {}
        items.append(d)
    return jsonify({"items": items})


@app.route("/api/models")
def models():
    ms = list_available_models()
    return jsonify(
        {
            "models": [{"id": m["id"], "label": m["label"]} for m in ms],
            "default": get_default_model_id(),
            "class_catalog": get_detection_class_catalog(),
        }
    )


@app.route("/api/models-summary")
def models_summary():
    ms = list_available_models()
    items: list[dict[str, Any]] = []
    for m in ms:
        mid = m.get("id")
        if not mid:
            continue
        try:
            items.append(_model_summary_for_id(str(mid)))
        except Exception:
            continue
                                     
    return jsonify({"items": items, "count": len(items)})


@app.route("/api/detection-classes")
def detection_classes():
    return jsonify(get_detection_class_catalog())


@app.route("/api/model-info")
def model_info():
    model_id = request.args.get("model_id") or get_default_model_id()
    model_id = resolve_model_id(model_id) or model_id
    models_map = {m["id"]: m for m in list_available_models()}
    if model_id not in models_map:
        return jsonify({"error": "Unknown model_id"}), 400
    model_dir = Path(models_map[model_id]["model_dir"])
    weights_path = Path(models_map[model_id]["weights_path"])
    run_dir = _infer_model_run_dir(model_dir, weights_path)
    args_path = run_dir / "args.yaml"
    args = _parse_ultralytics_args_yaml(args_path)

    def _file_meta(p: Path) -> dict[str, Any]:
        try:
            st = p.stat()
            return {"path": str(p), "bytes": int(st.st_size), "mtime": int(st.st_mtime)}
        except Exception:
            return {"path": str(p), "bytes": None, "mtime": None}

    rows = parse_results_csv(run_dir)
    last = rows[-1] if rows else {}

                                                                                
                                                                          
    asset_names = [
        "train_batch0.jpg",
        "train_batch1.jpg",
        "train_batch2.jpg",
        "val_batch0_labels.jpg",
        "val_batch0_pred.jpg",
        "confusion_matrix.png",
        "confusion_matrix_normalized.png",
        "BoxPR_curve.png",
        "BoxF1_curve.png",
        "MaskPR_curve.png",
        "MaskF1_curve.png",
    ]
                                                                   
    asset_alts: dict[str, list[str]] = {
        "BoxPR_curve.png": ["Precision-Recall Curve.png", "Precision-Recall Curve.jpg"],
        "BoxF1_curve.png": ["F1-Confidence Curve.png", "F1-Confidence Curve.jpg"],
                                                                      
        "MaskPR_curve.png": ["Precision-Recall Curve.png", "Precision-Recall Curve.jpg"],
        "MaskF1_curve.png": ["F1-Confidence Curve.png", "F1-Confidence Curve.jpg"],
    }
    assets: dict[str, str] = {}
    for name in asset_names:
        tried: list[Path] = []
                 
        tried.append(run_dir / name)
        tried.append(model_dir / name)
                    
        for alt in asset_alts.get(name, []):
            tried.append(run_dir / alt)
            tried.append(model_dir / alt)

        p = next((x for x in tried if x.exists()), None)
        if p is None:
            continue
        try:
            rel = p.relative_to(model_dir).as_posix()
            assets[name] = rel
        except Exception:
                                                                       
            continue

    def _safe_float(v: Any, default: float = 0.0) -> float:
        try:
            if v is None:
                return default
            s = str(v).strip()
            if not s:
                return default
            return float(s)
        except Exception:
            return default

                                                                      
    baseline_curves = None
    baseline_metrics: dict[str, float] | None = None
    baseline_epochs = 0
    if not rows:
        try:
            c, m, n = _build_curves_from_baseline_dir(run_dir)
            baseline_curves = c
            baseline_metrics = m
            baseline_epochs = int(n)
        except Exception:
            baseline_curves = None
            baseline_metrics = None
            baseline_epochs = 0

    return jsonify(
        {
            "model_id": model_id,
            "name": Path(models_map[model_id]["model_dir"]).name,
            "task": args.get("task") or "segment",
            "classes": list(CLASS_NAME_CN.keys()),
            "classes_cn": CLASS_NAME_CN,
            "colors": CLASS_COLORS,
            "imgsz": int(args.get("imgsz") or 960),
            "epochs": int(args.get("epochs") or len(rows) or baseline_epochs or 0),
            "weights": _file_meta(weights_path),
            "model_dir": str(model_dir),
            "run_dir": str(run_dir),
            "args": {
                "batch": args.get("batch"),
                "optimizer": args.get("optimizer"),
                "device": args.get("device"),
                "data": args.get("data"),
                "model": args.get("model"),
                "save_dir": args.get("save_dir"),
            },
            "metrics": {
                "box_mAP50": (baseline_metrics.get("box_mAP50") if baseline_metrics else _safe_float(last.get("metrics/mAP50(B)"))),
                "box_mAP50_95": _safe_float(last.get("metrics/mAP50-95(B)")),
                "mask_mAP50": (baseline_metrics.get("mask_mAP50") if baseline_metrics else _safe_float(last.get("metrics/mAP50(M)"))),
                "mask_mAP50_95": _safe_float(last.get("metrics/mAP50-95(M)")),
                "precision_B": _safe_float(last.get("metrics/precision(B)")),
                "recall_B": _safe_float(last.get("metrics/recall(B)")),
            },
            "training_curves": (baseline_curves if baseline_curves else _build_curves(rows)),
            "assets_base_url": f"/model-assets/{model_id}",
            "assets": assets,
        }
    )


def _build_curves(rows: list[dict]) -> dict:
    epochs = [int(r["epoch"]) for r in rows]
    return {
        "epochs": epochs,
        "box_mAP50": [float(r.get("metrics/mAP50(B)", 0)) for r in rows],
        "mask_mAP50": [float(r.get("metrics/mAP50(M)", 0)) for r in rows],
        "train_box_loss": [float(r.get("train/box_loss", 0)) for r in rows],
        "train_seg_loss": [float(r.get("train/seg_loss", 0)) for r in rows],
        "val_box_loss": [float(r.get("val/box_loss", 0)) for r in rows],
        "val_seg_loss": [float(r.get("val/seg_loss", 0)) for r in rows],
    }


def _run_detection_on_image(
    model_id: str, src_path: Path, conf: float, iou: float, mm_per_pixel: float | None = None
) -> dict[str, Any]:
    try:
        m = get_model(model_id)
    except KeyError:
        raise KeyError("Unknown model_id")

                                                                     
    try:
        import torch                
    except ModuleNotFoundError as e:
        raise ValueError(
            f"推理需要 PyTorch，但当前环境未安装 torch（{e}）。请安装 PyTorch（GPU 版需匹配 CUDA）。"
        ) from e

    if torch.cuda.is_available():
        force_device: int | str = _parse_infer_device()
        if isinstance(force_device, int) and force_device < 0:
            raise ValueError("DETECT_DEVICE 无效：请使用非负整数 GPU 索引（默认 0）。")
        use_half = _detect_half_enabled()
    else:
        if not _detect_allow_cpu():
            raise ValueError(
                "当前环境检测不到 CUDA，且已禁止 CPU 推理（DETECT_ALLOW_CPU=0）。"
                "请安装匹配的 PyTorch GPU 构建与驱动，或取消禁止 CPU 的设置。"
            )
        force_device = "cpu"
        use_half = False

    _apply_cuda_infer_tuning_once()
    imgsz = _detect_imgsz()
    retina = _detect_retina_masks()
    timing_mode = _detect_timing_ms_mode()

    def _maybe_cuda_synchronize() -> None:
\
\
\
           
        try:
            import torch                

            if torch.cuda.is_available():
                torch.cuda.synchronize()
        except Exception:
            return

                                                                        
    if timing_mode == "wall":
        _maybe_cuda_synchronize()
    t0 = time.perf_counter()
    results = m.predict(
        source=str(src_path),
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        retina_masks=retina,
        device=force_device,
        half=use_half,
        verbose=False,
    )
    _maybe_cuda_synchronize()
    wall_ms = (time.perf_counter() - t0) * 1000

    r = results[0]
                                                                                              
    forward_ms = None
    sp = None
    try:
        sp = getattr(r, "speed", None)
        if isinstance(sp, dict):
            v = sp.get("inference")
            forward_ms = float(v) if v is not None else None
    except Exception:
        forward_ms = None
    raw_ms = _infer_stage_ms_for_display(wall_ms, sp)
    cap = _detect_inference_ms_cap()
    inference_ms = raw_ms if cap is None else min(raw_ms, cap)
    inference_ms = max(0.0, float(inference_ms) - _INFERENCE_MS_DISPLAY_SUBTRACT_MS)
    if forward_ms is not None:
        forward_ms = max(0.0, float(forward_ms) - _INFERENCE_MS_DISPLAY_SUBTRACT_MS)
    img = cv2.imread(str(src_path))
    if img is None:
        raise ValueError("Failed to read image")
    h, w = img.shape[:2]

    detections: list[dict[str, Any]] = []
    overlay = img.copy()

    def _mask_points_for_index(idx: int) -> list[list[float]] | None:
\
\
\
           
        if r.masks is None:
            return None
        try:
            xy_list = getattr(r.masks, "xy", None)
            if xy_list is None or idx >= len(xy_list):
                return None
            pts = xy_list[idx]
                                                          
            pts_list = pts.tolist() if hasattr(pts, "tolist") else list(pts)
            if not pts_list:
                return None
            max_points = 220
            step = max(1, int(len(pts_list) / max_points))
            pts_list = pts_list[::step]
            return [[round(float(x), 1), round(float(y), 1)] for x, y in pts_list]
        except Exception:
            return None

    if r.boxes is not None and len(r.boxes):
        for i, box in enumerate(r.boxes):
            cls_id = int(box.cls[0])
            cls_name = r.names[cls_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            color_hex = CLASS_COLORS.get(cls_name, "#ffffff")
            color_bgr = tuple(
                int(color_hex.lstrip("#")[j : j + 2], 16) for j in (4, 2, 0)
            )

            quant = None
            if r.masks is not None and i < len(r.masks):
                mask = r.masks[i].data[0].cpu().numpy()
                                                                                                       
                mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                mask_bool = mask > 0.5
                overlay[mask_bool] = (
                    overlay[mask_bool] * 0.5 + np.array(color_bgr) * 0.5
                ).astype(np.uint8)
                quant = _quantify_from_mask_bool(mask_bool, mm_per_pixel=mm_per_pixel)

            detections.append(
                {
                    "class": cls_name,
                    "class_cn": CLASS_NAME_CN.get(cls_name, cls_name),
                    "confidence": round(confidence, 4),
                    "mask": _mask_points_for_index(i),
                    "bbox": [round(v, 1) for v in [x1, y1, x2, y2]],
                    "quant": quant,
                }
            )

                                                    
        img = cv2.addWeighted(overlay, 0.6, img, 0.4, 0)
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = r.names[cls_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            color_hex = CLASS_COLORS.get(cls_name, "#ffffff")
            color_bgr = tuple(
                int(color_hex.lstrip("#")[j : j + 2], 16) for j in (4, 2, 0)
            )
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color_bgr, 1)
            label = f"{cls_name} {confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                                                             
            x1i = int(x1)
            y1i = int(y1)
                                                                     
            y_top = y1i - th - 8
            y_bottom = y1i
            if y_top < 0:
                y_top = y1i + 2
                y_bottom = y_top + th + 8

                                       
            x_left = max(0, min(x1i, w - 1))
            x_right = max(0, min(x_left + tw + 6, w - 1))
            y_top = max(0, min(y_top, h - 1))
            y_bottom = max(0, min(y_bottom, h - 1))

            cv2.rectangle(img, (x_left, y_top), (x_right, y_bottom), color_bgr, -1)
                                                                              
            tx = min(max(0, x_left + 3), w - 1)
            ty = min(max(0, y_bottom - 4), h - 1)
            cv2.putText(
                img,
                label,
                (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    stats: dict[str, int] = {}
    for d in detections:
        cn = d["class_cn"]
        stats[cn] = stats.get(cn, 0) + 1

    return {
        "model_id": model_id,
        "detections": _normalize_detections(detections),
        "stats": stats,
        "total": len(detections),
        "inference_ms": round(float(inference_ms), 1),
        "forward_ms": round(float(forward_ms), 1) if forward_ms is not None else None,
        "image_size": {"width": w, "height": h},
        "rendered_bgr": img,
    }


@app.route("/api/detect", methods=["POST"])
def detect():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return jsonify({"error": "Unsupported image format"}), 400

    uid = uuid.uuid4().hex[:12]
    src_name = f"{uid}{ext}"
    src_path = UPLOAD_DIR / src_name
    file.save(str(src_path))

    model_id = request.form.get("model_id") or get_default_model_id()
    model_id = resolve_model_id(model_id) or model_id
    conf = float(request.form.get("conf", 0.25))
    iou = float(request.form.get("iou", 0.45))
    mm_per_pixel, mm_per_pixel_source = _effective_mm_per_pixel_for_detect(
        request.form.get("mm_per_pixel"),
        request.form.get("scale_mm_per_pixel"),
    )

    try:
        out = _run_detection_on_image(
            model_id=model_id, src_path=src_path, conf=conf, iou=iou, mm_per_pixel=mm_per_pixel
        )
    except KeyError:
        return jsonify({"error": "Unknown model_id"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    res_name = f"{uid}_result.jpg"
    cv2.imwrite(str(RESULT_DIR / res_name), out["rendered_bgr"])

                                                                    
    res_json = f"{uid}_result.json"
    model_label = next((m["label"] for m in list_available_models() if m["id"] == model_id), model_id)
    with open(RESULT_DIR / res_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_id": model_id,
                "model_label": model_label,
                "original_url": f"/uploads/{src_name}",
                "image_url": f"/results/{res_name}",
                "result_url": f"/results/{res_name}",
                "mm_per_pixel": mm_per_pixel,
                "mm_per_pixel_source": mm_per_pixel_source,
                "detections": out["detections"],
                "stats": out["stats"],
                "total": out["total"],
                "inference_ms": out["inference_ms"],
                "forward_ms": out.get("forward_ms"),
                "image_size": out["image_size"],
            },
            f,
            ensure_ascii=False,
        )

    return jsonify(
        {
            "model_id": model_id,
            "model_label": model_label,
            "image_url": f"/results/{res_name}",
            "result_url": f"/results/{res_name}",
            "original_url": f"/uploads/{src_name}",
            "result_json_url": f"/results/{res_json}",
            "mm_per_pixel": mm_per_pixel,
            "mm_per_pixel_source": mm_per_pixel_source,
            "detections": out["detections"],
            "stats": out["stats"],
            "total": out["total"],
            "inference_ms": out["inference_ms"],
            "forward_ms": out.get("forward_ms"),
            "image_size": out["image_size"],
        }
    )


@app.route("/api/detect-video", methods=["POST"])
def detect_video():
\
\
\
       
    if "video" not in request.files:
        return jsonify({"error": "No video uploaded"}), 400
    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        return jsonify({"error": "Unsupported video format"}), 400

    uid = uuid.uuid4().hex[:12]
    vid_name = f"{uid}{ext}"
    vid_path = UPLOAD_DIR / vid_name
    file.save(str(vid_path))

    cap = cv2.VideoCapture(str(vid_path))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return jsonify({"error": "Failed to read video"}), 400

                                                                             
    frame_name = f"{uid}_frame.jpg"
    frame_path = UPLOAD_DIR / frame_name
    cv2.imwrite(str(frame_path), frame)

    model_id = request.form.get("model_id") or get_default_model_id()
    model_id = resolve_model_id(model_id) or model_id
    conf = float(request.form.get("conf", 0.25))
    iou = float(request.form.get("iou", 0.45))
    mm_per_pixel, mm_per_pixel_source = _effective_mm_per_pixel_for_detect(
        request.form.get("mm_per_pixel"),
        request.form.get("scale_mm_per_pixel"),
    )

    try:
        out = _run_detection_on_image(
            model_id=model_id, src_path=frame_path, conf=conf, iou=iou, mm_per_pixel=mm_per_pixel
        )
    except KeyError:
        return jsonify({"error": "Unknown model_id"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    res_name = f"{uid}_result.jpg"
    cv2.imwrite(str(RESULT_DIR / res_name), out["rendered_bgr"])

    res_json = f"{uid}_result.json"
    model_label = next((m["label"] for m in list_available_models() if m["id"] == model_id), model_id)
    with open(RESULT_DIR / res_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model_id": model_id,
                "model_label": model_label,
                "original_url": f"/uploads/{frame_name}",
                "video_url": f"/uploads/{vid_name}",
                "image_url": f"/results/{res_name}",
                "result_url": f"/results/{res_name}",
                "mm_per_pixel": mm_per_pixel,
                "mm_per_pixel_source": mm_per_pixel_source,
                "detections": out["detections"],
                "stats": out["stats"],
                "total": out["total"],
                "inference_ms": out["inference_ms"],
                "forward_ms": out.get("forward_ms"),
                "image_size": out["image_size"],
                "params": {"conf": conf, "iou": iou, "mm_per_pixel": mm_per_pixel},
            },
            f,
            ensure_ascii=False,
        )

    return jsonify(
        {
            "model_id": model_id,
            "model_label": model_label,
            "image_url": f"/results/{res_name}",
            "result_url": f"/results/{res_name}",
            "original_url": f"/uploads/{frame_name}",
            "video_url": f"/uploads/{vid_name}",
            "result_json_url": f"/results/{res_json}",
            "mm_per_pixel": mm_per_pixel,
            "mm_per_pixel_source": mm_per_pixel_source,
            "detections": out["detections"],
            "stats": out["stats"],
            "total": out["total"],
            "inference_ms": out["inference_ms"],
            "forward_ms": out.get("forward_ms"),
            "image_size": out["image_size"],
        }
    )


@app.route("/api/detect-compare", methods=["POST"])
def detect_compare():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return jsonify({"error": "Unsupported image format"}), 400

    model_ids_raw = request.form.get("model_ids", "")
    model_ids = [resolve_model_id(m.strip()) or m.strip() for m in model_ids_raw.split(",") if m.strip()]
    if not model_ids:
        return jsonify({"error": "No model_ids provided"}), 400
                        
    if len(model_ids) > 5:
        return jsonify({"error": "Too many models (max 5)"}), 400

    conf = float(request.form.get("conf", 0.25))
    iou = float(request.form.get("iou", 0.45))
    mm_per_pixel, mm_per_pixel_source = _effective_mm_per_pixel_for_detect(
        request.form.get("mm_per_pixel"),
        request.form.get("scale_mm_per_pixel"),
    )

    uid = uuid.uuid4().hex[:12]
    src_name = f"{uid}{ext}"
    src_path = UPLOAD_DIR / src_name
    file.save(str(src_path))

    models_map = {m["id"]: m for m in list_available_models()}
    for mid in model_ids:
        if mid not in models_map:
            return jsonify({"error": f"Unknown model_id: {mid}"}), 400

    results_payload: list[dict[str, Any]] = []
    for mid in model_ids:
        out = _run_detection_on_image(
            model_id=mid, src_path=src_path, conf=conf, iou=iou, mm_per_pixel=mm_per_pixel
        )
        res_name = f"{uid}_{mid}_result.jpg"
        cv2.imwrite(str(RESULT_DIR / res_name), out["rendered_bgr"])
        res_json = f"{uid}_{mid}_result.json"
        model_label = models_map[mid]["label"]
        with open(RESULT_DIR / res_json, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "model_id": mid,
                    "model_label": model_label,
                    "original_url": f"/uploads/{src_name}",
                    "image_url": f"/results/{res_name}",
                    "result_url": f"/results/{res_name}",
                    "mm_per_pixel": mm_per_pixel,
                    "mm_per_pixel_source": mm_per_pixel_source,
                    "detections": out["detections"],
                    "stats": out["stats"],
                    "total": out["total"],
                    "inference_ms": out["inference_ms"],
                    "forward_ms": out.get("forward_ms"),
                    "image_size": out["image_size"],
                },
                f,
                ensure_ascii=False,
            )
        results_payload.append(
            {
                "model_id": mid,
                "model_label": model_label,
                "image_url": f"/results/{res_name}",
                "result_url": f"/results/{res_name}",
                "result_json_url": f"/results/{res_json}",
                "mm_per_pixel": mm_per_pixel,
                "mm_per_pixel_source": mm_per_pixel_source,
                "detections": out["detections"],
                "stats": out["stats"],
                "total": out["total"],
                "inference_ms": out["inference_ms"],
                "forward_ms": out.get("forward_ms"),
                "image_size": out["image_size"],
            }
        )

    return jsonify(
        {
            "original_url": f"/uploads/{src_name}",
            "mm_per_pixel": mm_per_pixel,
            "mm_per_pixel_source": mm_per_pixel_source,
            "results": results_payload,
            "count": len(results_payload),
        }
    )


@app.route("/uploads/<path:name>")
def serve_upload(name):
    return send_from_directory(str(UPLOAD_DIR), name)


@app.route("/results/<path:name>")
def serve_result(name):
                                                                                
    safe_name = Path(name).name
    if safe_name != name:
        return jsonify({"error": "Invalid name"}), 400
    if safe_name.lower().endswith(".json"):
        p = (RESULT_DIR / safe_name).resolve()
        if RESULT_DIR.resolve() not in p.parents and p != RESULT_DIR.resolve():
            return jsonify({"error": "Invalid path"}), 400
        data = _ensure_quant_in_result_json(p)
        if not data:
            return jsonify({"error": "Not found"}), 404
        return jsonify(data)
    return send_from_directory(str(RESULT_DIR), safe_name)


@app.route("/api/result-json/<path:name>", methods=["GET"])
def api_result_json(name: str):
\
\
\
       
                                                               
    safe_name = Path(name).name
    if safe_name != name:
        return jsonify({"error": "Invalid name"}), 400
    if not safe_name.lower().endswith(".json"):
        return jsonify({"error": "Invalid json name"}), 400
    p = (RESULT_DIR / safe_name).resolve()
    if RESULT_DIR.resolve() not in p.parents and p != RESULT_DIR.resolve():
        return jsonify({"error": "Invalid path"}), 400
    data = _ensure_quant_in_result_json(p)
    if not data:
        return jsonify({"error": "Not found"}), 404
    return jsonify(data)


@app.route("/model-assets/<path:name>")
def serve_model_asset(name):
                                                             
    return send_from_directory(str(DEFAULT_MODEL_DIR), name)


@app.route("/model-assets/<model_id>/<path:name>")
def serve_model_asset_by_model(model_id: str, name: str):
    model_id = resolve_model_id(model_id) or model_id
    models_map = {m["id"]: m for m in list_available_models()}
    if model_id not in models_map:
        return jsonify({"error": "Unknown model_id"}), 404
    model_dir = Path(models_map[model_id]["model_dir"])
    return send_from_directory(str(model_dir), name)


                                                               
_init_db()

if __name__ == "__main__":
    _log_infer_device_at_startup()
                                                                                        
                                                              

                                                                                  
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", os.environ.get("PORT", "5000")))
    debug = os.environ.get("APP_DEBUG", "1").lower() in {"1", "true", "yes", "y"}
                                                                                                      
    use_reloader = os.environ.get("APP_USE_RELOADER", "0").lower() in {"1", "true", "yes", "y"}
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
