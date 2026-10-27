"""Tiny probe-only training script (NOT a fixture). Full-batch MLP, 15 steps."""
import os
import random

import torch
import torch.nn as nn


def main():
    seed = int(os.environ.get("MLDOCTOR_SEED", "0"))
    random.seed(seed)
    torch.manual_seed(seed)
    x = torch.randn(200, 10)
    y = (x.sum(dim=1, keepdim=True) > 0).float()
    model = nn.Sequential(nn.Linear(10, 16), nn.ReLU(), nn.Linear(16, 1))
    opt = torch.optim.SGD(model.parameters(), lr=0.05)
    loss_fn = nn.BCEWithLogitsLoss()
    for step in range(15):
        opt.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        opt.step()
        print(f"step={step} loss={loss.item():.6f}", flush=True)
    print(f"FINAL loss={loss.item():.6f}", flush=True)


if __name__ == "__main__":
    main()
