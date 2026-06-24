from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class BiFPNFuse(nn.Module):
\
\
\
\
       

    def __init__(self, n_inputs: int = 2, eps: float = 1e-4):
        super().__init__()
        self.eps = eps
        self.n_inputs = n_inputs
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.alpha = nn.Parameter(torch.ones(1, dtype=torch.float32), requires_grad=True)
        self.beta = nn.Parameter(torch.zeros(1, dtype=torch.float32), requires_grad=True)

    def forward(self, x):
        context = self.pool(x)
        gate = torch.sigmoid(self.alpha * context + self.beta)
        local = F.avg_pool2d(x, kernel_size=3, stride=1, padding=1)
        return x * gate + local * (1.0 - gate)