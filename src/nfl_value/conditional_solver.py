"""Opt-in square-root conditional fits; the archived default kernel is unchanged.

Exact binary aliases within an isotropic prior block can be integrated out, not
constrained to zero. Their independent prior variance is restored to contrasts.
No numerical rank cutoff, diagonal jitter, or precision clipping is used.
"""

from fractions import Fraction
from itertools import chain
from math import fsum

import numpy as np
from scipy.linalg import qr, solve_triangular

from nfl_value.ingestion import json_bytes, sha256


def compensated_residual(design, coefficients, response):
    """Original sparse row residuals using split products and accurate summation.

    Binary64 Dekker products retain multiplication roundoff without requiring
    extended precision or platform-specific FMA. No model/reference substitution.
    Overflow/underflow fails explicitly instead of promising an exact split
    outside its representable range.
    """
    a = design.tocsr()
    b = np.asarray(coefficients, dtype=float)
    y = np.asarray(response, dtype=float)
    if b.ndim != 2 or y.shape != (a.shape[0], b.shape[1]) or b.shape[0] != a.shape[1]:
        raise ValueError("residual design, coefficient and response shapes differ")
    if not all(np.isfinite(v).all() for v in (a.data, b, y)):
        raise ValueError("finite original residual inputs required")
    left, right = a.data[:, None], b[a.indices]
    with np.errstate(over="raise", under="raise", invalid="raise"):
        product = left * right
        split_left, split_right = 134217729.0 * left, 134217729.0 * right
        high_left = split_left - (split_left - left)
        high_right = split_right - (split_right - right)
        low_left, low_right = left - high_left, right - high_right
        error = (
            ((high_left * high_right - product) + high_left * low_right) + low_left * high_right
        ) + low_left * low_right
    result = np.empty_like(y)
    bounds = list(zip(a.indptr[:-1].tolist(), a.indptr[1:].tolist()))
    for j in range(y.shape[1]):
        # Convert in bulk: fsum receives the identical ordered binary64 values,
        # without allocating a NumPy scalar for every term of every row.
        p, e = (-product[:, j]).tolist(), (-error[:, j]).tolist()
        response_values = y[:, j].tolist()
        result[:, j] = [
            fsum(chain((response_values[i],), p[start:end], e[start:end]))
            for i, (start, end) in enumerate(bounds)
        ]
    return result


def binary_nullspace(matrix):
    """Return an exact rational null basis; nonbinary designs are not rounded."""
    a = np.asarray(matrix)
    if a.ndim != 2 or not np.isin(a, (0, 1)).all():
        raise ValueError("exact binary design required for alias certification")
    columns = a.shape[1]
    packed = np.unique(np.packbits(a.astype(np.uint8), axis=1), axis=0)
    patterns = np.unpackbits(packed, axis=1)[:, :columns]
    pivots = {}
    for pattern in patterns:
        row = {int(j): Fraction(1) for j in np.flatnonzero(pattern)}
        while row:
            pivot = min(row)
            if pivot not in pivots:
                denominator = row[pivot]
                pivots[pivot] = {j: value / denominator for j, value in row.items()}
                break
            multiplier = row[pivot]
            for j, value in pivots[pivot].items():
                updated = row.get(j, Fraction(0)) - multiplier * value
                if updated:
                    row[j] = updated
                else:
                    row.pop(j, None)
    free = [j for j in range(columns) if j not in pivots]
    basis = []
    for j in free:
        vector = [Fraction(0)] * columns
        vector[j] = Fraction(1)
        for pivot in sorted(pivots, reverse=True):
            vector[pivot] = -sum(
                (value * vector[k] for k, value in pivots[pivot].items() if k != pivot),
                Fraction(0),
            )
        basis.append(vector)
    certificate = {
        "columns": columns,
        "unique_patterns": len(patterns),
        "exact_rank": len(pivots),
        "nullity": len(free),
        "rational_basis_sha256": sha256(json_bytes([[str(x) for x in v] for v in basis])),
    }
    return np.asarray(basis, dtype=float).reshape(len(free), columns).T, certificate


