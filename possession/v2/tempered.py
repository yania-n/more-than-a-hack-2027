"""Tempered-evidence HMM (v2): team-related emission log-likelihoods are scaled by 1/tau.

tau is the integrated autocorrelation time (in blocks) of the *state-conditional residual* of each
team feature, computed once from the v1 decoding (see analysis/hmm_v2/PREREGISTRATION.md, rule 1).
The tempered E-step makes the model treat ~tau consecutive blocks of team evidence as one
independent observation. The M-step is the ordinary weighted count update of the untempered
per-frame categorical emissions, so this is a power-likelihood pseudo-EM.
"""

import numpy as np

from .. import hmm

TAU_MIN, TAU_MAX = 1.0, 12.0   # PREREGISTRATION.md rule 1.5
MAX_LAG = 50


def residual_acf(scores, paths, max_lag=MAX_LAG, remove_state=True):
    """rho_k for k=1..max_lag of x - E[x | decoded state] over pairs observed in the same half.

    scores / paths: per-half arrays of block values (NaN = unobserved) and v1 states (0 H, 1 A, 2 D).
    Only blocks decoded H or A take part. remove_state=False gives the raw (signal + redundancy)
    autocorrelation, reported for information only.
    """
    xs = [np.where(p < 2, s, np.nan) for s, p in zip(scores, paths)]
    means = {}
    for c in (0, 1):
        v = np.concatenate([s[(p == c) & np.isfinite(s)] for s, p in zip(scores, paths)])
        means[c] = v.mean()
    es = []
    for x, p in zip(xs, paths):
        e = x.copy()
        if remove_state:
            e = e - np.where(p == 0, means[0], np.where(p == 1, means[1], np.nan))
        else:
            e = e - np.nanmean(np.concatenate(xs))
        es.append(e)
    rho = np.zeros(max_lag)
    for k in range(1, max_lag + 1):
        num = den = 0.0
        for e in es:
            a, b = e[:-k], e[k:]
            ok = np.isfinite(a) & np.isfinite(b)
            num += np.sum(a[ok] * b[ok])
            den += 0.5 * (np.sum(a[ok] ** 2) + np.sum(b[ok] ** 2))
        rho[k - 1] = num / den if den > 0 else 0.0
    return rho


def integrated_tau(rho):
    """1 + 2 * sum of rho_k up to (excluding) the first non-positive lag."""
    cut = np.flatnonzero(rho <= 0)
    K = int(cut[0]) if cut.size else len(rho)       # rho index K-1 is lag K: stop before it
    return 1.0 + 2.0 * float(np.sum(rho[:K]))


def tempering_weight(tau):
    return 1.0 / float(np.clip(tau, TAU_MIN, TAU_MAX))


def emission_loglik_w(X, logB, weights):
    ll = np.zeros((X.shape[0], hmm.S))
    for f, lb in enumerate(logB):
        x = X[:, f]
        ok = x >= 0
        ll[ok] += weights[f] * lb[:, x[ok]].T
    return ll


def fit(seqs, specs, stay_steps, weights, max_iter=300, tol=1e-7, prior_strength=10.0, verbose=False):
    """Baum-Welch with per-feature emission weights (1.0 = untempered)."""
    emis, A0 = hmm.init_params(seqs, specs, stay_steps)
    A = A0.copy()
    logpi = np.full(hmm.S, -np.log(hmm.S))
    n_steps = sum(len(s) for s in seqs)
    history = []
    for it in range(max_iter):
        logB = [np.log(e) for e in emis]
        logA = np.log(A)
        gammas, xi_tot, total = [], np.zeros((hmm.S, hmm.S)), 0.0
        for X in seqs:
            g, xi, lz = hmm.forward_backward(emission_loglik_w(X, logB, weights), logA, logpi)
            gammas.append(g)
            xi_tot += xi
            total += lz
        history.append(total)
        emis = hmm.m_step_emissions(specs, seqs, gammas)
        A = hmm._norm(xi_tot + prior_strength * A0)
        if verbose and it % 10 == 0:
            print("  EM iter {:3d}  tempered logL/step {:.5f}".format(it, total / n_steps))
        if it > 0 and abs(history[-1] - history[-2]) < tol * n_steps:
            break
    return dict(emis=emis, A=A, logpi=logpi, history=history, converged=it < max_iter - 1,
                A0=A0, weights=list(weights))


def decode(seqs, params):
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(params["A"])
    return [hmm.viterbi(emission_loglik_w(X, logB, params["weights"]), logA, params["logpi"])
            for X in seqs]
