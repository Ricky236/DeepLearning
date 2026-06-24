from __future__ import annotations

import torch
import torch.nn as nn


class CGA(nn.Module):
                                 

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.alpha = nn.Parameter(torch.tensor(1.0))
        self.beta = nn.Parameter(torch.tensor(0.0))

    def forward(self, x):
        stat = self.pool(x)
        stat = stat / (stat.abs().mean(dim=1, keepdim=True) + 1e-6)
        gate = torch.sigmoid(self.alpha * stat + self.beta)
        return x * gate


class SGA(nn.Module):
                                 

    def __init__(self, k: int = 7, *args, **kwargs):
        super().__init__()
        assert k in (3, 7)
        p = 3 if k == 7 else 1
        self.conv = nn.Conv2d(2, 1, k, padding=p, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg = torch.mean(x, dim=1, keepdim=True)
        mx, _ = torch.max(x, dim=1, keepdim=True)
        a = self.sigmoid(self.conv(torch.cat([avg, mx], dim=1)))
        return x * a