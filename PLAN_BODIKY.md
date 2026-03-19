╔═══════════════════════════════════════════════════════════════════════════════╗
║                    PLÁN DEVELOPMENT - BRANCH "BODIKY"                         ║
║               Points Canvas Integration + Interactive Editing                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📅 Datum: 18.3.2026
🎯 Cíl: Interaktivní editace vertebrálních bodů na X-ray obrázku
🏗️  Inspirace: GeoGebra-like controls (pan, zoom)

═══════════════════════════════════════════════════════════════════════════════

## ✅ FINÁLNÍ ODPOVĚDI NA OTÁZKY

1. BARVY BODŮ
   └─ Z points_panel.py:
      'TL': RGB(255, 192, 203)     # Pink
      'TR': RGB(144, 238, 144)     # Light Green
      'BL': RGB(173, 216, 230)     # Light Blue
      'BR': RGB(255, 255, 153)     # Light Yellow
      'C':  RGB(255, 200, 124)     # Light Orange
   → Extrahuji z existujícího kódu, přesunutí do config.py

2. MOVE CONSTRAINT
   └─ Canvas se vytvoří PŘESNĚ podle rozměrů snímku
   └─ Body nemůžou jít mimo obrázek (validace při move)
   └─ Canvas size = image.width × image.height (constant)

3. RESET BUTTON
   └─ Každý bod má vedle sebe tlačítko 🔄 Reset
   └─ Reset → vrátí bod na původní ML souřadnice
   └─ Implementace v VertebralPointsPanel

4. METRICS REALTIME
   └─ Počítají se okamžitě při každé změně souřadnic (myš, šipky)
   └─ Trigonometrie se vypočítá vždy když se bod posune
   └─ Zobrazení updated metrics live

5. SCALE/MAPPING
   └─ Canvas size = image size (pixel-perfect)
   └─ Souřadnice jsou vždy v originálním souř. systému obrázku
   └─ Žádná konverze potřeba (1:1 mapping)

═══════════════════════════════════════════════════════════════════════════════

## 🏗️ ARCHITEKTURA - FINÁLNÍ

SessionScreen (orchestrator)
│
├─ ImageCanvasPanel (NOVÝ - custom widget pro X-ray)
│  │
│  ├─ Canvas Widget (velikost = image.width × image.height)
│  │  ├─ QLabel s obrázkem (pozadí)
│  │  └─ PointsOverlay (custom QPainter - kreslení bodů)
│  │
│  ├─ Pan/Zoom Controls (GeoGebra-like)
│  │  ├─ Scroll wheel = zoom
│  │  ├─ Spacebar + drag = pan (move canvas)
│  │  ├─ Ctrl+Fit = auto-center v parent widget
│  │  └─ Current zoom % display
│  │
│  └─ Signals:
│     ├─ pointSelected(point_id)
│     ├─ pointMoved(point_id, x, y)
│     └─ metricsUpdated(metrics_dict) ← REALTIME!
│
├─ VertebralPointsPanel (UPDATED)
│  │
│  ├─ VertebralPointItem (upraven)
│  │  ├─ Barevný indikátor (TL/TR/BL/BR/C) - klikovatelný → select
│  │  ├─ Souřadnice (live updated z canvas)
│  │  ├─ Reset 🔄 tlačítko → restore ML coords
│  │  └─ Signal: pointSelected(point_id)
│  │
│  └─ Methods:
│     ├─ updateCoordinates(point_id, x, y) ← z canvas
│     └─ resetPoint(point_id) ← z UI
│
└─ State Management (v SessionScreen)
   ├─ self.vertebral_points: dict[id] = Point
   ├─ self.vertebral_points_original: dict[id] = Point (ML original)
   ├─ self.selected_point_id: str
   └─ onPointSelected(), onPointMoved(), onResetPoint()

═══════════════════════════════════════════════════════════════════════════════

## 📋 DETAILNÍ FEATURE LIST - PHASE BY PHASE

### PHASE 1: Canvas Setup + Rendering (3 dny)

─────────────────────────────────────────────

1.1 Vytvoř ImageCanvasPanel
    - [ ] Custom QWidget s:
      - [ ] Canvas area (velikost = image.size)
      - [ ] QLabel background (image)
      - [ ] PointsOverlay (custom QPainter)
    - [ ] Auto-center v parent widget
    - [ ] Zoom control (Ctrl+Scroll)
    - [ ] Pan control (Spacebar + drag / middle-mouse)

1.2 Implementuj PointsOverlay
    - [ ] paintEvent():
      - [ ] Nakresli všechny body jako malé kroužky
      - [ ] Barva = z configu (TL/TR/BL/BR/C)
      - [ ] Diameter = 4px (malé, ale viditelné)
      - [ ] Optional: labels (config: SHOW_POINT_LABELS)
    - [ ] mousePressEvent():
      - [ ] Detekuj klik na bod (hitbox radius = 8px)
      - [ ] Emit: pointSelected(point_id)
    - [ ] keyPressEvent():
      - [ ] Zatím placeholder (Phase 3)

