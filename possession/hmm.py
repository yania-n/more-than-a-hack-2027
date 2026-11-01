"""A small categorical-emission HMM with H / A / D states: Baum-Welch + Viterbi, numpy only.

Everything runs in log space. Observations are integer category codes per feature, with -1
meaning "missing": a missing feature simply drops out of the emission product (it is
marginalised, i.e. uninformative), so the chain carries its state across gaps via the transition
matrix alone.

Symmetry constraints (the point of this module, see README of the report):
  kind="team"  signed feature, categories ordered by signed value so that category k mirrors to
               K-1-k.  H's emission is free, A's emission is H's mirrored, D's is symmetric.
               EM therefore cannot swap the meaning of H and A *inside* the likelihood; the
               home/away anchor is the sign of the feature (positive = home closer) plus the
               initialisation, and fit() verifies it afterwards.
  kind="sym"   unsigned feature. H and A share one emission ("alive"); D has its own.
"""

import numpy as np

H, A, D = 0, 1, 2
S = 3
STATE_NAMES = ("H", "A", "D")


class FeatureSpec(object):
    def __init__(self, name, n_cat, kind, dead_tilt=0, unit_values=None):
        assert kind in ("team", "sym")
        self.name, self.n_cat, self.kind = name, n_cat, kind
        # Only used to break the H/A/D symmetry of the *initial* D emission: +1 = high category
        # is more typical of a dead ball, -1 = low category is, 0 = no opinion.
        self.dead_tilt = dead_tilt
        self.unit_values = unit_values  # raw per-block values (T,) for reporting means in units


def _lse(a, axis):
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    return (m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))).squeeze(axis)


def emission_loglik(X, logB):
    """(T, S) log P(observed features | state); missing (-1) entries contribute 0."""
    ll = np.zeros((X.shape[0], S))
    for f, lb in enumerate(logB):
        x = X[:, f]
        ok = x >= 0
        ll[ok] += lb[:, x[ok]].T
    return ll


def forward_backward(ll, logA, logpi):
    T = ll.shape[0]
    alpha = np.empty((T, S))
    alpha[0] = logpi + ll[0]
    for t in range(1, T):
        alpha[t] = _lse(alpha[t - 1][:, None] + logA, 0) + ll[t]
    beta = np.zeros((T, S))
    for t in range(T - 2, -1, -1):
        beta[t] = _lse(logA + (ll[t + 1] + beta[t + 1])[None, :], 1)
    logz = _lse(alpha[-1], 0)
    gamma = np.exp(alpha + beta - logz)
    xi = np.zeros((S, S))
    for t in range(T - 1):
        xi += np.exp(alpha[t][:, None] + logA + (ll[t + 1] + beta[t + 1])[None, :] - logz)
    return gamma, xi, float(logz)


def viterbi(ll, logA, logpi):
    T = ll.shape[0]
    delta = np.empty((T, S))
    back = np.zeros((T, S), dtype=np.int8)
    delta[0] = logpi + ll[0]
    for t in range(1, T):
        cand = delta[t - 1][:, None] + logA
        back[t] = np.argmax(cand, axis=0)  # ties -> lowest state index, deterministic
        delta[t] = cand[back[t], np.arange(S)] + ll[t]
    path = np.empty(T, dtype=np.int8)
    path[-1] = np.argmax(delta[-1])
    for t in range(T - 2, -1, -1):
        path[t] = back[t + 1, path[t + 1]]
    return path


def _norm(p):
    return p / p.sum(axis=-1, keepdims=True)


