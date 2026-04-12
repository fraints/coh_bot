from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

@dataclass
class TeamMember:
    name: str = "Unknown"
    hp_pct: float = 1.0
    endurance_pct: float = 1.0
    is_dead: bool = False
    is_leader: bool = False

@dataclass
class GameState:
    timestamp: float
    player_hp_pct: float = 1.0
    player_endurance_pct: float = 1.0
    
    target_type: str = "target__none"
    target_name: Optional[str] = None
    target_hp_pct: Optional[float] = None
    target_endurance_pct: Optional[float] = None
    target_level: Optional[int] = None
    target_rank: Optional[str] = None
    target_archetype: Optional[str] = None
    target_origin: Optional[str] = None
    target_enemy_type: Optional[str] = None
    target_super_group: Optional[str] = None
    
    team_members: List[TeamMember] = field(default_factory=list)
    
    def as_dict(self):
        return asdict(self)
