"""Step 0 plots + learned parameters + label-free comparison table.  python -m possession.report

Writes only under analysis/hmm_v1/ (gitignored). Needs matplotlib (possession/requirements.txt).
Reads evaluation/results/baseline_*.csv only to compute the same label-free statistics for them.
"""

import json
import os

import numpy as np

from . import data, diagnostics, features, hmm, run

OUT = data.OUT_DIR
BASELINES = ("baseline_raw", "baseline_smooth25", "baseline_smooth50", "baseline_smooth125")


def gmm2(x, iters=500):
    """2-component 1-D Gaussian mixture by EM, deterministic init at the 25th/75th percentile."""
    mu = np.percentile(x, [25, 75]).astype(float)
    sd = np.array([x.std(), x.std()]) * 0.5
    w = np.array([0.5, 0.5])
    prev = -np.inf
    for _ in range(iters):
        dens = w * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        tot = dens.sum(1)
        ll = np.log(tot).sum()
        r = dens / tot[:, None]
        n = r.sum(0)
        w, mu = n / len(x), (r * x[:, None]).sum(0) / n
        sd = np.sqrt((r * (x[:, None] - mu) ** 2).sum(0) / n)
        if abs(ll - prev) < 1e-9 * len(x):
            break
        prev = ll
    o = np.argsort(mu)
    mu, sd, w = mu[o], sd[o], w[o]
    ashman = np.sqrt(2) * abs(mu[1] - mu[0]) / np.sqrt(sd[0] ** 2 + sd[1] ** 2)
    k1 = 2  # one Gaussian: mean, sd
    ll1 = -0.5 * len(x) * (np.log(2 * np.pi * x.var()) + 1.0)  # Gaussian MLE log-likelihood
    bic1, bic2 = -2 * ll1 + k1 * np.log(len(x)), -2 * ll + 5 * np.log(len(x))
    return dict(mu=mu.tolist(), sd=sd.tolist(), w=w.tolist(), ashman_D=float(ashman),
                bic_1=float(bic1), bic_2=float(bic2), ll=float(ll))


def step0(sig, atd):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g, vis = sig["graded"], sig["vis"]
    sp = sig["pspeed"][g]
    sp = sp[np.isfinite(sp)]
    fit = gmm2(sp)
    fig, ax = plt.subplots(2, 3, figsize=(16, 8))
    a = ax[0, 0]
    a.hist(sp, bins=80, density=True, color="#9ab", log=True)
    xs = np.linspace(sp.min(), sp.max(), 400)
    comp = [fit["w"][i] * np.exp(-0.5 * ((xs - fit["mu"][i]) / fit["sd"][i]) ** 2)
            / (fit["sd"][i] * np.sqrt(2 * np.pi)) for i in (0, 1)]
    a.plot(xs, comp[0], "r--", label="GMM comp 1 (mu %.2f)" % fit["mu"][0])
    a.plot(xs, comp[1], "g--", label="GMM comp 2 (mu %.2f)" % fit["mu"][1])
    a.plot(xs, comp[0] + comp[1], "k", lw=1, label="sum")
    a.set_ylim(1e-4, None)
    a.set_title("Mean player speed, 1 s smoothed (log y)\nAshman D = %.2f" % fit["ashman_D"])
    a.set_xlabel("m/s")
    a.legend(fontsize=8)
    bs = sig["bspeed"][g & vis]
    bs = bs[np.isfinite(bs)]
    ax[0, 1].hist(bs, bins=80, color="#9ab", log=True)
    ax[0, 1].axvline(sig["carry"], color="r", ls="--", label="carry speed %.1f" % sig["carry"])
    ax[0, 1].set_title("Ball speed (+-0.2 s), log y")
    ax[0, 1].set_xlabel("m/s")
    ax[0, 1].legend(fontsize=8)
    bd = sig["beyond"][g & vis]
    ax[0, 2].hist(bd[bd > 0], bins=np.linspace(0, 10, 60), color="#9ab", log=True)
    ax[0, 2].axvline(features.OUTSIDE_MARGIN, color="r", ls="--", label="margin 0.5 m")
    ax[0, 2].set_title("Ball beyond the lines: %.1f%% of visible frames > margin"
                       % (100 * np.mean(bd > features.OUTSIDE_MARGIN)))
    ax[0, 2].set_xlabel("m beyond line")
    ax[0, 2].legend(fontsize=8)
    for k, c, lab in ((sig["dH"], "r", "nearest home"), (sig["dA"], "b", "nearest away")):
        v = k[g & vis]
        ax[1, 0].hist(v[np.isfinite(v)], bins=np.linspace(0, 30, 90), alpha=.5, color=c, label=lab)
    ax[1, 0].axvline(sig["radius"], color="k", ls="--", label="control radius %.2f" % sig["radius"])
    ax[1, 0].set_title("Distance ball -> nearest player")
    ax[1, 0].legend(fontsize=8)
    gap = sig["gap_all"][g & vis]
    gap = gap[np.isfinite(gap)]
    ax[1, 1].hist(gap, bins=np.linspace(-20, 20, 100), color="#9ab")
    ax[1, 1].set_title("g = d_A - d_H  (>0 home closer); |g|<1 m: %.0f%%" % (100 * np.mean(np.abs(gap) < 1)))
    ax[1, 2].axis("off")
    dmin = sig["dmin"][g & vis]
    txt = ("ball visible (graded): %.1f%%\nflight (ball > carry speed): %.1f%% of visible\n"
           "median dmin %.2f m\nplayer speed pct 5/50/95: %s"
           % (100 * vis[g].mean(), 100 * sig["flight"][g & vis].mean(), np.nanmedian(dmin),
              np.round(np.percentile(sp, [5, 50, 95]), 2).tolist()))
    ax[1, 2].text(0, .5, txt, fontsize=11, va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "step0.png"), dpi=110)
    plt.close(fig)
    return dict(gmm=fit, speed_pct=np.percentile(sp, [1, 5, 25, 50, 75, 95, 99]).tolist(),
                ball_visible_graded=float(vis[g].mean()), flight_share=float(sig["flight"][g & vis].mean()),
                outside_share=float(np.mean(bd > features.OUTSIDE_MARGIN)),
                radius=sig["radius"], carry=sig["carry"],
                gap_lt1m=float(np.mean(np.abs(gap) < 1)))


