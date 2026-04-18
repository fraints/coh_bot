# WindowDetector Implementation Plan

## 1. Goal
Design and implement a robust `WindowDetector` that can consistently locate the 6 primary City of Heroes UI windows. The detector will feed bounding boxes to specialized `DataExtractors` capable of reading health bars, endurance bars, and text.

## 2. Core Assumptions & Architecture
**Assumption**: *Once a window is found, it does not move.*
- **Optimization**: The `WindowDetector` will cache the `BoundingBox` for each window type once successfully discovered. On subsequent ticks, it will only try to detect windows that have not yet been framed (or have been explicitly invalidated by a state reset).

The system will rely heavily on:
- **Template Matching**: Anchoring off distinct UI elements (like borders or distinct buttons) that are structurally consistent.
- **Text-based Anchor Matching**: Locating the specific text buttons on the borders of windows to identify and orient the window boundary.
- **Bar Color Filtering**: Extracting metrics based on known bar shapes (rectangles with rounded edges) and color degradation logic.

## 3. Window Reference & Image Requirements

To accurately build and tune the detectors for the 6 primary windows, the following specific images and screenshots must be provided to feed the test runner. 

> **Important For All Windows**: Please provide at least 2 **full-screen captures** where the window is present in different locations or over different backgrounds to prove the detection is robust to scene variation. 

### 3.1 Player Bar
- **Characteristics**: Contains HP, Endurance, "special", and XP bars. Has an XP wheel and level number. Features text buttons: `Chat`, `Tray`, `Target`, `Nav`, `Menu`.
- **Location Strategy**: Anchor off the text buttons and the distinctive circular XP wheel.
- **Images Needed**:
  - Full-screen capture of the player bar.
  - Cropped templates of the `Chat Tray Target Nav Menu` text buttons.
  - Cropped templates of the XP circle/wheel at various states of fullness, including the level badge.
  - Screenshots of the player bar at Full HP (Green), Mid HP (Yellow), and Low HP (Red).
  - Screenshots depicting full and low Endurance (Blue/Purple to Black). 

### 3.2 Nav Window
- **Characteristics**: Compass, collapsible map. Features text buttons: `Map`, `Contact`, `Mission`, `Clues`, `Badges`.
- **Location Strategy**: Anchor off the compass ring and the bottom row of text buttons.
- **Images Needed**:
  - Full-screen capture.
  - Cropped templates of the text buttons.
  - Screenshots showing the Nav window both **collapsed** and **fully expanded** to handle height variations.
  - Cropped template of the compass perimeter.

### 3.3 Target Window
- **Characteristics**: Target name, `Actions` text button. Sometimes includes level, supergroup information, and HP/Endurance bars. 
- **Location Strategy**: Anchor off the `Actions` button and target UI borders. Fallback to name-plate text detection if needed.
- **Images Needed**:
  - Cropped template of the `Actions` text button.
  - High-res crops of Target windows *with* HP/End bars and *without* HP/End bars (e.g., targeting a teammate vs targeting an object or NPC).
  - Screenshots showing maximum layout variations (Target with supergroup text vs without).

### 3.4 Team Window
- **Characteristics**: List of teammates with per-player HP and Endurance bars. Sometimes has status icons to the right. 
- **Location Strategy**: Standardize anchor on the top title bar and/bottom frame, interpolating the dynamic height based on the player count (1 to 8).
- **Images Needed**:
  - Screenshots showing an active team window with 1 member, 4 members, and 8 members.
  - Cropped templates of the top of the team window and the bottom boundary.
  - Screenshots that *include* the status decos/buffs spreading to the right, to ensure the bounding box correctly limits horizontal bar extraction.
  - Sample crops of teammate bars at various degradation phases (Green → Yellow → Red → Black).

### 3.5 Chat Window
- **Characteristics**: Text panes with chat logs. Features text buttons: `Team`, `League`, `Friends`, `Super`, `Email`, `LFG`.
- **Location Strategy**: Anchor exclusively off the row of specific text buttons which clearly demarcate the top boundaries of the text pane.
- **Images Needed**:
  - Full-screen captures of the chat window.
  - Cropped templates of the specific text buttons (`Team`, `League`, etc.).
  - Screenshot of a multi-tabbed or split chat pane, if applicable, to understand sub-window framing.

### 3.6 Power Window
- **Characteristics**: Collection of circular powers. Features text buttons: `Powers`, `Inspirations`, `Enhance`, `Salvage`, `Recipes`, `+`. 
- **Location Strategy**: Anchor off the bottom/top row of text buttons and the `+` expansion button.
- **Images Needed**:
  - Cropped templates of the text buttons.
  - Screenshots showing a single tray, a double tray, and a triple tray to account for dynamically sized grids.
  - Close-up cropped templates of empty tray slots vs filled tray slots.

## 4. Bar Extraction Logic (Color Projection)
The `DataExtractor` modules attached to these windows will share a common `BarExtractor` utility obeying the following physical constraints:
- **Shape**: Rectangular or rectangular with slightly rounded corners. (Data extraction algorithms will inset by 2-3 pixels to avoid sampling rounded corners and borders).
- **Fill Depletion**: Fills from left to right. When HP or END decreases, the background (black) is revealed underneath on the right side.
- **Health (HP)**:
  - High: Green dominant.
  - Medium: Yellow/Orange dominant.
  - Low: Red dominant.
- **Endurance (End)**:
  - High to Low: Blue or Purple dominant degrading to Black.

**Algorithm Design**:
The exact filled percentage will be calculated by locating the horizontal pixel array for the bar's internal span, analyzing the dominant color, and finding the explicit boundary where the active color (Green/Yellow/Red for HP, Blue/Purple for END) sharply drops off and purely Black background pixels continue to the right margin.