def _alias_transform(prepared, groups, *, remove_aliases, reverse_basis):
    p, r = len(prepared.names), prepared.fixed_count
    supplied = []
    for indices in groups.values():
        a = np.asarray(indices)
        if a.ndim != 1 or a.dtype.kind not in "iu":
            raise ValueError("integer random-effect group indices required")
        supplied.extend(a.tolist())
    if sorted(supplied) != list(range(r, p)):
        raise ValueError("random-effect groups must partition all random columns")
    fixed = [
        j
        for j, name in enumerate(prepared.names[:r])
        if name == "context/intercept" or name.startswith("context/season_")
    ]
    fixed_design = prepared.x[:, fixed].toarray()
    if not np.isin(fixed_design, (0, 1)).all():
        raise ValueError("certified context columns must be binary")
    parts = [np.eye(p)[:, :r]]
    reduced_groups, removed, certificates = {}, {}, {}
    offset = r
    used = []
    for group, indices in groups.items():
        indices = np.asarray(indices, dtype=int)
        if reverse_basis:
            indices = indices[::-1]
        used.extend(indices.tolist())
        xg = prepared.x[:, indices].toarray()
        k = len(indices)
        certificate = {"nullity": 0, "reason": "reduction_disabled"}
        null, fixed_shift = np.empty((k, 0)), np.empty((r, 0))
        complement = np.eye(k)
        if remove_aliases and k:
            if np.isin(xg, (0, 1)).all():
                raw, certificate = binary_nullspace(np.column_stack([fixed_design, xg]))
                count = raw.shape[1]
                if count:
                    random_raw = raw[len(fixed) :]
                    # A null vector in fixed context alone would make the flat
                    # prior improper; do not hide it with a numerical rank rule.
                    if any(not np.any(random_raw[:, j]) for j in range(count)):
                        raise ValueError("dependent certified fixed context")
                    rotation, upper = qr(random_raw, mode="full")
                    null, complement = rotation[:, :count], rotation[:, count:]
                    if np.any(np.diag(upper[:count]) == 0):
                        raise ValueError("singular exact alias coordinate map")
                    shift = solve_triangular(upper[:count].T, -raw[: len(fixed)].T, lower=True).T
                    fixed_shift = np.zeros((r, count))
                    fixed_shift[fixed] = shift
            else:
                certificate = {"nullity": 0, "reason": "nonbinary_block_not_reduced"}
        t = np.zeros((p, complement.shape[1]))
        t[indices] = complement
        parts.append(t)
        reduced_groups[group] = np.arange(offset, offset + complement.shape[1])
        offset += complement.shape[1]
        u = np.zeros((p, null.shape[1]))
        u[:r] = -fixed_shift
        u[indices] = null
        removed[group] = u
        certificates[group] = certificate
    if sorted(used) != list(range(r, p)):
        raise ValueError("random-effect groups must partition all random columns")
    return np.column_stack(parts), reduced_groups, removed, certificates


