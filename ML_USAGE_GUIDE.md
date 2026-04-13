"""
ML INTEGRATION GUIDE - Phase 1 & 2 Complete ✓

Quick Start pro vývojáře a uživatele
"""

# ============================================================================

# 1. STARTUP - Co se musí stát na začátku aplikace

# ============================================================================

# V main.py nebo config.py na POČÁTKU

from core.models.initialize_models import initialize_models

# Zavolej toto jedenkrát během startu

initialize_models()

# Nyní jsou modely registrované a připravené k použití

# ============================================================================

# 2. NORMÁLNÍ POUŽITÍ - Jak spustit inference

# ============================================================================

from core.models.model_manager import ModelManager
import numpy as np

# Získej manager (singleton)

manager = ModelManager.get_instance()

# Loadni model

model = manager.get_model(
    model_name='preview',          # nebo 'atlas_unet'
    session_id='session_123'       # Unikátní ID pro tuto session
)

# Spusť inference (používáme predict() interface)

result = model.predict("path/to/image.png")

# Result je JSON ve formátu LabelMe 5.2.1

# {

# 'version': '5.2.1'

# 'shapes': [

# {'label': 'C2', 'points': [[x1,y1], [x2,y2], ...], ...}

# 

# ]

# }

# Na konci session

manager.unload_model('preview', 'session_123')

# ============================================================================

# 3. DOSTUPNÉ MODELY

# ============================================================================

from core.models.registry import ModelRegistry

# Zjisti které modely jsou dostupné

available = ModelRegistry.list_enabled_models()

# Output: ['preview', 'atlas_unet'] (pokud je PyTorch nainstalován)

# Zjisti informace o modelu

model_class = ModelRegistry.get_model_class('preview')
config = ModelRegistry.get_model_config('preview')

# ============================================================================

# 4. KONFIGUROVÁNÍ MODELŮ

# ============================================================================

# Každý model má vlastní konfiguraci

# - core/models/preview/config.py

# - core/models/atlas_unet/config.py

# Měň konfiguraci v těchto souborech, ne v kódu

# ============================================================================

# 5. ARCHITEKTURA - Jak to funguje

# ============================================================================

"""
┌─────────────────┐
│  APLIKACE       │
└────────┬────────┘
         │
         ├─→ initialize_models()  [Na startu, jedenkrát]
         │      └─→ ModelRegistry.register('preview', MLInferenceSimulator)
         │      └─→ ModelRegistry.register('atlas_unet', AtlasUNetModel)
         │
         └─→ manager = ModelManager.get_instance()
                └─→ model = manager.get_model('preview', 'session_001')
                   └─→ Lazy-loads model (poprvé)
                   └─→ Vrátí MLInferenceSimulator instance

                └─→ result = model.predict("image.png")
                   └─→ Spustí inference
                   └─→ Vrátí LabelMe JSON

                └─→ manager.unload_model('preview', 'session_001')
                   └─→ Vymaže model ze paměti
"""

# ============================================================================

# 6. LAZY LOADING - Co to znamená?

# ============================================================================

"""
Lazy loading = model se naloaduje až když se POPRVÉ POUŽIJE

Výhody:
✓ Aplikace startuje rychle (neloaduje všechny modely)
✓ VRAM se používá jen když je potřeba
✓ Pokud si model vyberu a nepoužiju ho, není v paměti

Jak to funguje:

1. initialize_models() - jen REGISTRUJE modely (bez loadování!)
2. get_model() - poprvé: LOADUJE model, vrátí instanci
3. get_model() - podruhé: vrátí TU SAMOU instanci (cached)
4. unload_model() - vymaže model ze paměti
"""

# ============================================================================

# 7. PER-SESSION INSTANCES - Co to znamená?

# ============================================================================

"""
Per-session = každá session má svou KOPII modelu

Proč to děláme?
✓ Thread-safety: každý thread má svou instanci
✓ Isolation: změny v jedné session neovlivní jinou
✓ Paralelismus: lze spustit inference na více sessionech zároveň

Jak to funguje:
manager.get_model('preview', session_id='session_001')  # Instanci #1
manager.get_model('preview', session_id='session_002')  # Instanci #2 (jiná!)

# Všechny volání se session_id='session_001' vrací STEJNOU instanci

manager.get_model('preview', session_id='session_001')  # Stejná jako #1
"""

# ============================================================================

# 8. TESTOVÁNÍ - Jak ověřit že to funguje?

# ============================================================================

"""
Spusť test suite:

    cd c:\GitHub\DigiT...-PySide-GUI-Project
    python -m core.models.test_models

Testy:
✓ TEST 1: Registry - ověří singleton pattern
✓ TEST 2: Manager - ověří lazy-loading a caching
✓ TEST 3: Initialize - ověří registraci modelů
✓ TEST 4: Preview Inference - ověří spuštění inference
✓ TEST 5: End-to-End - ověří kompletní workflow
"""

# ============================================================================

# 9. PŘIDÁNÍ NOVÉHO MODELU - Jak to udělat?

# ============================================================================

"""
Když chceš přidat nový ML model (např. TensorFlow model):

1. Vytvoř novou složku: core/models/my_model/

2. Vytvoř:
   - __init__.py (export třídy)
   - config.py (nastavení modelu)
   - my_model.py (implementace)

3. Implementuj BaseMLInference:
   class MyModel(BaseMLInference):
       def predict(self, image_path: str, **kwargs) -> Optional[Dict]:
           # Spusť inference
           # Vrátí LabelMe JSON nebo None
           pass

       def get_model_name(self) -> str:
           return "My Model Name"

4. Zaregistruj v core/models/initialize_models.py:
   ModelRegistry.register(
       model_name='my_model',
       model_class=MyModel,
       config={'some_param': 'value'},
       enabled=True
   )

5. Teď můžeš používat:
   manager.get_model('my_model', session_id='sess_001')
"""

# ============================================================================

# 10. TROUBLESHOOTING

# ============================================================================

"""
Q: PyTorch není nainstalován a Atlas model se neregistruje
A: To je normální. Preview model funguje bez PyTorchu.
   Když budeš mít PyTorch, Atlas model se automaticky registruje.

Q: Model se mi neuvolňuje z paměti
A: Zavolej manager.unload_model() na konci session.
   Nebo manager.unload_all() pro vše.

Q: Circular import chyba při registraci atlasu
A: Normální - atlas model se lazy-loaduje. Registrace bere jen třídu,
   ne celý modul. Ignoruj varování.

Q: Jak spustím inference bez UI?
A: Spusť test_models.py - je to příklad end-to-end workflowu bez UI.
"""
