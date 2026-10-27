"""CONTROLLED fixture: divergence (no input normalization + lr far too high)."""
import os
import random

import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

SEED = int(os.environ.get("MLDOCTOR_SEED", "0"))
EPOCHS = 3
BATCH = 128
LR = 5.0  # BUG: far too high, combined with raw 0-16 pixel values below.


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    x, y = load_digits(return_X_y=True)
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=0.2, random_state=SEED)
    # BUG: raw pixel values 0-16, no normalization.
    xtr_t = torch.tensor(xtr, dtype=torch.float32)
    ytr_t = torch.tensor(ytr, dtype=torch.long)
    xte_t = torch.tensor(xte, dtype=torch.float32)
    yte_t = torch.tensor(yte, dtype=torch.long)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(xtr_t, ytr_t), batch_size=BATCH,
        shuffle=True, generator=torch.Generator().manual_seed(SEED))
    model = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 10))
    opt = torch.optim.SGD(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(EPOCHS):
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
    with torch.no_grad():
        logits = model(xte_t)
        if torch.isfinite(logits).all():
            acc = (logits.argmax(1) == yte_t).float().mean().item()
        else:
            acc = float("nan")
    print(f"FINAL metric={acc:.4f}", flush=True)


if __name__ == "__main__":
    main()