1.3 Config.py - Color Map
    - [ ] POINT_COLORS = dict[abbr] → QColor
    - [ ] POINT_RADIUS = 2 (5px diameter)
    - [ ] POINT_SELECTED_RADIUS = 4 (8px diameter, když selected)
    - [ ] POINT_CLICK_RADIUS = 5 (10px hitbox)
    - [ ] SHOW_POINT_LABELS = True/False
    - [ ] RESTRICT_SELECTION_TO_TABLE = True
    - [ ] ARROW_KEY_STEP = 1
    - [ ] ARROW_KEY_STEP_SHIFT = 5

1.4 SessionScreen integration
    - [ ] Přidej ImageCanvasPanel do layoutu
    - [ ] Connect signals: pointSelected → VertebralPointsPanel highlight

### PHASE 2: Point Selection + Highlighting (2 dny)

────────────────────────────────────────────────

2.1 VertebralPointsPanel UPDATE
    - [ ] VertebralPointItem:
      - [ ] Barevný indikátor je KLIKOVATELNÝ
      - [ ] onClicked → emit pointSelected(point_id)
      - [ ] Highlight když je selected (bold text, border)
    - [ ] Zkontroluj: points_panel.py umožňuje select?

2.2 ImageCanvasPanel - Highlight
    - [ ] PointsOverlay.paintEvent() změna:
      - [ ] If point_id == selected_point_id:
        - [ ] Radius = POINT_SELECTED_RADIUS
        - [ ] Color = bright version (e.g., brighter, white outline)
        - [ ] Draw selection indicator (obrys / halo)

2.3 State Management
    - [ ] SessionScreen.selected_point_id: str
    - [ ] onPointSelected(point_id): update canvas + table

### PHASE 3: Point Editing (3 dny)

─────────────────────────────────

3.1 Mouse Drag-Drop
    - [ ] PointsOverlay.mouseMoveEvent():
      - [ ] If selected_point_id and mouse pressed:
        - [ ] Compute new coords from mouse position
        - [ ] Check bounds (must be within image)
        - [ ] Update Point in data model
        - [ ] Emit: pointMoved(point_id, x, y)
        - [ ] Trigger repaint
    - [ ] PointsOverlay.mouseReleaseEvent():
      - [ ] Finalize move
      - [ ] Store in state

3.2 Arrow Keys (Precise Placement)
    - [ ] PointsOverlay.keyPressEvent():
      - [ ] If selected_point_id:
        - [ ] Up/Down → y -= ARROW_KEY_STEP
        - [ ] Left/Right → x ± ARROW_KEY_STEP
        - [ ] Shift+arrows → 5x step
        - [ ] Check bounds before apply
        - [ ] Emit: pointMoved()
        - [ ] Repaint

3.3 VertebralPointsPanel SYNC
    - [ ] onPointMoved(point_id, x, y):
      - [ ] Update Point in self.vertebral_points
      - [ ] Update display in table (live)
      - [ ] Call updateCoordinates() in VertebralPointItem

3.4 Reset Button
    - [ ] VertebralPointItem:
      - [ ] Přidej 🔄 Reset tlačítko
      - [ ] onClick → emit pointReset(point_id)
    - [ ] SessionScreen.onResetPoint(point_id):
      - [ ] point = self.vertebral_points_original[point_id]
      - [ ] self.vertebral_points[point_id].x = point.x
      - [ ] self.vertebral_points[point_id].y = point.y
      - [ ] Emit: pointMoved() → update canvas
      - [ ] Update table

### PHASE 4: Metrics Integration (2 dny)

─────────────────────────────────────

4.1 Metrics Realtime Calculation
    - [ ] Nový modul: core/metrics/vertebra_metrics.py
      - [ ] def calculate_cervical_metrics(points: dict) → dict
      - [ ] Trigonometric calculations (distances, angles)
      - [ ] Return: {metric_name: value, ...}

4.2 SessionScreen Integration
    - [ ] onPointMoved():
      - [ ] Po každé změně souřadnic:
        - [ ] Compute: metrics = calculate_cervical_metrics(...)
        - [ ] Emit: metricsUpdated(metrics)
        - [ ] Display v MetricsPanel (placeholder na data)

4.3 MetricsPanel Display
    - [ ] Zatím: Text label s metrikami (simple)
    - [ ] Format: "Metric Name: Value Unit"
    - [ ] Live update jako se body pohybují

═══════════════════════════════════════════════════════════════════════════════