def learned(model):
    p, step_s = model["params"], features.BLOCK / data.FPS
    G = np.concatenate(hmm.posteriors(model["seqs"], p))
    raw = {k: np.concatenate([h[k] for h in model["halves"]]) for k in ("pspeed", "bspeed", "gap")}
    means = {}
    for k, v in raw.items():
        ok = np.isfinite(v)
        means[k] = [float(np.sum(G[ok, s] * v[ok]) / G[ok, s].sum()) for s in range(3)]
    A = p["A"]
    spd = p["emis"][[s.name for s in model["specs"]].index("player_speed")]
    edges = model["edges"]["player_speed"]
    # Dead-ball speed "threshold": speed where the D and alive emissions cross (likelihood ratio 1)
    ratio = spd[2] / spd[0]
    cross = next((float(edges[i]) for i in range(len(edges)) if ratio[i] < 1.0 <= ratio[i + 1] or
                  ratio[i] >= 1.0 > ratio[i + 1]), None)
    return dict(A=A.tolist(), sojourn_s=(step_s / (1 - np.diag(A))).tolist(),
                posterior_mean_by_state={"player_speed_mps(H,A,D)": means["pspeed"],
                                         "ball_speed_mps(H,A,D)": means["bspeed"],
                                         "signed_gap_m(H,A,D)": means["gap"]},
                state_share_posterior=G.mean(0).tolist(),
                speed_cross_mps=cross,
                p_outside=[float(p["emis"][4][s, 1]) for s in range(3)],
                p_setpiece=[float(p["emis"][5][s, 1]) for s in range(3)],
                converged=bool(p["converged"]), iters=len(p["history"]),
                logL_per_step=p["history"][-1] / sum(len(s) for s in model["seqs"]),
                monotone=bool(np.all(np.diff(p["history"]) > -1e-6 * abs(p["history"][0]) * 1e-3)),
                anchor_ok=bool(means["gap"][0] > 0 > means["gap"][1]))


def curves(model):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = model["params"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(np.array(p["history"]) / sum(len(s) for s in model["seqs"]))
    ax[0].set_title("EM log-likelihood per block")
    ax[0].set_xlabel("iteration")
    edges = np.concatenate(([0], model["edges"]["player_speed"]))
    spd = p["emis"][[s.name for s in model["specs"]].index("player_speed")]
    ax[1].step(edges, spd[0], where="post", label="H/A (alive)")
    ax[1].step(edges, spd[2], where="post", label="D")
    ax[1].set_title("Learned P(player-speed bin | state)  (equal-mass bins)")
    ax[1].set_xlabel("bin lower edge, m/s")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "em.png"), dpi=110)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    model = run.fit_model(verbose=False)
    sig, atd = model["sig"], model["atd"]
    res = {"step0": step0(sig, atd), "learned": learned(model)}
    curves(model)
    sps = data.load_set_pieces()
    table = {}
    for name in BASELINES:
        table[name] = diagnostics.summarise(
            diagnostics.read_codes(os.path.join(data.ROOT, "evaluation", "results", name + ".csv")),
            sig, sps)
    table["hmm_v1"] = diagnostics.summarise(diagnostics.read_codes(run.SUBMISSION), sig, sps)
    res["comparison"] = table
    with open(os.path.join(OUT, "results.json"), "w") as handle:
        json.dump(res, handle, indent=1)
    keys = list(table["hmm_v1"].keys())
    cols = ["baseline_smooth50", "hmm_v1", "baseline_raw", "baseline_smooth25", "baseline_smooth125"]
    lines = ["| metric | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for k in keys:
        lines.append("| %s | %s |" % (k, " | ".join("%.2f" % table[c][k] for c in cols)))
    with open(os.path.join(OUT, "comparison.md"), "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(json.dumps(res["step0"]["gmm"], indent=1))
    print(json.dumps(res["learned"], indent=1))


if __name__ == "__main__":
    main()
