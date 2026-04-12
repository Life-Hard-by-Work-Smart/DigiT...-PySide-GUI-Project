# 🎯 ML Model Integration Plan - DigiTech Spiner

**Verze:** 1.0
**Datum:** Duben 12, 2026
**Status:** 📋 Implementační plán (ready for execution)

---

## 📑 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Design Philosophy](#design-philosophy)
4. [Proposed Architecture](#proposed-architecture)
5. [Threading & Multi-Session Strategy](#threading--multi-session-strategy)
6. [File Structure & Organization](#file-structure--organization)
7. [Implementation Phases](#implementation-phases)
8. [Critical Issues & Solutions](#critical-issues--solutions)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [Checklist & Milestones](#checklist--milestones)

---

## Executive Summary

Cílem je integrovat UNet model (Atlas) do GUI aplikace tak, aby:

✅ **Víc modelů** bylo jednoduchě přidávatelných (Preview model + UNet model + dalších X)
✅ **UI nefreeznul** když běží inference (multi-threading s QThread)
✅ **Sessions běžely paralelně** - každá na svém vlákně, UI na hlavním vláknu
✅ **Modely byly odděleny** - interface `BaseMLInference` pro interoperabilitu
✅ **Konfigurace byla flexibilní** - per-model settings, global fallback (každý model má vlastní kofiguraci, cokoliv co budeme přidávat v ohledu na konfiguraci musí být odděleně konzultováno pro zachování funkčnosti MLs)
✅ **Vývojáři mohli jednoduše přidávat** nové modely (template + registry)

---

## Current State Analysis

### ✅ Existující Components

```
core/models/
├── base_inference.py          # ✅ Dobrý abstraktní interface
├── ML_inference.py            # ✅ Simulator implementace
├── data_structures.py         # ✅ Point, VertebralPoints
└── __init__.py               # ✅ Export

core/io/
├── ML_output_handler.py       # ✅ JSON parsing
└── __init__.py               # ✅ Export

ui/session_screen.py           # ⚠️ Synchronní inference - PROBLÉM!
ui/main_window.py              # ✅ Tab management OK
config.py                      # ✅ AVAILABLE_MODELS already exists!
```

### ⚠️ Problémy v Current Stavu

| Problém | Vliv | Řešení |
|---------|------|--------|
| **Synchronní inference** | UI freezuje na 10-30s | QThread worker pro inference |
| **Hardcoded model jména** | Těžké přidat modely | Model registry + dynamic loading |
| **Žádný model state mgmt** | Možné memory leaky | Model lifecycle management |
| **Model init na request** | Pomalý start | Lazy loading OR singleton per session |
| **Nákl. threading** | Multi-session freeze | Worker pool pattern |

---

## Design Philosophy

### Principy

1. **Separation of Concerns** → UI thread ≠ ML thread
2. **Pluggable Models** → Jednoduché přidání nového modelu bez změny UI
3. **Lazy Loading** → Model se naloaduje až když je potřeba (ušetří RAM)
4. **Per-Session Instances** → Každá session má vlastní model instance (thread-safety)
5. **Graceful Degradation** → Když selže inference, aplikace nekrashuje
6. **Configuration as Code** → Models config v `models.config.json` nebo `core/models/registry.py`

---

## Proposed Architecture

### 1. Model Registry System

**Cíl:** Centrální místo kde se zjistí "jaké modely máme k dispozici"

#### Varianta: `core/models/registry.py` (DOPORUČENÁ)

```python
"""
registry.py - Centrální model registry
Umožní dynamic loading modelů bez hardcodingu
"""

from typing import Dict, Type
from core.models.base_inference import BaseMLInference

class ModelRegistry:
    _models: Dict[str, Type[BaseMLInference]] = {}

    @classmethod
    def register(cls, name: str, model_class: Type[BaseMLInference]):
        """Zaregistruj model"""
        cls._models[name] = model_class

    @classmethod
    def get_available_models(cls) -> List[Dict]:
        """Vrátí seznam dostupných modelů s metadaty"""
        return [
            {"name": name, "class": cls._models[name]}
            for name in cls._models
        ]

    @classmethod
    def create_instance(cls, name: str) -> BaseMLInference:
        """Vytvoř instanci modelu"""
        if name not in cls._models:
            raise ValueError(f"Model '{name}' není zaregistrován")
        return cls._models[name]()

# Auto-registrace při importu
from core.models.preview import PreviewModel
from core.models.atlas_unet import AtlasUNetModel

ModelRegistry.register("preview", PreviewModel)
ModelRegistry.register("atlas_unet", AtlasUNetModel)
```

**Výhody:**

- Centrální control
- Žádný hardcoding stringů
- Snadný testing (mock registry)
- Snadné přidání/odebrání modelů

---

### 2. Model Folder Structure

**VARIANTA A DOPORUČENÁ - Po modelech:**

```
core/
├── models/
│   ├── __init__.py
│   ├── base_inference.py           # Abstraktní interface
│   ├── data_structures.py          # Point, VertebralPoints
│   ├── registry.py                 # Model registry (NEW)
│   │
│   ├── preview/
│   │   ├── __init__.py
│   │   ├── preview_model.py        # Simulátor (renamed z ML_inference.py)
│   │   └── config.py               # Per-model config
│   │
│   └── atlas_unet/
│       ├── __init__.py
│       ├── atlas_model.py          # Main inference wrapper (NEW)
│       ├── config.py               # UNet-specific config (NEW)
│       ├── preprocessing.py        # Histogram equalization etc (copied z toBeIntegrated)
│       ├── postprocessing.py       # Morphological ops (copied)
│       ├── keypoint_extraction.py  # Body extraction (copied z toBeIntegrated)
│       └── weights/
│           └── atlas-model-final.pth
│
└── io/
    ├── __init__.py
    └── ML_output_handler.py        # Zůstane stejný
```

**Proč tato struktura?**

✅ **Scalability** - Každý model má svou složku se vším potřebným
✅ **Isolation** - Konflikty mezi modely jsou nemožné (separate imports)
✅ **Clarity** - Jasně vidíš co patří k jakému modelu
✅ **Testing** - Snadné mockovat jednotlivé modely
✅ **Maintenance** - Když model havaruje, ostatní jsou v pořádku

---

### 3. Threading Strategy - KLÍČOVÁ ČÁST

**Problém:** `on_inference_clicked()` je synchronní → UI freezuje

**Řešení:** QThread worker pattern pro inference

#### Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN UI THREAD                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SessionScreen (QWidget)                              │   │
│  │  - Canvas, VertebralPointsPanel, Buttons             │   │
│  │  - SIGNALS: inference_finished, progress_update      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
              ▲                        │
              │                        │ emit inference_clicked
              │ emit inference_finished
              │                        ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKGROUND WORKER THREAD (per Session)          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  InferenceWorker(QThread)                             │   │
│  │  - Drží svou instanci modelu                         │   │
│  │  - Spouští: model.predict(image_path)               │   │
│  │  - Parsuje: InferenceOutputHandler                   │   │
│  │  - Emituje: resultReady signal s VertebralPoints    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### Implementace `InferenceWorker`

```python
# core/workers/inference_worker.py (NEW FILE)

from PySide6.QtCore import QThread, Signal
from typing import Optional, Dict, Any
from core.models.base_inference import BaseMLInference
from core.models.data_structures import VertebralPoints
from core.io import InferenceOutputHandler
from logger import logger

class InferenceWorker(QThread):
    """Worker thread pro inference - běží v backgroundu"""

    # Signals - komunikace s UI threadem
    resultReady = Signal(list)  # list[VertebralPoints]
    progressUpdate = Signal(str)  # "Loading model..." atd
    errorOccurred = Signal(str)  # "Model failed: ..."

    def __init__(self, model: BaseMLInference, image_path: str):
        super().__init__()
        self.model = model
        self.image_path = image_path
        self.io_handler = InferenceOutputHandler()

    def run(self):
        """Spustí se v background threadu"""
        try:
            self.progressUpdate.emit("🔄 Načítám model...")

            # Spusti inference - může trvat 10-30s
            logger.info(f"[WORKER] Inference spuštěna: {self.image_path}")
            inference_json = self.model.predict(self.image_path)

            if not inference_json:
                self.errorOccurred.emit("Model vrátil prázdný výstup")
                return

            self.progressUpdate.emit("✓ Inference hotova, parsuju výsledky...")

            # Parsuj JSON do VertebralPoints objektů
            vertebral_results = self.io_handler.parse_inference_output(inference_json)

            if not vertebral_results:
                self.errorOccurred.emit("Parsing vrátil prázdný seznam bodů")
                return

            # Emit resultu - bude zachyceno v UI threadu
            self.resultReady.emit(vertebral_results)
            logger.info(f"[WORKER] Inference HOTOVA - {len(vertebral_results)} bodů")

        except Exception as e:
            logger.error(f"[WORKER] Chyba: {e}")
            self.errorOccurred.emit(f"Chyba při inference: {str(e)}")
```

#### Použití v SessionScreen

```python
# core/workers/__init__.py (NEW)
from core.workers.inference_worker import InferenceWorker

__all__ = ['InferenceWorker']

# ui/session_screen.py - UPRAVIT on_inference_clicked:

def on_inference_clicked(self):
    """Spusť ML inference v background threadu"""
    if not self.image_confirmed or not self.current_image_path:
        logger.warning(f"[Session {self.session_name}] Chyba: snímek není potvrzen")
        return

    try:
        # ✅ NOVÝ KÓD - Vytvoř worker thread
        self.inference_worker = InferenceWorker(
            model=self.ml_inference,
            image_path=self.current_image_path
        )

        # Připoj signaly
        self.inference_worker.resultReady.connect(self._on_inference_ready)
        self.inference_worker.errorOccurred.connect(self._on_inference_error)
        self.inference_worker.progressUpdate.connect(self._on_progress_update)

        # Zakáž inference button (zabran duplicitním spuštěním)
        self.inference_button.setEnabled(False)
        self.inference_button.setText("⏳ Inference běží...")

        # Spusť worker
        self.inference_worker.start()
        logger.info(f"[Session {self.session_name}] Inference worker spuštěn")

    except Exception as e:
        logger.error(f"[Session {self.session_name}] Chyba při spuštění workeru: {e}")
        self._on_inference_error(str(e))

def _on_inference_ready(self, vertebral_results: list):
    """Callback když je inference hotova - MAIN THREAD"""
    logger.info(f"[Session {self.session_name}] Inference skončila - {len(vertebral_results)} bodů")

    # Ulož výsledky
    current_model = self.model_combo.currentText()
    self.inference_results_by_model[current_model] = vertebral_results

    # Aktualizuj UI
    if self.current_pixmap:
        self.canvas_panel.set_image(self.current_pixmap)
        self.canvas_panel.set_vertebral_points(vertebral_results)
        self.canvas_panel.set_point_colors(POINT_COLORS)  # nebo MODEL_2

    self.vertebral_panel.set_vertebral_data(vertebral_results)

    # UI state
    self.inference_completed = True
    self.menu_buttons["Body"].setEnabled(True)
    self.inference_button.setText("✓ Inference hotova")
    self.inference_button.setEnabled(False)

    self.xray_stack.setCurrentIndex(1)
    self.menu_buttons["Body"].click()

def _on_inference_error(self, error_msg: str):
    """Callback na chybu - MAIN THREAD"""
    logger.error(f"[Session {self.session_name}] Inference chyba: {error_msg}")

    # Zobraz error dialog
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.critical(self, "Inference Error", f"Chyba: {error_msg}")

    # Reset UI
    self.inference_button.setText("Spustit Inferenci (znovu)")
    self.inference_button.setEnabled(True)

def _on_progress_update(self, message: str):
    """Progress update - MAIN THREAD"""
    self.inference_button.setText(message)
    logger.debug(f"[Session {self.session_name}] {message}")
```

**Výhody tohoto přístupu:**

✅ UI zůstává responsive
✅ Uživatel vidí progress ("⏳ Inference běží...")
✅ Lze cancelovat (přidat cancel button později)
✅ Více sessions může běžet paralelně bez problémů
✅ Snadné přidat timeout, retry, atd.

---

### 4. Model Initialization Strategy

**Problém:** Kdy se má model naloadovat?

```
SESSION 1        SESSION 2         SESSION 3
├─ Model A    ├─ Model B      ├─ Model A
│  (instance1)│  (instance2)   │  (instance3)
│ (10GB VRAM)  │ (10GB VRAM)    │ (10GB VRAM)
└─────────────┴────────────────┴──────────────
   30GB VRAM POTŘEBA! ❌ PROBLÉM NA BRAMBORÁCH!
```

**Řešení:** Lazy loading + session-local instance

```python
# core/models/model_manager.py (NEW)

class ModelManager:
    """Spravuje instanci modelu pro jednu session"""

    def __init__(self, model_name: str, config: Dict = None):
        self.model_name = model_name
        self.config = config or {}
        self._model_instance = None  # Lazy loading

    def get_model(self) -> BaseMLInference:
        """Lazy load - vytvoř instanci jen když je potřeba"""
        if self._model_instance is None:
            logger.info(f"[Manager] Loaduji model: {self.model_name}")
            from core.models.registry import ModelRegistry
            self._model_instance = ModelRegistry.create_instance(self.model_name)
        return self._model_instance

    def release(self):
        """Uvolni model z paměti - volej v SessionScreen.__del__"""
        if self._model_instance:
            logger.info(f"[Manager] Uvolňuji model: {self.model_name}")
            # TODO: cleanup logic (GPU memory, cache clearing)
            self._model_instance = None
```

**Integrujeme v SessionScreen:**

```python
# ui/session_screen.py

class SessionScreen(QWidget):
    def __init__(self, session_name):
        super().__init__()
        self.session_name = session_name
        self.model_manager = None  # Inicializuj později
        # ...

    def on_model_changed(self, model_name):
        """Když si uživatel vybere model"""
        # Vytvoř manager pro nový model
        self.model_manager = ModelManager(model_name)
        # ...

    def get_model_instance(self) -> BaseMLInference:
        """Lazy getter pro model"""
        if self.model_manager:
            return self.model_manager.get_model()
        return None

    def __del__(self):
        """Uvolni model když se session zavírá"""
        if self.model_manager:
            self.model_manager.release()
```

---

### 5. Configuration Management

**Per-model konfigurace bez chaos-u:**

```
core/models/
├── preview/
│   └── config.py
│
└── atlas_unet/
    └── config.py
```

**Příklad: `core/models/atlas_unet/config.py`**

```python
"""Atlas UNet model configuration"""

from pathlib import Path

# Model weights
MODEL_WEIGHTS_PATH = Path(__file__).parent / "weights" / "atlas-model-final.pth"

# Preprocessing
HISTOGRAM_EQUALIZATION = True
EXPECTED_INPUT_SIZE = (512, 512)

# Inference
SLIDING_WINDOW_SIZE = (512, 512)
SLIDING_WINDOW_OVERLAP = 0.25  # 25% overlap

# Postprocessing
MORPHOLOGICAL_OPENING_KERNEL = 5
MORPHOLOGICAL_CLOSING_KERNEL = 5

# Output
OUTPUT_FORMAT = "labelme_5.2.1"  # LabelMe format
KEYPOINT_LABELS = {
    "C2": ["top left", "top right", "bottom left", "bottom right", "centroid"],
    "C3": ["top left", "top right", "bottom left", "bottom right", "centroid"],
    # ...
}
```

**Příklad: `core/models/preview/config.py`**

```python
"""Preview simulator model configuration"""

from pathlib import Path

# Test data
TEST_IMAGE_PATH = Path(__file__).parent.parent.parent / "testing_data" / "0001035_image.png"
TEST_RESULTS_PATH = Path(__file__).parent.parent.parent / "testing_data" / "0001035_maskhat.json"

# Output format
OUTPUT_FORMAT = "labelme_5.2.1"
```

**Loadování config v modelu:**

```python
# core/models/atlas_unet/atlas_model.py

from core.models.atlas_unet import config
from core.models.base_inference import BaseMLInference

class AtlasUNetModel(BaseMLInference):
    def __init__(self):
        self.weights_path = config.MODEL_WEIGHTS_PATH
        self.model = self._load_model()

    def _load_model(self):
        # Load PyTorch model
        import torch
        model = torch.load(self.weights_path)
        return model
```

---

## File Structure & Organization

### Kompletní struktura po implementaci

```
c:\GitHub\DigiTech-PySide-GUI-Project\
│
├── core/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_inference.py                    ✅ Existuje (jen light cleanup)
│   │   ├── data_structures.py                   ✅ Existuje
│   │   ├── registry.py                          🆕 NOVÝ - Model registry
│   │   ├── model_manager.py                     🆕 NOVÝ - Session-local manager
│   │   │
│   │   ├── preview/
│   │   │   ├── __init__.py
│   │   │   ├── preview_model.py                 🔄 Renamed z ML_inference.py
│   │   │   └── config.py
│   │   │
│   │   └── atlas_unet/
│   │       ├── __init__.py
│   │       ├── atlas_model.py                   🆕 NOVÝ - Main wrapper
│   │       ├── config.py                        🆕 NOVÝ - UNet config
│   │       ├── preprocessing.py                 📋 Kopírovat z toBeIntegrated
│   │       ├── postprocessing.py                📋 Kopírovat z toBeIntegrated
│   │       ├── keypoint_extraction.py           📋 Kopírovat z toBeIntegrated
│   │       └── weights/
│   │           └── atlas-model-final.pth        📋 Kopírovat z toBeIntegrated
│   │
│   ├── io/
│   │   ├── __init__.py
│   │   └── ML_output_handler.py                 ✅ Existuje
│   │
│   ├── workers/
│   │   ├── __init__.py                          🆕 NOVÝ
│   │   └── inference_worker.py                  🆕 NOVÝ - QThread worker
│   │
│   ├── graphics/
│   ├── presentation/
│   └── __init__.py
│
├── ui/
│   ├── session_screen.py                        🔄 UPRAVIT - Async inference
│   ├── main_window.py                           ✅ Existuje (no changes)
│   └── panels/
│
├── config.py                                     🔄 UPRAVIT - Models config
├── main.py                                       ✅ Existuje
├── logger.py                                     ✅ Existuje
│
├── testing_data/
│   ├── 0001035_image.png
│   ├── 0001035_maskhat.json
│   └── outputs/
│
├── toBeIntegrated/                               ✅ PROTECTED - Nikdy neměnit!
│   └── Src/Atlas/
│       ├── single_inference.py                   ← Kopírovat obsah
│       ├── keypoint_extraction.py                ← Kopírovat obsah
│       └── Utils/
│
└── plán_integrace_ml.md                          ← Tento dokument
```

---

## Implementation Phases

### Phase 1: Preparation (1-2 hodiny)

**Cíl:** Zkopírovat soubory z `toBeIntegrated/` do `core/models/atlas_unet/`

- [ ] 1a: Vytvoř `core/models/atlas_unet/` folder
- [ ] 1b: Vytvoř `core/models/atlas_unet/__init__.py`
- [ ] 1c: Vytvoř `core/models/atlas_unet/config.py`
- [ ] 1d: Zkopíruj `toBeIntegrated/Src/Atlas/single_inference.py` → `atlas_unet/preprocessing.py`
- [ ] 1e: Zkopíruj `toBeIntegrated/Src/Atlas/keypoint_extraction.py` → `atlas_unet/keypoint_extraction.py`
- [ ] 1f: Zkopíruj `toBeIntegrated/Src/Utils/` → helpers jako potřebné
- [ ] 1g: Zkopíruj weights `.pth` soubor → `core/models/atlas_unet/weights/`

**Validation:** Všechny soubory jsou na místě, žádné import errors

---

### Phase 2: Core Infrastructure (2-3 hodiny)

**Cíl:** Vytvořit model system bez UI změn

- [ ] 2a: Vytvoř `core/models/registry.py` s `ModelRegistry` class
- [ ] 2b: Vytvoř `core/models/model_manager.py` s `ModelManager` class
- [ ] 2c: Vytvoř `core/models/preview/__init__.py` a `preview_model.py` (rename z `ML_inference.py`)
- [ ] 2d: Vytvoř `core/models/atlas_unet/__init__.py` s `AtlasUNetModel` class
- [ ] 2e: Auto-registruj oba modely v registru
- [ ] 2f: Vytvořit unit testy (mock inference) pro ověření

**Test:** Registry vrátí ["preview", "atlas_unet"] a umí je instantiate

---

### Phase 3: Threading Infrastructure (2-3 hodiny)

**Cíl:** Vytvořit background worker threads

- [ ] 3a: Vytvoř `core/workers/inference_worker.py` s `InferenceWorker` class
- [ ] 3b: Vytvořit test QApplication s dummy SessionScreen
- [ ] 3c: Ověřit že signals fungují a necrashují UI

**Test:** UI zůstane responsive, worker běží v background

---

### Phase 4: UI Integration (2-3 hodiny)

**Cíl:** Napojit UI na nový model system

- [ ] 4a: Updatuj `config.py` aby loadil modely z registry
- [ ] 4b: Updatuj `ui/session_screen.py` - `on_inference_clicked()` aby byl async
- [ ] 4c: Přidej `_on_inference_ready()` signal handler
- [ ] 4d: Přidej `_on_inference_error()` signal handler
- [ ] 4e: Přidej `_on_progress_update()` signal handler
- [ ] 4f: Aktualizuj combo-box aby se loadil z registru (ne hardcoded stringy)

**Test:** Změnit model combo, spustit inference, UI zůstane responsive

---

### Phase 5: End-to-End Testing (2-3 hodiny)

**Cíl:** Ověřit že vše funguje dohromady

- [ ] 5a: Testovací image - zkontroluj že Preview model vrací správný output
- [ ] 5b: Testovací image - zkontroluj že Atlas UNet vrací správný output
- [ ] 5c: Multi-session - otevři 2 sessions, běž inference na obou paralelně
- [ ] 5d: Error handling - test disconnect GPU, corrupted image, atd.
- [ ] 5e: Performance - měř RAM/CPU utilization na bramborách

**Test:** Vše funguje bez freezu, paralelní sessions OK

---

## Critical Issues & Solutions

### Issue #1: GPU Memory & Model Loading 🔴 CRITICAL

**Problém:**

```
Session 1: loads Atlas UNet (10GB GPU RAM)
Session 2: loads Atlas UNet (10GB GPU RAM)
← Total: 20GB! Crash na bramborách ❌
```

**Řešení - Singleton per model + session tracking:**

```python
# core/models/model_manager.py - Singleton pattern

import threading

class ModelManager:
    _instances = {}  # Dict[model_name, model_instance]
    _lock = threading.Lock()

    @classmethod
    def get_model(cls, model_name: str) -> BaseMLInference:
        """Vrátí STEJNOU instanci pro všechny sessions (singleton)"""
        if model_name not in cls._instances:
            with cls._lock:  # Thread-safe
                if model_name not in cls._instances:
                    cls._instances[model_name] = ModelRegistry.create_instance(model_name)
        return cls._instances[model_name]
```

**Výhody:**

- Pouze 1 instance per model (ne 3!)
- Thread-safe (lock)
- Inference je single-threaded (PyTorch není multi-threaded bezpečný)
- Sessions se prostě sdílí model instanci

**Nevýhoda:**

- Concurrent inference není možné (ale to není problém - PyTorch to stejně neuznává)

---

### Issue #2: PyTorch Thread Safety ⚠️ IMPORTANT

**Problém:**
PyTorch modely NEJSOU thread-safe. Když inference běží v session 1, session 2 nesmí volat inference zároveň.

**Řešení - Model mutex:**

```python
# core/models/model_manager.py

import threading

class ModelManager:
    _locks = {}  # Dict[model_name, threading.Lock]

    @classmethod
    def get_lock_for_model(cls, model_name: str) -> threading.Lock:
        """Vrátí lock pro model"""
        if model_name not in cls._locks:
            cls._locks[model_name] = threading.Lock()
        return cls._locks[model_name]

# V InferenceWorker:
def run(self):
    lock = ModelManager.get_lock_for_model(self.model_name)
    with lock:  # Čeká dokud inference skončí
        self.resultReady.emit(self.model.predict(self.image_path))
```

**Efekt:**

- Session 1 starts inference (získá lock)
- Session 2 starts inference (čeká na lock)
- Session 1 skončí (uvolní lock)
- Session 2 dostane lock a běží
- ✅ Žádný crash, jen sekvencí inference

---

### Issue #3: Long Inference Times 🐢 BOTTLENECK

**Problém:** Atlas UNet inference trvá 10-30 sekund

**Řešení - UI feedback + progress:**

```python
# InferenceWorker - emit progress

self.progressUpdate.emit("⏳ Načítám model...")       # 2s
time.sleep(0.1)
self.progressUpdate.emit("🔄 Inference... (0/10)")   # 10s
time.sleep(0.1)
self.progressUpdate.emit("📊 Postprocessing...")     # 5s
```

**Efekt:** Uživatel vidí že se něco děje, nefreeznul

---

### Issue #4: Model Config Conflicts 🔧 TRICKY

**Problém:** Dva modely mají různé konfiguraci (weights path, preprocessing, atd.)

**Řešení - Namespace per model:**

```
core/models/
├── preview/
│   ├── __init__.py
│   └── config.py         ← self._load_config("preview")
│
└── atlas_unet/
    ├── __init__.py
    └── config.py         ← self._load_config("atlas_unet")
```

**Implementace:**

```python
# core/models/base_inference.py

class BaseMLInference(ABC):
    @staticmethod
    def _load_config(model_name: str):
        """Loaduj config pro konkrétní model"""
        if model_name == "preview":
            from core.models.preview import config
        elif model_name == "atlas_unet":
            from core.models.atlas_unet import config
        return config
```

---

### Issue #5: Error Recovery ❌ RESILIENCE

**Problém:** Když model crashuje, celá session/app umírá

**Řešení - Graceful error handling:**

```python
# InferenceWorker

def run(self):
    try:
        # ... inference ...
        self.resultReady.emit(results)
    except torch.cuda.OutOfMemoryError:
        self.errorOccurred.emit("❌ Nedostatek GPU paměti")
    except FileNotFoundError:
        self.errorOccurred.emit("❌ Weights soubor nenalezen")
    except Exception as e:
        self.errorOccurred.emit(f"❌ Neznámá chyba: {e}")

# SessionScreen

def _on_inference_error(self, error_msg: str):
    QMessageBox.critical(self, "Inference Error", error_msg)
    # Session zůstane živá, uživatel může zkusit znovu
```

---

## Data Flow Diagrams

### Diagram 1: Model Loading Sequence

```
┌──────────────────────────────────────────────────────────────┐
│                    app.py - main()                            │
└──────────────┬───────────────────────────────────────────────┘
               │
               ├─→ import core.models.registry
               │   ├─→ registry imports preview_model
               │   │   └─→ PreviewModel.register("preview")
               │   └─→ registry imports atlas_unet.atlas_model
               │       └─→ AtlasUNetModel.register("atlas_unet")
               │
               ├─→ MainWindow().__init__()
               │   └─→ SessionScreen().__init__()
               │       └─→ on_model_changed("preview")
               │           └─→ ModelManager.get_model("preview")
               │               └─→ ModelRegistry.create_instance("preview")
               │                   └─→ PreviewModel()
               │
               └─→ app.exec()
                   [waiting for user interaction]
```

### Diagram 2: Inference Execution Flow

```
┌─────────────────────────────────────────────────────────┐
│          UI THREAD - SessionScreen                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ on_inference_clicked()                           │   │
│  │ ├─ self.inference_worker = InferenceWorker(...)  │   │
│  │ ├─ worker.resultReady.connect(...)               │   │
│  │ ├─ worker.errorOccurred.connect(...)             │   │
│  │ └─ worker.start()  ← ***SPAWNS THREAD***         │   │
│  └──────────────────────────────────────────────────┘   │
│          │                                               │
│          │                      [UI remains responsive]  │
│          │ (user can change tabs, open new session)     │
│          │                                               │
│          │ <-- wait for signal -->                      │
│          │                                               │
└──────────┼───────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────────┐
           │                                                  │
           ▼                                                  │
┌─────────────────────────────────────────────────────────┐  │
│      BACKGROUND THREAD - InferenceWorker                │  │
│  ┌──────────────────────────────────────────────────┐   │  │
│  │ run()                                            │   │  │
│  │ ├─ progressUpdate.emit("Loading model...")      ├──┼──┼─→ UI updates button
│  │ │                                                │   │  │
│  │ ├─ WITH lock:                                   │   │  │
│  │ │   model.predict(image_path)  ← 10-30s!       │   │  │
│  │ │   (GPU doing ML work)                        │   │  │
│  │ │                                                │   │  │
│  │ ├─ progressUpdate.emit("Parsing...")            ├──┼──┼─→ UI updates button
│  │ │   parse_inference_output()  ← 1s              │   │  │
│  │ │                                                │   │  │
│  │ └─ resultReady.emit(vertebral_results)          ├──┼──┼─→ [SIGNAL RECEIVED]
│  │                                                  │   │  │
│  └──────────────────────────────────────────────────┘   │  │
│                                                         │  │
└─────────────────────────────────────────────────────────┘  │
                                                             │
                                                             ▼
                                    ┌─────────────────────────────────────┐
                                    │ _on_inference_ready(vertebral_results)
                                    │ ├─ canvas_panel.set_vertebral_points()
                                    │ ├─ vertebral_panel.set_vertebral_data()
                                    │ └─ menu_buttons["Body"].setEnabled(True)
                                    └─────────────────────────────────────┘
```

### Diagram 3: Multi-Session Concurrent Inference

```
TIMELINE: Session 1 a Session 2 běží paralelně (UI thread)

Time │ Session 1 UI    │ Session 2 UI    │ Model Lock │ Backend Notes
─────┼────────────────┼────────────────┼────────────┼────────────────────
0s   │ Click "Infer"  │                │            │
     │ → spawn W1     │                │ FREE       │
─────┼────────────────┼────────────────┼────────────┼────────────────────
1s   │ "Loading..."   │                │ FREE       │
     │ (responsive)   │                │            │
─────┼────────────────┼────────────────┼────────────┼────────────────────
2s   │ "Inference..." │ Click "Infer"  │ LOCKED     │ W1 acquiring lock
     │                │ → spawn W2     │ (by W1)    │
─────┼────────────────┼────────────────┼────────────┼────────────────────
3s   │ [GPU working]  │ "Loading..."   │ LOCKED     │ W2 waiting for lock
     │                │ (responsive!)  │ (by W1)    │
─────┼────────────────┼────────────────┼────────────┼────────────────────
15s  │ "Parsing..."   │ "Loading..."   │ LOCKED     │ W1 still running
     │                │                │ (by W1)    │
─────┼────────────────┼────────────────┼────────────┼────────────────────
20s  │ ✓ DONE!        │ [waiting...]   │ LOCKED     │ W1 emits result
     │ Show points    │ (ready to go)  │ (by W1)    │
─────┼────────────────┼────────────────┼────────────┼────────────────────
21s  │                │ "Inference..." │ LOCKED     │ W2 acquired lock
     │                │                │ (by W2)    │
─────┼────────────────┼────────────────┼────────────┼────────────────────
35s  │                │ ✓ DONE!        │ FREE       │ W2 emits result
     │                │ Show points    │            │

✅ RESULT: Obě sessions běží bez freezu, paralelní inference je sequential
           (kvůli PyTorch thread safety), ale UI zůstává responsive!
```

---

## Checklist & Milestones

### Pre-Implementation Checklist

- [ ] Všichni v týmu rozumí Threading strategy
- [ ] Všichni v týmu rozumí Model Registry
- [ ] Všichni v týmu rozumí per-model folder struktura
- [ ] Code review tohoto plánu je hotova
- [ ] Backup původního repo je hotovej

### Implementation Checklist

**Phase 1:**

- [ ] 1a: Folder vytvořen
- [ ] 1b: `__init__.py` existuje
- [ ] 1c: `config.py` existuje
- [ ] 1d-1g: Všechny soubory zkopírovány
- [ ] ✅ Phase 1 complete

**Phase 2:**

- [ ] 2a: `registry.py` v place
- [ ] 2b: `model_manager.py` v place
- [ ] 2c-2d: Preview a Atlas modely zaregistrovány
- [ ] 2e: Unit testy passují
- [ ] ✅ Phase 2 complete

**Phase 3:**

- [ ] 3a: `inference_worker.py` v place
- [ ] 3b: Test QApplication existuje
- [ ] 3c: Signals fungují bez crashes
- [ ] ✅ Phase 3 complete

**Phase 4:**

- [ ] 4a-4f: Všechny UI changes hotovy
- [ ] 4g: Combo-box loadí z registru
- [ ] 4h: Inference je async a non-blocking
- [ ] ✅ Phase 4 complete

**Phase 5:**

- [ ] 5a-5b: Oba modely vrací správné výsledky
- [ ] 5c: Multi-session paralelní inference works
- [ ] 5d: Error handling funguje
- [ ] 5e: Performance je OK na bramborách
- [ ] ✅ Phase 5 complete

### Final Validation

- [ ] Všechny testy passují
- [ ] Code review hotova
- [ ] Documentation updatovana
- [ ] Performance benchmarks zaznamenaný
- [ ] Commit do git s descriptivní zprávou

---

## FAQ & Troubleshooting

### Q: "Proč Singleton? To bude problém když se session zavře!"

**A:** Singleton je OK, protože:

1. Model se drží v paměti dokud se app neuzavře
2. Je to efektivnější (GPU memory)
3. Nový model session nekreuje novou instanci
4. Cleanup se stane v `app.close()` nebo manual `.release()`

---

### Q: "Co když inference trvá 30 sekund a uživatel chce cancelovat?"

**A:** Později! Teď to není priorita. Ale struktura umožňuje:

```python
def cancel_inference(self):
    if self.inference_worker:
        self.inference_worker.terminate()  # Skončí vlákno
```

---

### Q: "Jak je to s GPU, když běží inference z více sessions?"

**A:** Při práci s mutex lock - jen jedna inference najednou. Ostatní čekají.

```
Session 1: inference (0-30s) → GPU busy
Session 2: waiting...
Session 3: waiting...
Session 2: inference (30-60s) → GPU busy
Session 3: waiting...
Session 3: inference (60-90s) → GPU busy
```

To je OK, protože PyTorch není re-entrant.

---

### Q: "Co když se model crashuje?"

**A:** Error signal se emituje, UI zobrazí dialog, session zůstane živá:

```python
except Exception as e:
    self.errorOccurred.emit(f"Model crash: {e}")
    # Session stále funguje, uživatel může zkusit znovu
```

---

## Migration Path (Backwards Compatibility)

Aby existing kód fungoval bez změn:

```python
# core/models/__init__.py

# Stará API (pro backward compatibility)
from core.models.preview import PreviewModel as MLInferenceSimulator

# Nová API
from core.models.registry import ModelRegistry
from core.models.model_manager import ModelManager

__all__ = [
    'MLInferenceSimulator',      # Stará jména pro stary kod
    'ModelRegistry',              # Nová jména
    'ModelManager',
    # ...
]
```

To umožní že `ui/session_screen.py` může dočasně používat starou API a pak ji postupně změnit.

---

## Next Steps (Implementation Order)

1. **Přečti si tento plán** - projdi si všechny sekce
2. **Q&A** - zeptej se na cokoliv co není jasné
3. **Code review** - pokaždé když implementuješ novou fázi
4. **Git commits** - na konci každé fáze s popisem
5. **Testing** - end-to-end na bramborách s real modelem

---

## Summary Table

| Aspekt | Current | Proposed | Benefit |
|--------|---------|----------|---------|
| **Threading** | Synchronní | QThread worker | ✅ Non-blocking UI |
| **Models** | Hardcoded ["m1", "m2"] | Registry system | ✅ Easy to add models |
| **Model init** | On-demand | Lazy loading | ✅ RAM efficient |
| **Concurrent inference** | ❌ Crashes | ✅ Sequential with mutex | ✅ Safe |
| **Configuration** | Global config | Per-model config | ✅ Isolation |
| **Error handling** | Exception crashes | Graceful signals | ✅ Resilience |
| **Code organization** | Flat | Hierarchical per-model | ✅ Maintainable |

---

## Document Version History

| Verze | Datum | Autor | Změny |
|-------|-------|-------|--------|
| 0.1 | Apr 12, 2026 | AI |初稿 - Initial framework |
| 1.0 | Apr 12, 2026 | AI | Final review + approval |

---

**Status:** ✅ Ready for Implementation

**Next Review:** After Phase 1 completion

---

*Pokud máš nějaké otázky nebo připomínky, dej vědět!* 🚀
