# 📊 ML Integration Plan - Quick Reference

## Problem Summary

```txt
CURRENT STATE ❌
├─ Synchronní inference → UI FREEZES na 10-30s
├─ Hardcoded models ["m1", "m2"] → Těžko přidávat nové
├─ Model loading on-demand → RAM neefektivní
├─ Bez threading → Blokuje vše když běží
└─ Flat structure → Těžko se orientuje

DESIRED STATE ✅
├─ Async inference s QThread → UI RESPONSIVE
├─ Model registry system → Easy pluggable models
├─ Lazy loading + singleton → RAM optimized
├─ Per-session threads → Paralelní sessions
└─ Per-model folders → Clear organization
```

---

## Solution Architecture

### Threading Model

```
┌─────────────────────────────────────┐
│    MAIN UI THREAD                   │
│  ┌─────────────────────────────────┐│
│  │ QApplication.exec()             ││
│  │   └─ Session 1, 2, 3 UI updates ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
    ▼         ▼         ▼
   S1-W     S2-W      S3-W
  (idle)   (busy)     (idle)
           Inference  Waiting
           Queue

✅ Benefit: UI responsive, inference sequential + thread-safe
```

### Model Registry

```
ModelRegistry
├─ register("preview", PreviewModel)
├─ register("atlas_unet", AtlasUNetModel)
└─ register("custom_xyz", CustomModel)

┌─────────────────┐
│ SessionScreen 1 │
└────────┬────────┘
         │ get_model("atlas_unet")
         ▼
┌─────────────────┐
│ ModelManager    │
└────────┬────────┘
         │ create_instance()
         ▼
┌─────────────────┐
│ AtlasUNetModel  │ ← Singleton (shared across sessions)
└─────────────────┘
```

### Folder Structure

```
core/models/
├─ base_inference.py         ← Abstract interface
├─ registry.py               ← NEW: Model discovery
├─ model_manager.py          ← NEW: Lifecycle mgmt
│
├─ preview/
│  ├─ preview_model.py
│  └─ config.py
│
└─ atlas_unet/
   ├─ atlas_model.py         ← NEW: Main wrapper
   ├─ config.py              ← NEW: UNet config
   ├─ preprocessing.py        ← FROM toBeIntegrated
   ├─ postprocessing.py       ← FROM toBeIntegrated
   ├─ keypoint_extraction.py  ← FROM toBeIntegrated
   └─ weights/
      └─ atlas-model-final.pth

core/workers/
└─ inference_worker.py       ← NEW: QThread worker
```

---

## Implementation Phases

| Phase | Goal | Duration | Status |
|-------|------|----------|--------|
| 1️⃣ **Prep** | Copy files from toBeIntegrated | 1-2h | 📋 Ready |
| 2️⃣ **Core** | Registry + model system | 2-3h | 📋 Ready |
| 3️⃣ **Threading** | QThread worker + signals | 2-3h | 📋 Ready |
| 4️⃣ **UI Integration** | Async inference button | 2-3h | 📋 Ready |
| 5️⃣ **Testing** | End-to-end validation | 2-3h | 📋 Ready |

**Total: ~12-15 hours** of coding

---

## Critical Issues & Mitigations

| Issue | Severity | Mitigation |
|-------|----------|-----------|
| 🔴 GPU memory (multiple models) | CRITICAL | Singleton per model (not per session) |
| 🔴 PyTorch thread safety | CRITICAL | Model mutex lock (sequential inference) |
| 🟡 Long inference times (10-30s) | HIGH | QThread + progress signals |
| 🟡 Model config conflicts | MEDIUM | Namespace per model (separate config.py) |
| 🟢 Error recovery | LOW | Graceful error signals + dialog |

---

## Key Concepts

### Lazy Loading

```python
# Don't load model until needed
model = None
if need_inference:
    model = ModelRegistry.create_instance("atlas_unet")  # Load now
```

### Singleton Pattern

```python
# Only ONE instance of model (shared)
ModelManager._instances["atlas_unet"] = AtlasUNetModel()  # Created once
# All sessions use same instance
```

### Threading with Mutex

```python
# Only one inference at a time (PyTorch limitation)
with ModelManager.get_lock_for_model("atlas_unet"):
    model.predict(image_path)  # Exclusive access
```

### Signals & Slots

```python
# Worker thread → Main thread communication
worker.resultReady.emit(results)  # ← Worker thread
# Main thread receives:
def _on_inference_ready(self, results):
    self.canvas_panel.set_vertebral_points(results)
```

---

## Before You Start

✅ **Pre-Flight Checklist:**

