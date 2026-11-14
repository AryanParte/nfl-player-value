"""Small independent Decimal mixed-model oracle, never an NFL fitting default."""

from decimal import Decimal, localcontext

import numpy as np


def decimal_cell(
    x, y, fixed_count, penalty, game_codes, game_precision, contrasts, shape, scale, *, digits=80
):
    """Build original augmented normal equations from exact float inputs.

    LDL in Decimal is independent of the production QR/alias and marginalized
    sufficient-statistic paths. Deliberately bounded to tiny verification cases.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y[:, None]
    if x.shape[0] > 64 or x.shape[1] > 32 or not 60 <= digits <= 160:
        raise ValueError("Decimal oracle is restricted to small known-answer controls")
    codes = np.asarray(game_codes, dtype=int)
    z = np.eye(int(codes.max()) + 1)[codes] if len(codes) else np.empty((len(x), 0))
    full_x = np.column_stack([x, z])
    penalties = np.r_[penalty, np.full(z.shape[1], game_precision or 0)]
    full_l = np.column_stack([contrasts, np.zeros((len(contrasts), z.shape[1]))])
    with localcontext() as context:
        context.prec = digits
        zero, one = Decimal(0), Decimal(1)
        convert = lambda a: [[Decimal.from_float(float(v)) for v in row] for row in a]
        a, responses, l = convert(full_x), convert(y), convert(full_l)
        d = [Decimal.from_float(float(v)) for v in penalties]
        n, p, m = len(a), len(a[0]), y.shape[1]
        gram = [
            [
                sum((row[i] * row[j] for row in a), zero) + (d[i] if i == j else zero)
                for j in range(p)
            ]
            for i in range(p)
        ]
        lower = [[zero] * p for _ in range(p)]
        diagonal = [zero] * p
        for i in range(p):
            lower[i][i] = one
            diagonal[i] = gram[i][i] - sum((lower[i][k] ** 2 * diagonal[k] for k in range(i)), zero)
            if diagonal[i] <= 0:
                raise ValueError("high-precision control system is not positive definite")
            for j in range(i + 1, p):
                lower[j][i] = (
                    gram[j][i]
                    - sum((lower[j][k] * lower[i][k] * diagonal[k] for k in range(i)), zero)
                ) / diagonal[i]

        def solve(rhs):
            forward = [zero] * p
            for i in range(p):
                forward[i] = rhs[i] - sum((lower[i][j] * forward[j] for j in range(i)), zero)
            answer = [forward[i] / diagonal[i] for i in range(p)]
            for i in range(p - 1, -1, -1):
                answer[i] -= sum((lower[j][i] * answer[j] for j in range(i + 1, p)), zero)
            return answer

        beta = []
        q = []
        for j in range(m):
            cross = [sum((a[i][k] * responses[i][j] for i in range(n)), zero) for k in range(p)]
            mean = solve(cross)
            beta.append(mean)
            q.append(
                sum(
                    (
                        (responses[i][j] - sum((a[i][k] * mean[k] for k in range(p)), zero)) ** 2
                        for i in range(n)
                    ),
                    zero,
                )
                + sum((d[k] * mean[k] ** 2 for k in range(p)), zero)
            )
        location = [
            [sum((row[k] * beta[j][k] for k in range(p)), zero) for j in range(m)] for row in l
        ]
        variances = [sum((v * s for v, s in zip(row, solve(row))), zero) for row in l]
        posterior_shape = Decimal.from_float(float(shape)) + Decimal(n - fixed_count) / 2
        posterior_scale = [Decimal.from_float(float(scale)) + value / 2 for value in q]
        determinant = sum((value.ln() for value in diagonal), zero) - sum(
            (value.ln() for value in d[fixed_count:]), zero
        )
        likelihood = [-determinant / 2 - posterior_shape * value.ln() for value in posterior_scale]
        result = {
            "mean": [[beta[j][k] for j in range(m)] for k in range(x.shape[1])],
            "game_mean": [[beta[j][k] for j in range(m)] for k in range(x.shape[1], p)],
            "location": location,
            "diagonal": variances,
            "residual_quadratic": q,
            "posterior_shape": posterior_shape,
            "posterior_scale": posterior_scale,
            "log_likelihood": likelihood,
        }

        def strings(value):
            return [strings(v) for v in value] if isinstance(value, list) else str(value)

        return {key: strings(value) for key, value in result.items()}


def reference_agreement(a, b):
    """Check before binary64 conversion, including zeros and large variances."""

    def recurse(left, right):
        if isinstance(left, list):
            return len(left) == len(right) and all(recurse(x, y) for x, y in zip(left, right))
        x, y = Decimal(left), Decimal(right)
        return abs(x - y) <= Decimal("1e-20") * (Decimal(1) + abs(y))

    with localcontext() as context:
        context.prec = 120
        return set(a) == set(b) and all(recurse(a[key], b[key]) for key in a)


def as_float(result):
    return {key: np.asarray(value, dtype=float) for key, value in result.items()}
