"""Stable evaluation of a signed normal-CDF increment, not a statistical change."""

import numpy as np
from scipy.special import log_ndtr

_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(8)
_NODES, _WEIGHTS = (_NODES + 1) / 2, _WEIGHTS / 2


def normal_cdf_increment(center, delta):
    center, delta = np.broadcast_arrays(np.asarray(center, float), np.asarray(delta, float))
    if not np.isfinite(center).all() or not np.isfinite(delta).all():
        raise ValueError("finite normal-CDF increment coordinates required")
    shape = center.shape
    c, d = center.ravel(), delta.ravel()
    out = np.empty_like(c)
    small = np.abs(d) * (1 + np.abs(c) + np.abs(d)) <= 0.125
    cs, ds = c[small], d[small]
    offset = ds[:, None] * _NODES
    average = np.exp(-cs[:, None] * offset - 0.5 * offset**2) @ _WEIGHTS
    out[small] = ds * np.exp(-0.5 * cs**2 - 0.5 * np.log(2 * np.pi)) * average
    cl, dl = c[~small], d[~small]
    endpoint = cl + dl
    if not np.isfinite(endpoint).all():
        raise ValueError("normal-CDF endpoint overflow")
    # TwoSum recovers the small part lost when forming c + delta. Its density
    # correction is first-order accurate; the omitted term is O(ulp(endpoint)^2).
    recovered_delta = endpoint - cl
    addition_error = (cl - (endpoint - recovered_delta)) + (dl - recovered_delta)
    lo, hi = np.minimum(cl, endpoint), np.maximum(cl, endpoint)
    survival = hi >= -lo
    near = np.where(survival, -lo, hi)
    far = np.where(survival, -hi, lo)
    log_near, log_far = log_ndtr(near), log_ndtr(far)
    out[~small] = np.sign(dl) * np.exp(log_near) * (-np.expm1(log_far - log_near))
    out[~small] += addition_error * np.exp(-0.5 * endpoint**2 - 0.5 * np.log(2 * np.pi))
    if not np.isfinite(out).all():
        raise ValueError("nonfinite normal-CDF increment")
    return out.reshape(shape)


def centered_probit(intercept, slopes, z):
    s = np.sum(slopes**2, axis=1)
    t = np.sqrt(1 + s)
    centering_shift = -intercept * s / (t * (t + 1))
    return normal_cdf_increment(intercept + centering_shift, z @ slopes.T - centering_shift)