- [ ] Read `plán_integrace_ml.md` fully
- [ ] Understand threading diagram
- [ ] Understand model registry concept
- [ ] Ask questions (don't skip!)
- [ ] Backup repo
- [ ] Create feature branch: `git checkout -b feature/ml-integration`

---

## Quick Implementation Order

1. **Phase 1:** Folder structure + file copy (straightforward)
2. **Phase 2:** Registry + model system (core foundation)
3. **Phase 3:** Worker thread (threading magic)
4. **Phase 4:** UI plumbing (connect everything)
5. **Phase 5:** Testing + validation (ensure robustness)

---

## Data Flow Summary

```
USER: Clicks "Spustit Inferenci" button
  │
  ├─→ on_inference_clicked() [UI THREAD]
  │   ├─ Create InferenceWorker(model, image_path)
  │   ├─ Connect signals → slots
  │   └─ worker.start() ← ***SPAWNS THREAD***
  │
  ├─→ InferenceWorker.run() [BACKGROUND THREAD]
  │   ├─ progressUpdate.emit("Loading...")
  │   ├─ WITH lock:
  │   │   model.predict(image_path) ← 10-30s GPU work
  │   ├─ progressUpdate.emit("Parsing...")
  │   ├─ parse_inference_output()
  │   └─ resultReady.emit(vertebral_results)
  │
  └─→ _on_inference_ready(results) [UI THREAD]
      ├─ canvas_panel.set_vertebral_points(results)
      ├─ vertebral_panel.set_vertebral_data(results)
      └─ menu_buttons["Body"].click()

✅ RESULT: UI stayed responsive the whole time!
```

---

## Common Questions

**Q: What if model crashes?**
A: Error signal emitted → UI shows dialog → Session stays alive → User can retry

**Q: Can 2 sessions run inference at same time?**
A: Sequentially (one at a time) due to PyTorch limitation, but UI never freezes

**Q: What happens to model memory when session closes?**
A: Model stays in memory (singleton) until app closes (OK on bramborách)

**Q: Can I add a new model?**
A: Yes! Create `core/models/my_model/my_model.py`, register in registry, done!

---

## Success Criteria

✅ **Phase 1 PASS:** All files copied, no import errors
✅ **Phase 2 PASS:** Registry returns model instances correctly
✅ **Phase 3 PASS:** QThread worker runs without crashing
✅ **Phase 4 PASS:** UI button triggers async inference
✅ **Phase 5 PASS:** Both models work, multi-session OK, no freezes

---

## Git Commit Messages (Template)

```
feat(ml-integration): Phase 1 - Copy Atlas files

- Create core/models/atlas_unet/ structure
- Copy preprocessing, postprocessing, keypoint_extraction
- Add model weights directory
- RELATED: #issue_number

feat(ml-integration): Phase 2 - Implement model registry

- Add ModelRegistry for dynamic model discovery
- Add ModelManager for per-session lifecycle
- Register preview and atlas_unet models
- 100% backward compatible

feat(ml-integration): Phase 3 - Add QThread worker

- Implement InferenceWorker(QThread)
- Add resultReady, errorOccurred, progressUpdate signals
- Thread-safe with mutex lock

feat(ml-integration): Phase 4 - UI integration

- Update SessionScreen.on_inference_clicked() to async
- Add _on_inference_ready() signal handler
- Update model combo to load from registry
- Update button text with progress

feat(ml-integration): Phase 5 - End-to-end testing

- Test both models on real images
- Validate multi-session parallel execution
- Performance testing on target hardware
```

---

## File Locations (For Reference)

| What | Where | Status |
|------|-------|--------|
| Model registry | `core/models/registry.py` | 🆕 NEW |
| Model manager | `core/models/model_manager.py` | 🆕 NEW |
| Threading worker | `core/workers/inference_worker.py` | 🆕 NEW |
| Atlas model wrapper | `core/models/atlas_unet/atlas_model.py` | 🆕 NEW |
| Atlas config | `core/models/atlas_unet/config.py` | 🆕 NEW |
| Session screen | `ui/session_screen.py` | 🔄 UPDATE |
| Config | `config.py` | 🔄 UPDATE |
| Plan doc | `plán_integrace_ml.md` | ✅ CREATED |

---

## Useful Links

- [PySide6 QThread docs](https://doc.qt.io/qtforpython/PySide6/QtCore/QThread.html)
- [Python threading.Lock docs](https://docs.python.org/3/library/threading.html#lock-objects)
- [Design patterns: Singleton](https://refactoring.guru/design-patterns/singleton)
- [PyTorch thread safety](https://pytorch.org/docs/stable/notes/multiprocessing.html)

---

**Created:** April 12, 2026
**Status:** Ready for implementation
**Next Step:** Start Phase 1 (file copying)

🚀 **Let's build this!**
