"""Non-operational contracts for downstream Black Diamond research layers."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List


class IJointSimulationEngine(ABC):
    @abstractmethod
    def reconcile_team_budgets(self, player_fits: Dict[str, Any],
                               team_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Return allocations that respect shared team/game opportunity budgets."""
        raise NotImplementedError

    @abstractmethod
    def run_correlated_simulation(self, game_state_priors: Dict[str, Any],
                                  trials: int = 100000) -> Dict[str, Any]:
        """Run dependency-preserving trials; implementation must disclose provenance."""
        raise NotImplementedError


class IWalkForwardValidator(ABC):
    @abstractmethod
    def split_chronological_windows(self, start_time: datetime, end_time: datetime,
                                    step_days: int) -> List[Dict[str, datetime]]:
        """Produce leakage-safe train/test windows in chronological order."""
        raise NotImplementedError

    @abstractmethod
    def calculate_calibration_metrics(self, simulated_probabilities: List[float],
                                      real_outcomes: List[int]) -> Dict[str, float]:
        """Return proper scoring and reliability diagnostics, not certification."""
        raise NotImplementedError