def init_params(seqs, specs, stay_steps, rho=0.5):
    """Initial emissions from the data's own marginals, tilted weakly, plus a sticky transition matrix.

    Emission start (all label-free): every state starts at the pooled marginal of the feature,
    except (a) H is tilted toward positive team-feature categories and A toward negative ones
    (rho = 0.5: 'the closer team is somewhat more likely the one in control' -- the anchor), and
    (b) D is tilted toward the dead-ball-typical end of the dead-ball features (slow, ball out,
    set-piece lead-in) by the same weak factor. EM is free to move away from all of it.
    """
    X = np.concatenate(seqs)
    emis = []
    for f, sp in enumerate(specs):
        x = X[:, f]
        m = np.bincount(x[x >= 0], minlength=sp.n_cat).astype(float) + 1.0
        m = m / m.sum()
        k = np.arange(sp.n_cat)
        if sp.kind == "team":
            m = 0.5 * (m + m[::-1])
            sign = np.sign(k - (sp.n_cat - 1) / 2.0)
            emis.append(np.stack([_norm(m * (1 + rho * sign)), _norm(m * (1 - rho * sign)), m]))
        else:
            tilt = sp.dead_tilt * (2.0 * (k + 0.5) / sp.n_cat - 1.0)
            emis.append(np.stack([m, m, _norm(m * (1 + rho * tilt))]))
    # Sticky transitions: stay with prob 1 - 1/stay_steps per step; leave mass split evenly.
    Ainit = np.full((S, S), 0.0)
    for i in range(S):
        Ainit[i] = (1.0 / stay_steps[i]) / (S - 1)
        Ainit[i, i] = 1.0 - 1.0 / stay_steps[i]
    return emis, Ainit


def m_step_emissions(specs, seqs, gammas, alpha=1.0):
    X = np.concatenate(seqs)
    G = np.concatenate(gammas)
    emis = []
    for f, sp in enumerate(specs):
        x = X[:, f]
        ok = x >= 0
        cnt = np.zeros((S, sp.n_cat))
        for s in range(S):
            cnt[s] = np.bincount(x[ok], weights=G[ok, s], minlength=sp.n_cat)
        cnt += alpha  # Laplace pseudo-count, keeps every category possible
        if sp.kind == "team":
            pH = _norm(cnt[H] + cnt[A][::-1])           # H and mirrored A are the same sample
            pD = _norm(cnt[D] + cnt[D][::-1])           # D has no side
            emis.append(np.stack([pH, pH[::-1], pD]))
        else:
            pal = _norm(cnt[H] + cnt[A])
            emis.append(np.stack([pal, pal, _norm(cnt[D])]))
    return emis


def fit(seqs, specs, stay_steps, max_iter=300, tol=1e-7, prior_strength=10.0, verbose=True):
    """Baum-Welch on several independent sequences with shared parameters.

    pi is fixed uniform: with two sequences (the two halves) there is nothing to learn it from.
    The transition matrix is MAP-estimated with a Dirichlet prior centred on the sticky
    initialisation, worth `prior_strength` pseudo-transitions per row (negligible next to the
    thousands of observed steps; it only prevents exact zeros).
    """
    emis, A0 = init_params(seqs, specs, stay_steps)
    A = A0.copy()
    logpi = np.full(S, -np.log(S))
    n_steps = sum(len(s) for s in seqs)
    history = []
    for it in range(max_iter):
        logB = [np.log(e) for e in emis]
        logA = np.log(A)
        gammas, xi_tot, total = [], np.zeros((S, S)), 0.0
        for X in seqs:
            ll = emission_loglik(X, logB)
            g, xi, lz = forward_backward(ll, logA, logpi)
            gammas.append(g)
            xi_tot += xi
            total += lz
        # log-likelihood of the data under the *current* params (before this M-step); add the
        # (constant-in-it) prior terms only when comparing monotonicity, so we report raw data LL.
        history.append(total)
        emis = m_step_emissions(specs, seqs, gammas)
        A = _norm(xi_tot + prior_strength * A0)
        if verbose and (it % 10 == 0 or it < 3):
            print("  EM iter {:3d}  logL/step {:.5f}".format(it, total / n_steps))
        if it > 0 and abs(history[-1] - history[-2]) < tol * n_steps:
            break
    converged = it < max_iter - 1
    return dict(emis=emis, A=A, logpi=logpi, history=history, converged=converged, A0=A0)


def decode(seqs, params):
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(params["A"])
    return [viterbi(emission_loglik(X, logB), logA, params["logpi"]) for X in seqs]


def posteriors(seqs, params):
    logB = [np.log(e) for e in params["emis"]]
    logA = np.log(params["A"])
    return [forward_backward(emission_loglik(X, logB), logA, params["logpi"])[0] for X in seqs]
