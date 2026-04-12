# 📋 ML Integration Planning - Summary

**Date:** April 12, 2026
**Status:** ✅ Planning Complete - Ready for Implementation

---

## What Was Done

### 1. Deep Code Archaeology 🔍

- ✅ Analyzed `ui/session_screen.py` - identified synchronous inference as main bottleneck
- ✅ Studied `core/models/` structure - found good foundation with `BaseMLInference` interface
- ✅ Reviewed `config.py` - found `AVAILABLE_MODELS` already exists but hardcoded
- ✅ Examined threading - **NO QThread currently** (critical gap)
- ✅ Checked multi-session architecture - sessions are independent but share UI thread

### 2. Answered Key Design Questions ❓

**User Input (Your Responses):**

- A1: **Model config** - will use centralized registry
- A2: **Per-model config** - each model has its own `config.py`
- A3: **Model init** - lazy loading + thread-safe (detailed below)
- A4: **Folder structure** - Variant A (per-model folders) ✅
- A5: **Error handling** - type A (graceful errors with logging)
- A6: **Output format** - All models must return LabelMe JSON
- A7: **Testing** - Not our responsibility (delegated to ML team)
- A8: **Developer docs** - Both (docs + template)

### 3. Identified Critical Issues 🔴

| Issue | Severity | Root Cause |
|-------|----------|-----------|
| UI freezes during inference | 🔴 CRITICAL | `on_inference_clicked()` is synchronous |
| Model state management | 🔴 CRITICAL | No threading → can't handle concurrent sessions |
| GPU memory overhead | 🔴 CRITICAL | Multiple model instances per session would OOM |
| Hardcoded model names | 🟡 HIGH | Strings not registered, UI combo boxed hardcoded |
| Model configuration conflicts | 🟡 HIGH | No namespace isolation between models |

### 4. Created Comprehensive Plan 📄

Generated **`plán_integrace_ml.md`** (15KB, 10 major sections):

**Sections:**

1. Executive Summary
2. Current State Analysis
3. Design Philosophy (5 core principles)
4. **Proposed Architecture** (registry, threading, models)
5. **Threading Strategy** (QThread + signal/slot pattern) ⭐
6. File Structure & Organization (complete folder layout)
7. **Implementation Phases** (Phase 1-5 with checklists)
8. **Critical Issues & Solutions** (5 gotchas with code examples)
9. Data Flow Diagrams (3 ASCII diagrams)
10. Checklist & Milestones

**Diagrams Included:**

- Model loading sequence
- Inference execution flow
- Multi-session concurrent execution timeline

### 5. Created Quick Reference 🚀

Generated **`QUICK_REFERENCE.md`** for quick lookup:

- Problem summary (visual before/after)
- Solution architecture (threading model ASCII)
- Implementation phases table
- Common questions FAQ
- Success criteria
- Git commit templates

### 6. Updated Documentation 📚

- Updated `README.md` to reference both plan docs
- Added development roadmap status
- Pointed to `plán_integrace_ml.md` as **ESSENTIAL**

---

## Key Design Decisions

### 1. Threading Strategy: QThread Workers

**Approach:**

```
Main UI Thread ──→ QThread Worker (inference)
                   │
                   ├─ resultReady signal → UI updates
                   ├─ errorOccurred signal → Error dialog
                   └─ progressUpdate signal → Button text
```

**Benefits:**

- ✅ UI stays responsive during inference (10-30s)
- ✅ Multiple sessions can queue up inference
- ✅ Progress feedback to user
- ✅ Graceful error handling
- ✅ Easy to add cancel button later

### 2. Model Registry: Dynamic Discovery

**Approach:**

```python
ModelRegistry.register("preview", PreviewModel)
ModelRegistry.register("atlas_unet", AtlasUNetModel)
ModelRegistry.get_available_models()  # ["preview", "atlas_unet"]
```

**Benefits:**

- ✅ No hardcoded model names in UI
- ✅ Easy to add/remove models
- ✅ Testable (mock registry)
- ✅ Backwards compatible

