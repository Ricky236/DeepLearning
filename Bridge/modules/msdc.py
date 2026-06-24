from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class MSDC(nn.Module):
\
\
\
       

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.w = nn.Parameter(torch.ones(3, dtype=torch.float32), requires_grad=True)

    def forward(self, x):
        x1 = F.avg_pool2d(x, kernel_size=3, stride=1, padding=1)
        x2 = F.avg_pool2d(x, kernel_size=5, stride=1, padding=2)
        x3 = F.max_pool2d(x, kernel_size=5, stride=1, padding=2)
        w = torch.softmax(self.w.to(device=x.device, dtype=x.dtype), dim=0)
        return w[0] * x1 + w[1] * x2 + w[2] * x3