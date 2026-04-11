"""
fsm.py - Lightweight Finite State Machine engine for coh_bot.

The FSM owns the currently active state and drives transitions on each tick.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional, Type

logger = logging.getLogger(__name__)


class BaseState(ABC):
    """
    Abstract base for all bot states.

    Subclasses implement ``on_enter``, ``tick``, and ``on_exit``.
    ``tick`` returns the *next* state class if a transition is needed,
    or ``None`` to remain in the current state.
    """

    def on_enter(self, fsm: "FSM") -> None:
        """Called once when the FSM enters this state."""

    @abstractmethod
    def tick(self, fsm: "FSM") -> Optional[Type["BaseState"]]:
        """
        Called every loop iteration.

        Returns
        -------
        Type[BaseState] | None
            The class of the next state to transition to, or ``None`` to stay.
        """

    def on_exit(self, fsm: "FSM") -> None:
        """Called once when the FSM leaves this state."""


class FSM:
    """
    Finite State Machine that coordinates between Perception and Actions.

    Parameters
    ----------
    initial_state:
        The state class to start in.
    context:
        Arbitrary shared data passed to states (e.g. ScreenReader, InputHandler).
    """

    def __init__(
        self,
        initial_state: Type[BaseState],
        context: Optional[dict] = None,
    ) -> None:
        self.context: dict = context or {}
        self._state: BaseState = initial_state()
        self._state.on_enter(self)
        logger.info("FSM started in state: %s", type(self._state).__name__)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def current_state(self) -> BaseState:
        return self._state

    def tick(self) -> None:
        """Run one iteration of the FSM."""
        next_state_cls = self._state.tick(self)
        if next_state_cls is not None:
            self._transition(next_state_cls)

    def transition_to(self, state_cls: Type[BaseState]) -> None:
        """Manually trigger a state transition (useful from state code)."""
        self._transition(state_cls)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _transition(self, state_cls: Type[BaseState]) -> None:
        old_name = type(self._state).__name__
        self._state.on_exit(self)
        self._state = state_cls()
        self._state.on_enter(self)
        logger.info("FSM transition: %s → %s", old_name, state_cls.__name__)