class SquareRootSystem:
    """Prepared row-space computation for one design and one/more responses."""

    def __init__(
        self,
        prepared,
        y,
        groups,
        *,
        exact_aliases=False,
        reverse_basis=False,
        original_residual=False,
    ):
        self.prepared = prepared
        self.groups = {g: np.asarray(indices) for g, indices in groups.items()}
        y = np.asarray(y, dtype=float)
        if y.ndim == 1:
            y = y[:, None]
        if y.ndim != 2 or y.shape[0] != prepared.x.shape[0] or not np.isfinite(y).all():
            raise ValueError("finite response matrix matching design required")
        if not y.shape[1]:
            raise ValueError("at least one response required")
        self.y = y
        self.original_residual = original_residual
        self.game_indices = (
            [np.flatnonzero(prepared.game_codes == g) for g in range(len(prepared.game_names))]
            if original_residual
            else []
        )
        self.transform, self.reduced_groups, self.removed, self.certificates = _alias_transform(
            prepared, self.groups, remove_aliases=exact_aliases, reverse_basis=reverse_basis
        )
        self.x = np.asarray(prepared.x @ self.transform)
        self.p = self.x.shape[1]
        self.responses = y.shape[1]
        self.game_x = np.empty((0, self.p))
        self.game_y = np.empty((0, self.responses))
        block = np.column_stack([self.x, y])
        if prepared.game_names:
            sums = np.zeros((len(prepared.game_names), block.shape[1]))
            np.add.at(sums, prepared.game_codes, block)
            means = sums / prepared.game_counts[:, None]
            self.game_x, self.game_y = means[:, : self.p], means[:, self.p :]
            block -= means[prepared.game_codes]
            self.game_rows = np.sqrt(prepared.game_counts)[:, None] * means
        else:
            self.game_rows = np.empty((0, block.shape[1]))
        self.within_rows = block
        self.compressed = qr(block, mode="r", check_finite=False)[0][: block.shape[1]]

    def cell(
        self, penalty, game_precision, contrasts, shape, scale, *, compressed=True, need_games=True
    ):
        prepared, r = self.prepared, self.prepared.fixed_count
        p = len(prepared.names)
        penalty = np.asarray(penalty, dtype=float)
        contrasts = np.asarray(contrasts, dtype=float)
        if (
            penalty.shape != (p,)
            or not np.isfinite(penalty).all()
            or np.any(penalty[:r] != 0)
            or np.any(penalty[r:] <= 0)
        ):
            raise ValueError("positive random-effect and zero context precisions required")
        if contrasts.ndim != 2 or contrasts.shape[1] != p or not np.isfinite(contrasts).all():
            raise ValueError("invalid linear contrasts")
        if not np.isfinite([shape, scale]).all() or shape <= 1 or scale <= 0:
            raise ValueError("proper finite-mean noise prior required")
        reduced_penalty = np.zeros(self.p)
        restored_variance = np.zeros(len(contrasts))
        for group, indices in self.groups.items():
            if not len(indices):
                continue
            value = penalty[indices[0]]
            if np.any(penalty[indices] != value):
                raise ValueError("isotropic precision required within certified block")
            reduced_penalty[self.reduced_groups[group]] = value
            null_contrast = contrasts @ self.removed[group]
            restored_variance += np.sum(null_contrast * null_contrast, axis=1) / value
        prior = np.zeros((self.p - r, self.p + self.responses))
        prior[:, r : self.p] = np.diag(np.sqrt(reduced_penalty[r:]))
        rows = self.compressed if compressed else self.within_rows
        logdet_game = 0.0
        if prepared.game_names:
            if game_precision is None or not np.isfinite(game_precision) or game_precision <= 0:
                raise ValueError("positive game precision required")
            # Keep a tiny positive mean-direction weight as a square root. The
            # equivalent 1 - n/(n + lambda) would lose it by subtraction.
            weight = np.sqrt(game_precision) / np.sqrt(game_precision + prepared.game_counts)
            rows = np.vstack([rows, self.game_rows * weight[:, None]])
            logdet_game = float(
                (
                    np.logaddexp(np.log(game_precision), np.log(prepared.game_counts))
                    - np.log(game_precision)
                ).sum()
            )
        elif game_precision is not None:
            raise ValueError("game precision requires a game design")
        upper = qr(np.vstack([rows, prior]), mode="r", check_finite=False)[0]
        factor, response = upper[: self.p, : self.p], upper[: self.p, self.p :]
        if np.any(np.diag(factor) == 0):
            raise ValueError("singular square-root conditional system")
        mean = solve_triangular(factor, response, check_finite=False)
        reduced_contrast = contrasts @ self.transform
        inverse_root = solve_triangular(
            factor.T, reduced_contrast.T, lower=True, check_finite=False
        )
        diagonal = np.sum(inverse_root * inverse_root, axis=0) + restored_variance
        full_mean = self.transform @ mean
        game_mean = (
            (self.game_y - self.game_x @ mean)
            * (prepared.game_counts / (game_precision + prepared.game_counts))[:, None]
            if prepared.game_names and need_games
            else np.empty((0, self.responses))
        )
        if self.original_residual:
            residual = compensated_residual(prepared.x, full_mean, self.y)
            game_penalty = np.zeros(self.responses)
            if prepared.game_names:
                game_mean = (
                    np.array(
                        [
                            [fsum(residual[indices, j]) for j in range(self.responses)]
                            for indices in self.game_indices
                        ]
                    )
                    / (game_precision + prepared.game_counts)[:, None]
                )
                residual -= game_mean[prepared.game_codes]
                game_penalty = game_precision * np.sum(game_mean**2, axis=0)
            q = (
                np.sum(residual**2, axis=0)
                + np.sum(penalty[:, None] * full_mean**2, axis=0)
                + game_penalty
            )
            if not need_games:
                game_mean = np.empty((0, self.responses))
        else:
            q = np.sum(upper[self.p :, self.p :] ** 2, axis=0)
        a = shape + (prepared.x.shape[0] - r) / 2
        b = scale + q / 2
        determinant = (
            logdet_game
            + 2 * np.log(np.abs(np.diag(factor))).sum()
            - np.log(reduced_penalty[r:]).sum()
        )
        likelihood = -0.5 * determinant - a * np.log(b)
        arrays = [full_mean, game_mean, diagonal, q, likelihood]
        if any(not np.isfinite(value).all() for value in arrays):
            raise ValueError("nonfinite square-root conditional result")
        return {
            "mean": full_mean,
            "game_mean": game_mean,
            "location": contrasts @ full_mean,
            "diagonal": diagonal,
            "posterior_shape": a,
            "posterior_scale": b,
            "log_likelihood": likelihood,
            "residual_quadratic": q,
        }