### 3. Lazy Loading + Singleton: Memory Efficiency

**Approach:**

```python
# Create once, reuse in all sessions
model = ModelRegistry.create_instance("atlas_unet")  # Only here
# All 3 sessions share same instance

lock = ModelManager.get_lock_for_model("atlas_unet")
with lock:  # Sequential access (thread-safe)
    model.predict(image_path)
```

**Benefits:**

- ✅ Single model instance (10GB GPU → not 30GB!)
- ✅ Thread-safe with mutex
- ✅ PyTorch compatible (single-threaded)
- ✅ Only loads when needed (lazy)

### 4. Per-Model Folder Structure

**Folder Layout:**

```
core/models/
├─ preview/ (isolated)
│  ├─ preview_model.py
│  └─ config.py
│
└─ atlas_unet/ (isolated)
   ├─ atlas_model.py
   ├─ config.py
   ├─ preprocessing.py
   ├─ postprocessing.py
   ├─ keypoint_extraction.py
   └─ weights/
```

**Benefits:**

- ✅ Zero namespace conflicts
- ✅ Easy to find model-specific code
- ✅ Config isolation (no global collision)
- ✅ Easy to delete/deprecate models

---

## Implementation Roadmap

### Phase 1: Preparation (1-2 hours)

**Goal:** Copy files from `toBeIntegrated/`

Checklist:

- [ ] Create `core/models/atlas_unet/` structure
- [ ] Copy `preprocessing.py`, `postprocessing.py`, `keypoint_extraction.py`
- [ ] Copy model weights `.pth` file
- [ ] Create `config.py` for Atlas UNet

**Validation:** No import errors, all files in place

---

### Phase 2: Core Infrastructure (2-3 hours)

**Goal:** Model system without UI changes

Checklist:

- [ ] Create `registry.py` with `ModelRegistry` class
- [ ] Create `model_manager.py` with `ModelManager` class
- [ ] Refactor `ML_inference.py` → `preview/preview_model.py`
- [ ] Create `atlas_unet/atlas_model.py` wrapper
- [ ] Auto-register both models

**Validation:** Registry test passes, both models instantiate correctly

---

### Phase 3: Threading Infrastructure (2-3 hours)

**Goal:** Background worker threads with signals

Checklist:

- [ ] Create `core/workers/inference_worker.py`
- [ ] Implement `InferenceWorker(QThread)`
- [ ] Add signals: `resultReady`, `errorOccurred`, `progressUpdate`
- [ ] Test signals in isolation

**Validation:** Worker runs in background, signals fire correctly

---

### Phase 4: UI Integration (2-3 hours)

**Goal:** Connect everything to UI

Checklist:

- [ ] Update `session_screen.py` - `on_inference_clicked()` async
- [ ] Add `_on_inference_ready()` handler
- [ ] Add `_on_inference_error()` handler
- [ ] Add `_on_progress_update()` handler
- [ ] Update model combo to load from registry

**Validation:** UI non-blocking, model selection dynamic, inference async

---

### Phase 5: End-to-End Testing (2-3 hours)

**Goal:** Validate everything works

Checklist:

- [ ] Test Preview model on real image
- [ ] Test Atlas UNet model on real image
- [ ] Multi-session parallel execution test
- [ ] Error handling test (missing weights, GPU error, etc.)
- [ ] Performance measurement (RAM, CPU on target hardware)

**Validation:** All tests pass, no freezes, smooth UX

---

## Critical Insights

### Threading: Why QThread?

PySide6 blocks UI thread if work happens synchronously. QThread offloads to background:

- Worker runs in separate thread
- Signals cross thread boundaries safely
- UI thread handles signals (thread-safe by design)
- ✅ User can click other buttons while inference runs

### Model Singleton: Why Not Per-Session Instance?

Multiple instances = multiple GPU loads:

```
Session 1: Atlas UNet (10GB GPU)
Session 2: Atlas UNet (10GB GPU) ← bramborám se to nelíbí!
Session 3: Atlas UNet (10GB GPU)
────────────────────────────────
TOTAL: 30GB GPU needed ❌ CRASH!
```

