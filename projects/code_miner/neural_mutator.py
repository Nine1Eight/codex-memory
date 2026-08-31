import torch
import torch.nn as nn

class Mutator(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, 32),
            nn.ReLU(),
            nn.Linear(32, dim),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.net(x)
