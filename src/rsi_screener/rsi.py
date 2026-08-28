from __future__ import annotations

from collections.abc import Sequence


def wilder_rsi(closes: Sequence[float], period: int = 14) -> list[float | None]:
    """Return Wilder's RSI aligned to *closes* (warm-up values are None)."""
    if period < 1:
        raise ValueError("period must be positive")
    values = [float(value) for value in closes]
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result

    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    average_gain = sum(max(change, 0.0) for change in changes[:period]) / period
    average_loss = sum(max(-change, 0.0) for change in changes[:period]) / period

    def score(gain: float, loss: float) -> float:
        if loss == 0:
            return 100.0 if gain > 0 else 50.0
        return 100.0 - (100.0 / (1.0 + gain / loss))

    result[period] = score(average_gain, average_loss)
    for index in range(period + 1, len(values)):
        change = changes[index - 1]
        average_gain = (average_gain * (period - 1) + max(change, 0.0)) / period
        average_loss = (average_loss * (period - 1) + max(-change, 0.0)) / period
        result[index] = score(average_gain, average_loss)
    return result
