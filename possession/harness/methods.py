"""Built-in methods: the organizers' smooth50 baseline and v1 (refit / transfer), via the pilot's
validated adapters. Importing this module registers them."""

import os

from ..pilot import adapters
from .api import register


def _atd(ctx):
    return dict(ball=ctx.ball, players=ctx.players, pspeed=ctx.pspeed, team=ctx.team)


@register("smooth50")
def smooth50(ctx):
    """starter/baseline.py unchanged: nearest player to the ball + +-50 frame majority vote."""
    raw = os.path.join(ctx.tmp_dir, "{}_{}.txt".format(ctx.name, ctx.condition))
    adapters.write_raw_atd_like(raw, ctx.players, ctx.ball, ctx.pitch)
    try:
        return adapters.smooth50_codes(raw, ctx.team, ctx.n_frames, tuple(ctx.pitch))
    finally:
        os.remove(raw)                      # derived tracking export: never leave it lying around


@register("v1_refit")
def v1_refit(ctx):
    """v1 with EM refitted on this game and ball condition (constants and bin edges recomputed).
    The set-piece feature is missing: these games have no Smart Tagging."""
    return adapters.run_v1(_atd(ctx), ctx.blocks, [], ctx.pitch, mode="refit", setpiece_missing=True)["codes"]


@register("v1_transfer")
def v1_transfer(ctx):
    """v1 with parameters, radius, carry speed and bin edges learned on the provided match; decoding only."""
    return adapters.run_v1(_atd(ctx), ctx.blocks, [], ctx.pitch, mode="transfer", ref=ctx.reference(),
                           setpiece_missing=True)["codes"]
