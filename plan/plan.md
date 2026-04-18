# City of Heroes Bot — Development Plan

## 1. Overview

An automation bot for City of Heroes that:

1. **Perceives** — reads game state from screen captures and log files
2. **Tracks state** — maintains a world model (player, target, team, powers)
3. **Decides** — selects actions based on state, character archetype, and operational mode
4. **Acts** — sends key presses, clicks, and slash commands to the game

Every core component is **pluggable**: defined by an interface (Protocol / ABC) so implementations can be swapped without touching the rest of the system.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│          tick loop · wiring · signal handling            │
└──────────┬──────────────────────────────────┬───────────┘
           │                                  │
     ┌─────▼─────┐                     ┌──────▼──────┐
     │ Perception │                     │   Actions   │
     │  (inputs)  │                     │  (outputs)  │
     └─────┬──────┘                     └──────▲──────┘
           │  GameState                        │ Action
     ┌─────▼──────────────────────────────────▼──────┐
     │                    Brain                       │
     │  ┌────────────┐  ┌───────────┐  ┌───────────┐ │
     │  │ WorldModel  │  │  Decision │  │  CharSpec │ │
     │  │ (state)     │──│  Engine   │──│ (archetype│ │
     │  └────────────┘  └───────────┘  │  + powers)│ │
     │                                  └───────────┘ │
     └────────────────────────────────────────────────┘
```

### 2.1 Pluggable Interfaces

Each major component is behind a **Protocol** so implementations can be swapped independently.

| Interface | Example Impls | Purpose |
|---|---|---|
| `PerceptionSource` | `ScreenReader` | Produces a `GameState` snapshot |
| `WindowDetector` | `TemplateDetector`, `ColorPatternDetector`, `TextDetector`, `CompositeDetector` | Locates UI windows in a screenshot |
| `DataExtractor` | `ColorBarExtractor`, `TextExtractor` | Extracts data (HP %, name, etc.) from a located window region |
| `LogReader` | *(future)* | Tails the game log and emits structured events |
| `DecisionEngine` | `PriorityDecisionEngine` | Given world model, returns ordered list of actions |
| `ActionExecutor` | `InputHandler` | Sends inputs to the game (key press, click, slash command) |

---

## 3. Component Details

### 3.1 Perception Layer

The perception layer produces a `GameState` each tick. It is composed of sub-components:

#### 3.1.1 Screen Capture Pipeline

```
Full Screenshot
    │
    ├─► WindowDetector.detect(screenshot) → dict[WindowKind, BoundingBox]
    │       Locates each known window type (Player, Target, Team, Powers, Chat)
    │       The WindowDetector is entirely pluggable. Active implementations could include:
    │         • TemplateDetector: uses image templates of anchors (title bars, edges).
    │         • ColorPatternDetector: searches for specific background pixel ratios.
    │         • TextDetector: uses pixel-text analysis or OCR to find labels.
    │         • CompositeDetector: uses a combination of the above for robustness.
    │
    └─► DataExtractor.extract(window_region, window_kind) → WindowData
            Per-window extraction logic:
              • Player frame  → hp_pct, end_pct, name, level
              • Target frame  → hp_pct, end_pct, name, rank, level
              • Team window   → list[TeamMember(hp_pct, end_pct, is_alive, is_in_range)]
              • Power tray    → list[PowerSlot(is_available, is_recharging)]
```

**Key points:**
- `WindowDetector` uses template images of window chrome (title bars, edge decorations) to find windows regardless of position.
- Extraction uses color-projection (e.g. summing green-channel columns for HP bars) and is resolution-aware.
- The user will supply example screenshots and cropped reference images to calibrate detection.

#### 3.1.2 Log File Reader *(Phase 3+)*

- Tails the game's combat log file.
- Parses lines into structured events: `DamageEvent`, `HealEvent`, `BuffEvent`, `DefeatedEvent`.
- Feeds events into the `WorldModel` alongside screen-based perception.

#### 3.1.3 GameState

```python
@dataclass
class GameState:
    player: PlayerState        # hp, end, name, level
    target: TargetState | None # hp, end, name, rank, archetype
    team: list[TeamMember]     # up to 8 members
    powers: list[PowerSlot]    # tray slots and availability
    windows_detected: dict[WindowKind, BoundingBox]
    timestamp: float
