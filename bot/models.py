from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

BoundingBox = Tuple[int, int, int, int]  # x, y, w, h

@dataclass
class TeamMember:
    """Domain model for a team member's game state."""
    is_leader: bool = False
    status: str = "Alive"  # Alone, Alive, Dead, Hidden
    hp_pct: float = 1.0
    end_pct: float = 1.0
    name: Optional[str] = None

@dataclass
class TeamState:
    """Collection of team members."""
    members: List[TeamMember] = field(default_factory=list)
