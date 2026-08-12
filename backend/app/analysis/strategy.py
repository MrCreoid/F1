"""B.6 — the pit call, with hysteresis.

Naive thresholding flickers between compounds whenever the index sits on a boundary,
which is the exact failure a real strategist would mock. A recommendation changes only
after clearing the boundary by a margin *and* holding for consecutive windows.

`windows_held` is exposed deliberately: the UI shows the call arming before it fires,
and watching the system decide is the best moment in the product.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app import config
from app.analysis.trend import Compound, compound_for

CallState = Literal["HOLD", "ARMING", "BOX"]


@dataclass(frozen=True)
class CallResult:
    current: Compound
    next: Compound | None
    state: CallState
    windows_held: int
    windows_required: int
    rationale: str


class PitCallController:
    """Stateful across a session — hysteresis is memory, by definition."""

    def __init__(self, *, initial: Compound = "INTERMEDIATE") -> None:
        self._current: Compound = initial
        self._pending: Compound | None = None
        self._windows_held = 0

    @property
    def current(self) -> Compound:
        return self._current

    def _clears_margin(self, twi: float, candidate: Compound) -> bool:
        """Has the index cleared the boundary between current and candidate by the margin?"""
        low, high = config.COMPOUND_THRESHOLDS
        order: dict[Compound, int] = {"SLICK": 0, "INTERMEDIATE": 1, "FULL_WET": 2}
        drying = order[candidate] < order[self._current]

        # The boundary in question is the edge of the *current* band we are leaving.
        if self._current == "SLICK":
            boundary = low  # only one way out of the bottom band
        elif self._current == "FULL_WET":
            boundary = high  # only one way out of the top band
        else:
            boundary = low if drying else high

        if drying:
            return twi <= boundary - config.HYSTERESIS_MARGIN
        return twi >= boundary + config.HYSTERESIS_MARGIN

    def update(self, twi: float) -> CallResult:
        candidate = compound_for(twi)

        if candidate == self._current or not self._clears_margin(twi, candidate):
            self._pending = None
            self._windows_held = 0
            return CallResult(
                current=self._current,
                next=None,
                state="HOLD",
                windows_held=0,
                windows_required=config.HYSTERESIS_WINDOWS,
                rationale=f"TWI {twi:.1f}. Holding {_label(self._current)}. Margin insufficient.",
            )

        self._windows_held = self._windows_held + 1 if candidate == self._pending else 1
        self._pending = candidate

        if self._windows_held >= config.HYSTERESIS_WINDOWS:
            self._current = candidate
            self._pending = None
            held = config.HYSTERESIS_WINDOWS
            self._windows_held = 0
            return CallResult(
                current=candidate,
                next=None,
                state="BOX",
                windows_held=held,
                windows_required=config.HYSTERESIS_WINDOWS,
                rationale=f"TWI {twi:.1f} clear of the boundary. Box for {_label(candidate)}.",
            )

        return CallResult(
            current=self._current,
            next=candidate,
            state="ARMING",
            windows_held=self._windows_held,
            windows_required=config.HYSTERESIS_WINDOWS,
            rationale=(
                f"TWI {twi:.1f} clear of the {_label(candidate)} boundary. "
                f"Arming {self._windows_held} of {config.HYSTERESIS_WINDOWS}."
            ),
        )


def _label(compound: Compound) -> str:
    return {"SLICK": "slicks", "INTERMEDIATE": "intermediates", "FULL_WET": "full wets"}[compound]