```

### 3.2 World Model (State Tracking)

Sits in the Brain layer. Accumulates `GameState` snapshots over time and tracks derived state:

- **Player HP/End trends** — rising, falling, stable
- **Target persistence** — same target over multiple ticks, target swaps
- **Team member status** — who needs healing, who is dead, who is out of range
- **Power cooldowns** — tracks when each power was last used
- **Buff timers** — tracks active buff durations on self and team

```python
class WorldModel:
    def update(self, game_state: GameState) -> None: ...
    @property
    def player(self) -> PlayerModel: ...
    @property  
    def target(self) -> TargetModel | None: ...
    @property
    def team(self) -> TeamModel: ...
    @property
    def power_tracker(self) -> PowerTracker: ...
```

### 3.3 Character Specification

Defines the character's archetype and available powers. Loaded from config/YAML.

```python
@dataclass
class CharacterSpec:
    name: str
    archetype: Archetype          # Defender, Blaster, Controller, etc.
    primary_powerset: str         # e.g. "Empathy", "Radiation Emission"
    secondary_powerset: str       # e.g. "Dark Blast", "Force Field"
    powers: list[PowerDef]        # name, slot, recharge_time, type, target

@dataclass
class PowerDef:
    name: str
    slot: str                     # keybind or tray position
    recharge_seconds: float
    power_type: PowerType         # HEAL, BUFF, ATTACK, DEBUFF, CC, TOGGLE
    target: TargetType            # SELF, SINGLE_ALLY, AOE_ALLY, SINGLE_ENEMY, AOE_ENEMY
    priority: int                 # base priority for the decision engine
```

### 3.4 Decision Engine

Chooses which action to perform each tick. Core loop:

1. Gather candidate actions from all available powers
2. Filter by availability (not on cooldown, valid target exists)
3. Score each candidate based on:
   - Base priority from `PowerDef`
   - Current operational **mode** modifiers
   - Urgency signals (e.g. teammate at 20% HP → heal priority spikes)
4. Return the highest-scoring action

#### Operational Modes

| Mode | Behavior |
|---|---|
| `OFFENSIVE` | Prioritize attack powers, aggressive targeting |
| `DEFENSIVE` | Prioritize heals and buffs, avoid pulling aggro |
| `CONSERVE_POWER` | Minimize endurance usage, use only efficient powers |
| `FOLLOW` | Stay near the team leader, minimal autonomous actions |
| `REST` | Disengage and recover HP/End |

Modes can be set manually (keybind or config) or auto-switched by the decision engine (e.g. low endurance → `CONSERVE_POWER`).

### 3.5 Action Executor

Translates high-level action decisions into game inputs:

| Action | Implementation |
|---|---|
| Use power on slot `3` | `press_key("3")` |
| Target team member 4 | Slash command or keybind |
| Target nearest enemy | `press_key("tab")` |
| Follow leader | Slash command `/follow <leader>` |
| Send slash command | Type into chat: `Enter` → type text → `Enter` |

The current `InputHandler` (pynput-based) handles all of this. Future: support for direct game-client command injection if available.

---

## 4. Directory Structure (Target)

```
coh_bot2/
├── main.py
├── config.py
├── plan.md                              ← this file
├── requirements.txt
├── character_specs/                     ← YAML character definitions
│   └── empathy_defender.yaml
├── bot/
│   ├── __init__.py
│   ├── types.py                         ← shared types, enums, protocols
│   ├── perception/
│   │   ├── __init__.py
│   │   ├── protocols.py                 ← PerceptionSource, WindowDetector, DataExtractor
│   │   ├── screen_reader.py             ← main screen-based PerceptionSource impl
│   │   ├── window_detector.py           ← template-matching window finder
│   │   ├── extractors/
│   │   │   ├── __init__.py
│   │   │   ├── player_frame.py          ← extract player HP/End/Name
│   │   │   ├── target_frame.py          ← extract target HP/End/Name/Rank
│   │   │   ├── team_window.py           ← extract team member statuses
│   │   │   └── power_tray.py            ← extract power availability
│   │   ├── log_reader.py                ← (Phase 3) combat log parser
│   │   └── templates/                   ← reference images for matching
│   │       ├── player_frame_anchor.png
│   │       ├── target_frame_anchor.png
│   │       ├── team_window_top.png
│   │       ├── team_window_bottom.png
│   │       └── ...
│   ├── brain/
│   │   ├── __init__.py
│   │   ├── world_model.py               ← stateful world model
│   │   ├── decision_engine.py            ← priority-based action selection
│   │   ├── character_spec.py             ← CharacterSpec + PowerDef loader
│   │   ├── power_tracker.py              ← cooldown and buff tracking
│   │   ├── fsm.py                        ← FSM engine (existing)
│   │   └── states.py                     ← concrete states (existing, to be extended)
│   └── actions/
│       ├── __init__.py
│       ├── protocols.py                  ← ActionExecutor protocol
│       └── input_handler.py              ← pynput-based impl (existing)
├── tests/
│   ├── screenshots/                      ← reference screenshots for testing
│   ├── test_perception.py
│   ├── test_fsm.py
│   ├── test_window_detector.py
│   ├── test_extractors.py
│   ├── test_decision_engine.py
│   └── test_world_model.py
└── tools/
    ├── calibrate.py                      ← interactive tool: clicks on screen, saves coordinates
    └── snapshot_debug.py                 ← captures screenshot, runs perception, shows annotated output
