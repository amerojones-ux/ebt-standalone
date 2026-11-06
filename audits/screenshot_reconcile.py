"""Deterministic screenshot-leg reconciliation. No inferred settlements or probabilities."""
from collections import Counter
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Leg:
    game: str
    player: str
    market: str
    threshold: int

    @property
    def key(self):
        return (self.game, self.player.casefold(), self.market, self.threshold)

SLIPS = {
    "orl_phx": [
        Leg("ORL-PHX", "Wendell Carter Jr.", "rebounds", 8),
        Leg("ORL-PHX", "Franz Wagner", "assists", 6),
        Leg("ORL-PHX", "Desmond Bane", "points", 15),
        Leg("ORL-PHX", "Khaman Maluach", "rebounds", 4),
        Leg("ORL-PHX", "Miles Bridges", "points", 15),
        Leg("ORL-PHX", "Devin Booker", "assists", 4),
    ],
    "mia_gsw": [
        Leg("MIA-GSW", "Davion Mitchell", "assists", 6),
        Leg("MIA-GSW", "Giannis Antetokounmpo", "rebounds", 10),
        Leg("MIA-GSW", "Davion Mitchell", "points", 10),
        Leg("MIA-GSW", "Draymond Green", "assists", 4),
        Leg("MIA-GSW", "Brandin Podziemski", "rebounds", 4),
        Leg("MIA-GSW", "Stephen Curry", "threes", 3),
    ],
    "combined": [
        Leg("MIA-GSW", "Stephen Curry", "threes", 3),
        Leg("MIA-GSW", "Davion Mitchell", "assists", 6),
        Leg("ORL-PHX", "Desmond Bane", "threes", 2),
        Leg("ORL-PHX", "Wendell Carter Jr.", "points", 10),
        Leg("ORL-PHX", "Miles Bridges", "points", 15),
    ],
}

def unique_legs(slips=SLIPS):
    return {leg.key: leg for legs in slips.values() for leg in legs}

def duplicate_counts(slips=SLIPS):
    counts = Counter(leg.key for legs in slips.values() for leg in legs)
    return {key: n for key, n in counts.items() if n > 1}

def grade(leg: Leg, actual: Optional[int], verified: bool = False):
    """Require independently verified final stats; None is NOT a miss."""
    if not verified or actual is None:
        return {"status": "HOLD", "actual": actual, "margin": None}
    if actual < 0:
        raise ValueError("Actual stat cannot be negative")
    return {"status": "HIT" if actual >= leg.threshold else "MISS",
            "actual": actual, "margin": actual - leg.threshold}

def decimal_from_american(odds: int) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be zero")
    return 1 + (odds / 100 if odds > 0 else 100 / abs(odds))

def naive_price_is_invalid():
    """The three SGP prices cannot be multiplied: duplicated/correlated legs."""
    return bool(duplicate_counts())

if __name__ == "__main__":
    assert sum(map(len, SLIPS.values())) == 17
    assert len(unique_legs()) == 14
    assert len(duplicate_counts()) == 3
    assert grade(next(iter(unique_legs().values())), None)["status"] == "HOLD"
    assert naive_price_is_invalid()
    print("PASS: 17 displayed, 14 unique, 3 duplicate keys; unverified HOLD")
