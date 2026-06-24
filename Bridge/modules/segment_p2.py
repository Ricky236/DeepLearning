from __future__ import annotations

import copy

import torch
import torch.nn as nn
from ultralytics.nn.modules import Conv, Detect, Proto


class SegmentP2(Detect):
\
\
\
\
\
       

    def __init__(
        self,
        nc: int = 80,
        nm: int = 32,
        npr: int = 256,
        reg_max: int = 16,
        end2end: bool = False,
        ch: tuple = (),
        proto_idx: int | None = None,
    ):
        super().__init__(nc, reg_max, end2end, ch)
        if len(ch) < 2:
            raise ValueError("SegmentP2 需要至少两路输入特征，当前 ch 长度不足。")
        proto_idx = 0 if proto_idx is None and len(ch) <= 3 else (1 if proto_idx is None else proto_idx)
        if not 0 <= proto_idx < len(ch):
            raise ValueError(f"proto_idx={proto_idx} 越界，当前仅有 {len(ch)} 路特征。")

        self.nm = nm
        self.npr = npr
        self.proto_idx = proto_idx
        self.proto = Proto(ch[self.proto_idx], self.npr, self.nm)

        c4 = max(ch[0] // 4, self.nm)
        self.cv4 = nn.ModuleList(nn.Sequential(Conv(x, c4, 3), Conv(c4, c4, 3), nn.Conv2d(c4, self.nm, 1)) for x in ch)
        if end2end:
            self.one2one_cv4 = copy.deepcopy(self.cv4)

    @property
    def one2many(self):
        return dict(box_head=self.cv2, cls_head=self.cv3, mask_head=self.cv4)

    @property
    def one2one(self):
        return dict(box_head=self.one2one_cv2, cls_head=self.one2one_cv3, mask_head=self.one2one_cv4)

    def forward(self, x: list[torch.Tensor]) -> tuple | list[torch.Tensor] | dict[str, torch.Tensor]:
        outputs = super().forward(x)
        preds = outputs[1] if isinstance(outputs, tuple) else outputs
        proto = self.proto(x[self.proto_idx])
        if isinstance(preds, dict):
            if self.end2end:
                preds["one2many"]["proto"] = proto
                preds["one2one"]["proto"] = proto.detach()
            else:
                preds["proto"] = proto
        if self.training:
            return preds
        return (outputs, proto) if self.export else ((outputs[0], proto), preds)

    def _inference(self, x: dict[str, torch.Tensor]) -> torch.Tensor:
        preds = super()._inference(x)
        return torch.cat([preds, x["mask_coefficient"]], dim=1)

    def forward_head(
        self, x: list[torch.Tensor], box_head: torch.nn.Module, cls_head: torch.nn.Module, mask_head: torch.nn.Module
    ) -> dict[str, torch.Tensor]:
        preds = super().forward_head(x, box_head, cls_head)
        if mask_head is not None:
            bs = x[0].shape[0]
            preds["mask_coefficient"] = torch.cat([mask_head[i](x[i]).view(bs, self.nm, -1) for i in range(self.nl)], 2)
        return preds

    def postprocess(self, preds: torch.Tensor) -> torch.Tensor:
        boxes, scores, mask_coefficient = preds.split([4, self.nc, self.nm], dim=-1)
        scores, conf, idx = self.get_topk_index(scores, self.max_det)
        boxes = boxes.gather(dim=1, index=idx.repeat(1, 1, 4))
        mask_coefficient = mask_coefficient.gather(dim=1, index=idx.repeat(1, 1, self.nm))
        return torch.cat([boxes, scores, conf, mask_coefficient], dim=-1)

    def fuse(self) -> None:
        self.cv2 = self.cv3 = self.cv4 = None
