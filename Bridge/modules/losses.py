from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class BoundaryLoss(nn.Module):
\
\
\
       

    def __init__(self):
        super().__init__()
        kernel = torch.tensor(
            [[-1.0, -1.0, -1.0],
             [-1.0,  8.0, -1.0],
             [-1.0, -1.0, -1.0]],
            dtype=torch.float32,
        ).view(1, 1, 3, 3)
        self.register_buffer("lap", kernel)

    def edge_map(self, x):
        if x.shape[1] > 1:
            x = x.mean(dim=1, keepdim=True)
        e = F.conv2d(x, self.lap, padding=1)
        return torch.abs(e)

    def forward(self, pred, target):
        pe = self.edge_map(pred)
        te = self.edge_map(target)
        return F.l1_loss(pe, te)


class TverskyLoss(nn.Module):
    def __init__(self, alpha=0.3, beta=0.7, gamma=0.75, eps=1e-6):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.eps = eps

    def forward(self, pred, target):
        pred = pred.sigmoid()
        pred = pred.reshape(pred.shape[0], -1)
        target = target.reshape(target.shape[0], -1).float()

        tp = (pred * target).sum(dim=1)
        fp = (pred * (1 - target)).sum(dim=1)
        fn = ((1 - pred) * target).sum(dim=1)
        tversky = (tp + self.eps) / (tp + self.alpha * fp + self.beta * fn + self.eps)
        loss = (1 - tversky) ** self.gamma
        return loss.mean()


class SmallObjectLoss(nn.Module):
\
\
\
       

    def __init__(self, gamma: float = 1.0, eps: float = 1e-6):
        super().__init__()
        self.gamma = gamma
        self.eps = eps

    def forward(self, pred, target):
        prob = pred.sigmoid()
        target = target.float()

        area = target.flatten(2).sum(dim=-1, keepdim=True)
        area = torch.clamp(area, min=1.0)
        weights = (1.0 / area) ** self.gamma
        weights = weights / (weights.mean() + self.eps)
        weights = weights.unsqueeze(-1)

        bce = F.binary_cross_entropy(prob, target, reduction="none")
        bce = bce.flatten(2) * weights
        return bce.mean()


class HybridSegLoss(nn.Module):
    def __init__(
        self,
        lambda_boundary=1.0,
        lambda_tversky=0.5,
        lambda_small=0.5,
        alpha=0.3,
        beta=0.7,
        gamma=0.75,
        small_gamma=1.0,
    ):
        super().__init__()
        self.boundary = BoundaryLoss()
        self.tversky = TverskyLoss(alpha=alpha, beta=beta, gamma=gamma)
        self.small = SmallObjectLoss(gamma=small_gamma)
        self.lb = lambda_boundary
        self.lt = lambda_tversky
        self.ls = lambda_small

    def forward(self, pred, target):
        bce = F.binary_cross_entropy_with_logits(pred, target.float())
        bd = self.boundary(pred.sigmoid(), target.float())
        tv = self.tversky(pred, target)
        sm = self.small(pred, target)
        return bce + self.lb * bd + self.lt * tv + self.ls * sm