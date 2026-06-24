from __future__ import annotations

import torch
import torch.nn as nn

from .msdc import MSDC
from .attention import CGA, SGA

class GRB(nn.Module):
\
\
\
       

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.msdc = MSDC()
        self.cga = CGA()
        self.sga = SGA(7)
        self.alpha = nn.Parameter(torch.tensor(1.0))

    def forward(self, x):
        y = self.msdc(x)
        y = self.cga(y)
        y = self.sga(y)
        return x + self.alpha * y