## 🛠️ KOMPONENTY K VYTVOŘENÍ

### Nové soubory

1. ui/panels/image_canvas_panel.py (NOVÝ)
   ├─ class ImageCanvasPanel(QWidget)
   ├─ class PointsOverlay(QWidget)
   └─ class CanvasTransform(helper)
   [~400 řádků]

2. core/graphics/point_painter.py (NOVÝ)
   ├─ def draw_point(painter, x, y, color, radius, selected=False)
   ├─ def draw_label(painter, x, y, label)
   └─ def get_color_from_config(abbreviation)
   [~100 řádků]

3. core/metrics/vertebra_metrics.py (NOVÝ)
   ├─ def calculate_cervical_metrics(points_dict) → dict
   ├─ def calculate_distance(p1, p2) → float
   ├─ def calculate_angle(p1, p2, p3) → float
   └─ [helpers]
   [~200 řádků]

### Úpravované soubory

1. config.py
   ├─ + POINT_COLORS (dict)
   ├─ + POINT_RADIUS
   ├─ + POINT_SELECTED_RADIUS
   ├─ + POINT_CLICK_RADIUS
   ├─ + SHOW_POINT_LABELS
   ├─ + RESTRICT_SELECTION_TO_TABLE
   ├─ + ARROW_KEY_STEP
   └─ + ARROW_KEY_STEP_SHIFT

2. ui/session_screen.py
   ├─ + Import ImageCanvasPanel
   ├─ + Add ImageCanvasPanel to layout
   ├─ + State: selected_point_id, vertebral_points_original
   ├─ + Methods: onPointSelected, onPointMoved, onResetPoint
   └─ + Metrics calculation integration

3. ui/panels/points_panel.py
   ├─ VertebralPointItem:
   │  ├─ + Clickable indicator (select)
   │  ├─ + Reset 🔄 button
   │  ├─ + updateCoordinates() method
   │  └─ + pointSelected, pointReset signals
   └─ VertebralPointsPanel:
      └─ + resetPoint(point_id) method

4. core/models/data_structures.py
   ├─ Point: (existuje, no change)
   └─ VertebralPoints: (existuje, no change)

═══════════════════════════════════════════════════════════════════════════════

## 📊 SIGNALS/SLOTS MAP

ImageCanvasPanel
├─ Signal: pointSelected(point_id: str)
├─ Signal: pointMoved(point_id: str, x: float, y: float)
├─ Signal: metricsUpdated(metrics: dict)
└─ Slot: highlight(point_id: str)

VertebralPointsPanel
├─ Signal: pointSelected(point_id: str)
├─ Signal: resetPointRequested(point_id: str)
└─ Slot: updateCoordinates(point_id: str, x: float, y: float)

SessionScreen (orchestrator)
├─ onPointSelected(point_id) → update canvas + table
├─ onPointMoved(point_id, x, y) → calc metrics, update UI
├─ onResetPoint(point_id) → restore ML coords, update all
└─ onMetricsUpdated(metrics) → display metrics

═══════════════════════════════════════════════════════════════════════════════

## 🎮 USER INTERACTIONS

1. Load image + ML detection
   └─ SessionScreen displays data

2. Výběr bodu
   ├─ Klik na bod v tabulce (VertebralPointsPanel)
   │  └─ Canvas: bod se zvýrazní
   ├─ (Optional) Klik na bod v obrázku
   │  └─ Tabulka: select řádek s bodem

3. Editace bodu
   ├─ Drag-drop v obrázku
   │  └─ Tabulka + metrics se update live
   ├─ Šipky
   │  ├─ Arrow keys (1px step)
   │  └─ Shift+arrows (5px step)
   └─ Bounds check: bod zůstane v obrázku

4. Reset bodu
   └─ Click 🔄 v tabulce → vrátí na ML coords

5. Metrics display
   └─ Live update když se bod posune (realtime trigon)

═══════════════════════════════════════════════════════════════════════════════

## 📈 TIMELINE

Phase 1 (Canvas + Rendering)      → 3 dny
Phase 2 (Selection + Highlight)   → 2 dny
Phase 3 (Editing: mouse + keys)   → 3 dny
Phase 4 (Metrics + Integration)   → 2 dny
Testing + Polish + Bug fixes      → 2 dny
────────────────────────────────────────
CELKEM                            → ~12 dní

═══════════════════════════════════════════════════════════════════════════════

## ✅ READY TO START?

Máme finální plán. Chceš ať spustím s:

[ ] Phase 1.1 - ImageCanvasPanel basic structure
[ ] Phase 1.2 - PointsOverlay + painting
[ ] Něco jiného?

Kontrola: Máš ještě nějakou otázku/změnu PŘED než začnu kódovat?

═══════════════════════════════════════════════════════════════════════════════