Singleton solution:

```
Session 1: Uses model (acquires lock)
Session 2: Waits for lock
Session 3: Waits for lock
Session 1: Releases lock
Session 2: Uses model (acquires lock)
────────────────────────────────
MAX: 10GB GPU at any time ✅
```

### Config Namespace: Why Per-Model?

If everything in global `config.py`:

```python
ATLAS_WEIGHTS_PATH = "..."
PREVIEW_WEIGHTS_PATH = "..."
ATLAS_PREPROCESSING_ENABLED = True
PREVIEW_PREPROCESSING_ENABLED = False
# → Chaos! Hard to track what belongs where
```

Per-model config:

```
core/models/atlas_unet/config.py
├─ WEIGHTS_PATH
├─ PREPROCESSING_ENABLED
└─ MODEL_NAME

core/models/preview/config.py
├─ TEST_IMAGE_PATH
└─ MODEL_NAME
# → Clear! Each model owns its config
```

---

## Files Created/Modified

### Created (New Files)

- ✅ **`plán_integrace_ml.md`** (15KB) - Main implementation plan
- ✅ **`QUICK_REFERENCE.md`** (10KB) - Visual quick lookup
- ✅ This summary document

### Modified (Updated)

- ✅ **`README.md`** - Added references to plan docs

### To Be Created (During Implementation)

- `core/models/registry.py` - Model registry
- `core/models/model_manager.py` - Lifecycle manager
- `core/workers/inference_worker.py` - QThread worker
- `core/models/preview/` - Preview model (refactored)
- `core/models/atlas_unet/` - Atlas UNet integration

---

## Success Criteria

| Phase | Criteria | Status |
| ----- | -------- | ------ |
| **Phase 1** | All files copied, no import errors | 📋 Ready |
| **Phase 2** | Registry works, models instantiate | 📋 Ready |
| **Phase 3** | Worker thread + signals work | 📋 Ready |
| **Phase 4** | UI async, inference non-blocking | 📋 Ready |
| **Phase 5** | All models work, multi-session OK | 📋 Ready |

---

## Next Steps

1. **Review** - Read through `plán_integrace_ml.md` (especially sections 5, 8, 9)
2. **Questions** - Ask clarifying questions before starting
3. **Backup** - `git branch backup/pre-ml-integration`
4. **Start Phase 1** - Begin file copying (most straightforward)
5. **Commit Often** - One commit per phase with clear messages

---

## Known Limitations & Future Work

### Current Limitations

- Inference is sequential (not parallel) due to PyTorch thread safety
- Model loading is synchronous (could add progress spinner)
- No model caching in disk (could add MLOps later)
- No GPU device selection (fixed to first available)

### Future Enhancements

- Cancel inference button
- Model version selection
- Batch processing (multiple images)
- Model download/update functionality
- Hardware profiling (auto-detect GPU, CPU, RAM)
- Distributed inference (multi-machine)

---

## Contact & Questions

If anything is unclear:

1. Check `QUICK_REFERENCE.md` FAQ section
2. Read relevant section in `plán_integrace_ml.md`
3. Ask clarifying questions
4. Don't proceed if unsure!

---

## Document Status

| Document | Length | Status | Location |
| -------- | ------ | ------ | -------- |
| Main Plan | 15KB | ✅ Complete | `plán_integrace_ml.md` |
| Quick Ref | 10KB | ✅ Complete | `QUICK_REFERENCE.md` |
| This Doc | 3KB | ✅ Complete | `ML_INTEGRATION_SUMMARY.md` |
| README | Updated | ✅ Updated | `README.md` |

---

## Version History

| Version | Date | Author | Status |
| ------- | ---- | ------ | ------ |
| 1.0 | Apr 12, 2026 | AI Copilot | ✅ Complete |

---

**Ready to implement!** 🚀

Next: Phase 1 (file copying) can start immediately.
