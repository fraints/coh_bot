# City of Heroes Bot: Development Roadmap

This document outlines the architecture and implementation phases required to transform the current prototype into a production-ready, automated bot capable of complex roles such as healing, buffing, and strategic combat.

## 1. Vision: The "Heal/Buff Bot"
The primary goal is to create a bot that doesn't just attack but manages team resources. 
- **Role Awareness**: Understands its own powers (heals, buffs, debuffs).
- **Team Awareness**: Monitors health and endurance across the entire team.
- **Strategic Recasting**: Ensures buffs are maintained on all teammates without manual intervention.

---

## 2. Entity Perception System
The perception layer must shift from a "Player vs. Target" model to a more generic "Entity Tracking" model.

### 2.1 Generic `EntityState`
Every trackable unit (Team members, Enemies, Self) will share a common data structure:
- `id`: Index within the team (0-7) or "target".
- `name`: OCR extracted name.
- `hp_pct`: Current health percentage.
- `endurance_pct`: Current endurance percentage.
- `is_targeted`: Boolean flag if the bot currently has this entity selected.
- `status_effects`: List of active buff/debuff icons detected in their frame.

### 2.2 `TeamState` (Team Awareness)
- **Detection**: Uses Anchor-based template matching to locate the "Team Window".
- **Extraction**: Iterates through the 8 vertical slots in the Team Window to read `hp_pct` and `endurance_pct` for every teammate simultaneously.
- **Selection**: Maps F2-F8 keys to specific teammate slots for healing/buffing actions.

### 2.3 `EnemyState` (Combat Awareness)
- **Detailed Extraction**: When an enemy is targeted, the bot extracts:
    - **Rank**: (Minion, Lieutenant, Boss, Elite Boss, Archvillain).
    - **Level**: Absolute level of the target.
    - **Archetype**: (Blaster, Tanker, etc.) to prioritize targets.
- **Aggro Tracking**: Detects if an enemy is targeting the player (red border on nameplate).

---

## 3. Power Knowledge & Tracker
A bot is only as good as its understanding of its own toolbox.

### 3.1 `PowerSchema`
A static JSON/Python database containing:
- **Archetype Defaults**: Standard power sets (e.g., Empathy, Radiation Emission).
- **Power Metadata**:
    - `cooldown`: Internal timer before reuse.
    - `duration`: How long the buff/debuff lasts.
    - `type`: (Heal, Buff, Debuff, Attack, Toggle).
    - `target_type`: (Teammate, Enemy, Area).

### 3.2 `PowerTracker`
A runtime module that maintains a clock for each power:
- **Cooldown Timers**: Prevents sending inputs for powers not yet ready.
- **Uptime Tracking**: Knows exactly when "Clear Mind" or "Fortitude" was cast on Teammate #3 to schedule a recast before it expires.

---

## 4. Decision Engine (The "Brain")
The FSM will be replaced or augmented by a **Priority-Based Action Selector**.

### 4.1 Prioritization Logic
1. **Critical Recovery**: Heal self or teammate if HP < 25%.
2. **Buff Maintenance**: Recast essential defensive buffs on the team.
3. **Recovery**: Heal teammate if HP < 60%.
4. **Offense**: Use attack rotation on the current target.
5. **Efficiency**: Use "Rest" or conservation powers if endurance is low.

### 4.2 Behavioral Modes
- **Offensive**: Favor attacks and debuffs; heal only in emergencies.
- **Defensive**: Prioritize shields, heals, and status protection.
- **Conservation**: Disable high-cost toggles and use only low-endurance powers.

---

## 5. Implementation Roadmap

### Phase 1: Advanced Perception
- [ ] Implement Team Window anchor detection.
- [ ] Create multi-target health bar extraction logic.
- [ ] Implement rank/level OCR for enemy targets.

### Phase 2: Power System
- [ ] Build the `PowerSchema` database.
- [ ] Implement the `PowerTracker` clock system.
- [ ] Add "Recast" logic based on duration timers.

### Phase 3: Priority Engine
- [ ] Implement the `HealerState` in the FSM.
- [ ] Create the logic for cycling through teammates (F2-F8).
- [ ] Develop the "Operational Mode" configuration (Offensive/Defensive).

### Phase 4: Polish & Safety
- [ ] Add "Anti-stuck" logic (detecting if running into a wall).
- [ ] Implement logout safety (log out if health is extremely low and heals are on cooldown).
