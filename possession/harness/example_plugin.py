"""Example of adding a method to the harness without editing it (see possession/harness/api.py).

    python -m possession.harness.run --plugin possession.harness.example_plugin --methods smooth50,always_home

`always_home` labels every frame H: a deliberately trivial method (a constant guess scores spellF1 = 0),
useful as a smoke test of the plumbing.
"""

import numpy as np

from .api import register


@register("always_home")
def always_home(ctx):
    return np.zeros(ctx.n_frames, dtype=np.int8)      # 0 = H
