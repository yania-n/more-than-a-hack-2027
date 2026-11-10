"""The organizers' other published baseline windows, as harness methods.

starter/baseline.py publishes four variants that differ only in the half-width of the majority vote:
raw (0), smooth25, smooth50 and smooth125 (frames, at 25 fps). smooth50 is built into the harness; this
registers the other three through the very same adapter (same nearest-player step, same smooth()), so they
are the organizers' code unchanged. Check that on the provided match with check_baseline_windows.py.

    python -m possession.harness.run --plugin possession.harness.baseline_windows \
        --methods raw,smooth25,smooth50,smooth125,v1_refit,v1_transfer --out analysis/harness_baselines
"""

import os

from ..pilot import adapters
from .api import register


def _baseline(window):
    def method(ctx):
        raw = os.path.join(ctx.tmp_dir, "{}_{}_w{}.txt".format(ctx.name, ctx.condition, window))
        adapters.write_raw_atd_like(raw, ctx.players, ctx.ball, ctx.pitch)
        try:
            return adapters.smooth50_codes(raw, ctx.team, ctx.n_frames, tuple(ctx.pitch), window=window)
        finally:
            os.remove(raw)                  # derived tracking export: never leave it lying around
    return method


for _name, _window in (("raw", 0), ("smooth25", 25), ("smooth125", 125)):
    register(_name)(_baseline(_window))
