"""HMM with Erlang-like durations: each class (H, A, D) is a left-to-right chain of m substates.

Why: in the plain 3-state HMM every sojourn is geometric, so the most likely length of a
(possibly spurious) possession is one step and brief flips are cheap. A chain of m substates, all
sharing the class' emission, can only be left after passing through all m, which gives a duration
with a minimum of m steps and a mode, i.e. "a touch is not a possession" built into the model.

Parameters (all learned by EM, tied across substates of a class):
  s_c      self-loop probability of every substate of class c  (-> mean sojourn m / (1 - s_c))
  ex[c,c'] where a finished sojourn of class c goes next (c' != c)
Entry is always into substate 0 of the new class. m = 1 is exactly the plain HMM of hmm.py.
"""

import numpy as np

from possession import hmm
from possession.hmm import S, _lse, _norm


def build_trans(s, ex, m):
    N = S * m
    A = np.zeros((N, N))
    for c in range(S):
        for k in range(m):
            i = c * m + k
            A[i, i] = s[c]
            if k < m - 1:
                A[i, i + 1] = 1.0 - s[c]
            else:
                for c2 in range(S):
                    if c2 != c:
                        A[i, c2 * m] = (1.0 - s[c]) * ex[c, c2]
    return A


def _fb(ll, logA, logpi):
    T, N = ll.shape
    alpha = np.empty((T, N))
    alpha[0] = logpi + ll[0]
    for t in range(1, T):
        alpha[t] = _lse(alpha[t - 1][:, None] + logA, 0) + ll[t]
    beta = np.zeros((T, N))
    for t in range(T - 2, -1, -1):
        beta[t] = _lse(logA + (ll[t + 1] + beta[t + 1])[None, :], 1)
    logz = _lse(alpha[-1], 0)
    gamma = np.exp(alpha + beta - logz)
    xi = np.zeros((N, N))
    for t in range(T - 1):
        xi += np.exp(alpha[t][:, None] + logA + (ll[t + 1] + beta[t + 1])[None, :] - logz)
    return gamma, xi, float(logz)


def _viterbi(ll, logA, logpi):
    T, N = ll.shape
    delta = np.empty((T, N))
    back = np.zeros((T, N), dtype=np.int16)
    delta[0] = logpi + ll[0]
    for t in range(1, T):
        cand = delta[t - 1][:, None] + logA
        back[t] = np.argmax(cand, axis=0)
        delta[t] = cand[back[t], np.arange(N)] + ll[t]
    path = np.empty(T, dtype=np.int16)
    path[-1] = np.argmax(delta[-1])
    for t in range(T - 2, -1, -1):
        path[t] = back[t + 1, path[t + 1]]
    return path


def _expand(ll_class, m):
    return np.repeat(ll_class, m, axis=1)  # column c*m+k = class c


def fit(seqs, specs, stay_steps, m, max_iter=300, tol=1e-7, prior_strength=10.0, verbose=False):
    emis, A0c = hmm.init_params(seqs, specs, stay_steps)
    # Initial class-level durations: mean sojourn = stay_steps[c] steps => 1 - s = m / stay.
    s0 = np.array([max(0.0, 1.0 - m / stay_steps[c]) for c in range(S)])
    ex0 = np.array([[0.0 if c == c2 else 1.0 / (S - 1) for c2 in range(S)] for c in range(S)])
    s, ex = s0.copy(), ex0.copy()
    logpi = np.full(S * m, -np.log(S * m))
    n_steps = sum(len(x) for x in seqs)
    hist = []
    for it in range(max_iter):
        logB = [np.log(e) for e in emis]
        logA = np.log(np.maximum(build_trans(s, ex, m), 1e-300))
        gam_c, xi_tot, total = [], np.zeros((S * m, S * m)), 0.0
        for X in seqs:
            ll = _expand(hmm.emission_loglik(X, logB), m)
            g, xi, lz = _fb(ll, logA, logpi)
            gam_c.append(g.reshape(len(X), S, m).sum(2))
            xi_tot += xi
            total += lz
        hist.append(total)
        emis = hmm.m_step_emissions(specs, seqs, gam_c)
        for c in range(S):
            idx = [c * m + k for k in range(m)]
            stay = sum(xi_tot[i, i] for i in idx)
            adv = sum(xi_tot[idx[k], idx[k + 1]] for k in range(m - 1))
            exits = np.array([xi_tot[idx[-1], c2 * m] if c2 != c else 0.0 for c2 in range(S)])
            leave = adv + exits.sum()
            s[c] = (stay + prior_strength * s0[c]) / (stay + leave + prior_strength)
            ex[c] = _norm(exits + prior_strength * ex0[c])
        if verbose and (it % 10 == 0):
            print("  EM iter {:3d}  logL/step {:.5f}".format(it, total / n_steps))
        if it > 0 and abs(hist[-1] - hist[-2]) < tol * n_steps:
            break
    return dict(emis=emis, s=s, ex=ex, m=m, history=hist, converged=it < max_iter - 1,
                A=build_trans(s, ex, m), logpi=logpi)


def loglik(seqs, params):
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(np.maximum(params["A"], 1e-300))
    return sum(_fb(_expand(hmm.emission_loglik(X, logB), params["m"]), logA, params["logpi"])[2]
               for X in seqs)


def decode(seqs, params):
    m = params["m"]
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(np.maximum(params["A"], 1e-300))
    return [(_viterbi(_expand(hmm.emission_loglik(X, logB), m), logA, params["logpi"]) // m).astype(np.int8)
            for X in seqs]


def posteriors(seqs, params):
    m = params["m"]
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(np.maximum(params["A"], 1e-300))
    out = []
    for X in seqs:
        g = _fb(_expand(hmm.emission_loglik(X, logB), m), logA, params["logpi"])[0]
        out.append(g.reshape(len(X), S, m).sum(2))
    return out


def sojourn_s(params, step_s):
    return [params["m"] / (1.0 - params["s"][c]) * step_s for c in range(S)]