```

---

## 5. Development Phases

### Phase 1 — Screen Perception Foundation ◄ START HERE

**Goal:** Reliably detect and extract data from the Player frame, Target frame, and Team window using screenshot input.

| # | Task | Details |
|---|---|---|
| 1.1 | Define Protocols | Create `PerceptionSource`, `WindowDetector`, `DataExtractor` in `bot/perception/protocols.py` |
| 1.2 | Implement `WindowDetector` | Template-based detection for Player, Target, and Team windows. User provides reference images. |
| 1.3 | Player Frame Extractor | Extract HP %, Endurance %, name from the player frame region |
| 1.4 | Target Frame Extractor | Extract HP %, Endurance %, name, rank from the target frame region |
| 1.5 | Team Window Extractor | Extract per-member HP %, Endurance %, alive status for up to 8 members |
| 1.6 | Integrate into `ScreenReader` | Wire detectors + extractors into the existing `ScreenReader.capture()` pipeline |
| 1.7 | Tests | Unit tests with static screenshots for each extractor; parametrized across the existing screenshot corpus |
| 1.8 | Debug tooling | `snapshot_debug.py` — captures live screenshot, runs full perception, draws annotated bounding boxes and extracted values |

**Deliverable:** `ScreenReader.capture()` returns a rich `GameState` with accurate player/target/team data, verified against real screenshots.

---

### Phase 2 — World Model & Character Spec

**Goal:** Build the stateful brain that tracks game state over time and knows the character's powers.

| # | Task | Details |
|---|---|---|
| 2.1 | `WorldModel` class | Accumulates `GameState` snapshots; exposes trending data (HP rising/falling) and team status |
| 2.2 | `CharacterSpec` + YAML loader | Define the data model for archetypes and powers; load from YAML files |
| 2.3 | `PowerTracker` | Track cooldowns and active buff durations per power |
| 2.4 | Wire into main loop | `main.py` creates `WorldModel`, updates it each tick |
| 2.5 | Tests | Unit tests for world model state tracking, power cooldown logic |

**Deliverable:** The bot maintains a running model of the game world that persists across ticks.

---

### Phase 3 — Decision Engine & Operational Modes

**Goal:** Replace the static FSM state logic with a flexible, priority-based decision engine.

| # | Task | Details |
|---|---|---|
| 3.1 | `DecisionEngine` | Priority-based action scorer; filters by availability, scores by urgency + mode |
| 3.2 | Operational modes | Implement OFFENSIVE, DEFENSIVE, CONSERVE_POWER, FOLLOW, REST modes |
| 3.3 | Mode transitions | Auto-transition rules (e.g. low End → CONSERVE, low team HP → DEFENSIVE) |
| 3.4 | FSM integration | States delegate action choice to `DecisionEngine`; FSM handles high-level mode (in-combat vs idle) |
| 3.5 | Tests | Unit tests for decision scoring under various world states and modes |

**Deliverable:** Bot makes intelligent, context-aware decisions about which power to use each tick.

---

### Phase 4 — Log File Input & Advanced Perception

**Goal:** Add combat log parsing as a second input source; improve perception accuracy.

| # | Task | Details |
|---|---|---|
| 4.1 | `LogReader` | Tail the game log file; parse into structured events |
| 4.2 | Event types | `DamageEvent`, `HealEvent`, `BuffEvent`, `DefeatedEvent`, `XPEvent` |
| 4.3 | Fuse with screen data | `WorldModel` accepts both screen snapshots and log events |
| 4.4 | Power tray detection | Read power tray to detect recharge state, greyed-out powers |
| 4.5 | Tests | Unit tests for log parsing; integration test combining log + screen data |

**Deliverable:** Dual-input perception gives the bot richer, more reliable state information.

---

### Phase 5 — Polish & Robustness

| # | Task | Details |
|---|---|---|
| 5.1 | Error recovery | Handle lost windows, game minimized, loading screens gracefully |
| 5.2 | Calibration tool | Interactive `calibrate.py` to help users set up templates for their resolution/UI layout |
| 5.3 | Dashboard/overlay | Optional: real-time terminal dashboard showing bot state, decisions, and perception data |
| 5.4 | Multiple archetype support | Test and tune decision engine for Defender, Controller, Blaster, Tanker |
| 5.5 | Configuration UI | Simple config file or TUI for setting mode, swapping character spec, etc. |

---

## 6. Current Status (What Already Exists)

| Component | Status | Notes |
|---|---|---|
| `screen_reader.py` | ✅ Basic | Color-based HP bar parsing, template matching support, basic target/enemy detection |
| `fsm.py` | ✅ Working | Clean FSM engine with enter/tick/exit lifecycle |
| `states.py` | ✅ Basic | IdleState → ScanState → CombatState → LowHealthState flow |
| `input_handler.py` | ✅ Working | pynput-based key press, keybind resolution, chord support |
| `config.py` | ✅ Basic | Timing, regions, keybinds, combat thresholds |
| `test_fsm.py` | ✅ Passing | FSM engine + state transition tests |
| `test_perception.py` | ✅ Passing | HP bar, target detection, enemy detection tests |
| Screenshots | ✅ 16 files | Various game states: targets, team windows, HP levels |

---

## 7. Development Workflow

1. **Start from screenshots.** For each new window/extractor, the user provides:
   - Full game screenshots showing the window
   - Cropped images of the window's anchor points (title bar, edges)
   - Any metadata (what the values should be in that screenshot)

2. **Write the extractor.** Implement detection + extraction logic using the reference images.

3. **Test against the screenshot corpus.** Run `pytest` against all provided screenshots to verify accuracy.

4. **Iterate.** When extraction fails on a new screenshot, fix the algorithm and add the screenshot to the test corpus.

5. **Integration.** Once an extractor is solid, wire it into `ScreenReader` and verify the full pipeline.

---

## 8. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Protocols over inheritance** | Swap implementations without changing consumers (e.g. mock perception for testing) |
| **YAML character specs** | Easy to edit without code changes; supports multiple characters |
| **Priority-based decisions over hard-coded FSM logic** | More flexible, handles complex multi-role scenarios (heal + buff + attack) |
| **Screen capture as primary input** | Works regardless of game client modifications; log parsing supplements but doesn't replace |
| **Dedicated extractors per window type** | Each window has unique layout rules; isolating logic keeps extractors testable |
| **Debug tooling from day one** | `snapshot_debug.py` makes it easy to diagnose perception issues visually |
