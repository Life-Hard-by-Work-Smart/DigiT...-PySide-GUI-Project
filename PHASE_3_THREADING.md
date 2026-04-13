"""
PHASE 3 - Threading Infrastructure (COMPLETE)

✓ Vytvořeno:

- InferenceWorker - QThread worker pro async inference
- WorkerManager - High-level API pro spuštění workeru
- Test harness - Testuje QThread bez UI

Architektura:
"""

# ============================================================================

# 1. ARCHITECTURE - Jak QThread Inference Funguje

# ============================================================================

"""
STARY SYSTEM (Synchronní - UI FREEZUJE):

    User clicks button
         ↓
    on_inference_clicked() → MAIN THREAD
         ↓
    model.predict() → MAIN THREAD (BLOCKING!)
         ↓
    UI freezes na 5-30 sekund
         ↓
    Inference done, results returned

NOVY SYSTEM (Asynchronní - UI RESPONSIVE):

    User clicks button (MAIN THREAD)
         ↓
    manager.run_inference() (MAIN THREAD - vrátí hned!)
         ↓
    Spustí BACKGROUND THREAD s InferenceWorker
         ↓
    Background thread běží model.predict() (NE-BLOCKING!)
         ↓
    UI thread je VOLNÝ pro user events
         ↓
    Inference skončí v background threadu
         ↓
    Worker emituje resultReady signal
         ↓
    Main thread si signal connectne
         ↓
    Update UI s výsledky
"""

# ============================================================================

# 2. CORE COMPONENTS

# ============================================================================

"""
✓ InferenceWorker (core/workers/inference_worker.py)

- QObject který běží v background QThread
- Emituje signály:
  - started: Inference se startuje
  - progressUpdate(int): Pokrok 0-100%
  - resultReady(dict): Výsledky
  - errorOccurred(str): Chyba
  - finished: Worker skončil

✓ WorkerManager (core/workers/inference_worker.py)

- Helper class pro management worker + thread lifecycle
- Jednoduchý API:
  - run_inference(model, image, session_id)
  - connect_signals(on_result=..., on_error=..., etc)
  - stop()
  - is_running()

✓ Test Harness (core/workers/test_worker.py)

- Testuje QThread bez GUI
- Ověřuje signal flow
- Validuje threading model
"""

# ============================================================================

# 3. PHASE 4 INTEGRATION - Jak to zaintegovat do session_screen.py

# ============================================================================

"""
ZMĚNY V session_screen.py:

1. Import na začátku:

   from core.workers.inference_worker import WorkerManager
   from core.models.initialize_models import initialize_models

2. V __init__:

   # App startup (jedenkrát)

   initialize_models()  # Zaregistruj modely

   # Per-session

   self.worker_manager = WorkerManager()

3. Nahraď on_inference_clicked():

   def on_inference_clicked(self):
       # Stare:
       # inference_json = self.ml_inference.predict(self.current_image_path)

       # Nové:
       if not self.image_confirmed or not self.current_image_path:
           return

       # Disable button - inference běží
       self.inference_button.setText("Inference běží...")
       self.inference_button.setEnabled(False)

       # Spusť inference v background threadu
       self.worker_manager.run_inference(
           model_name='preview',  # nebo z combobox
           image_path=self.current_image_path,
           session_id=self.session_name
       )

       # Connect signály na callbacks
       self.worker_manager.connect_signals(
           on_started=self._on_inference_started,
           on_progress=self._on_inference_progress,
           on_result=self._on_inference_result,
           on_error=self._on_inference_error,
           on_finished=self._on_inference_finished
       )

4. Přidej signal handlers:

   def _on_inference_started(self):
       logger.info("Inference started in background")
       # Show progress indicator
       self.inference_button.setText("⟳ 0%")

   def _on_inference_progress(self, pct):
       logger.debug(f"Progress: {pct}%")
       # Update progress bar
       self.inference_button.setText(f"⟳ {pct}%")

   def _on_inference_result(self, data):
       if data.get('status') == 'success':
           result = data.get('result')  # LabelMe JSON

           # Zpracuj jako dřív
           vertebral_results = self.io_handler.parse_inference_output(result)

           current_model = self.model_combo.currentText()
           self.inference_results_by_model[current_model] = vertebral_results

           if self.current_pixmap:
               self.canvas_panel.set_image(self.current_pixmap)
               self.canvas_panel.set_vertebral_points(vertebral_results)

           self.vertebral_panel.set_vertebral_data(vertebral_results)
           self.inference_completed = True

           self.xray_stack.setCurrentIndex(1)
           self.menu_buttons["Body"].click()

           logger.info("✓ Inference completed and UI updated")

   def _on_inference_error(self, error_msg):
       logger.error(f"Inference error: {error_msg}")
       self.inference_button.setText("✗ Chyba")
       self.inference_button.setEnabled(True)

       # Show error dialog
       from PySide6.QtWidgets import QMessageBox
       QMessageBox.critical(self, "Inference Error", error_msg)

   def _on_inference_finished(self):
       logger.info("Inference worker finished")
       if self.inference_completed:
           self.inference_button.setText("✓ Inference hotova")
           self.inference_button.setEnabled(False)
       else:
           self.inference_button.setText("🔄 Inference")
           self.inference_button.setEnabled(True)
"""

# ============================================================================

# 4. SIGNAL FLOW DIAGRAM

# ============================================================================

"""
TIMELINE co se stane:

T0: User clicks "Inference" button

    Main Thread                      Background Thread
    ─────────────────────────────────────────────────

    on_inference_clicked()
    │
    ├─→ worker_manager.run_inference()
    │   ├─→ Create InferenceWorker
    │   ├─→ Create QThread
    │   ├─→ moveToThread()
    │   └─→ thread.start()  [START BACKGROUND THREAD]
    │
    ├─→ connect_signals()
    │   └─→ Connect all signals
    │
    └─→ Return immediately
        (UI CONTINUES TO RESPOND!)
                                    ↓
                                    InferenceWorker.run()
                                    │
                                    ├─→ started.emit()  →→→→→ MAIN THREAD
                                    │
                                    ├─→ Get model
                                    │
                                    ├─→ progressUpdate.emit(30)  →→→→→ MAIN THREAD
                                    │
                                    ├─→ model.predict()  [HEAVY COMPUTATION]
                                    │   (5-30 sekund tady)
                                    │
                                    ├─→ progressUpdate.emit(100)
                                    │
                                    ├─→ resultReady.emit(result)  →→→→→ MAIN THREAD
                                    │
                                    └─→ finished.emit()  →→→→→ MAIN THREAD
                                        (thread.quit())

T1: Result arrives in Main Thread

    Main Thread
    ─────────────────────────────────────────────────

    _on_inference_result(data)
    │
    ├─→ Parse JSON
    ├─→ Update canvas
    ├─→ Update points table
    └─→ Update UI elements
"""

# ============================================================================

# 5. ERROR HANDLING & ROBUSTNESS

# ============================================================================

"""
Graceful Error Handling:

1. Model load fails in background thread:
   ✓ errorOccurred signal emituje error msg
   ✓ Main thread si signal connectne
   ✓ _on_inference_error() shows error dialog
   ✓ UI state back to normal

2. Inference crashes:
   ✓ Try-catch v worker.run()
   ✓ Emituje errorOccurred
   ✓ finished signal i v error case
   ✓ Thread cleanup automatic

3. User closes session během inference:
   ✓ manager.stop() zastaví worker
   ✓ thread.quit() a thread.wait()
   ✓ Model unloaded from memory
   ✓ No dangling threads

4. Model already loaded (cached):
   ✓ manager.get_model() vrátí cached instanci
   ✓ Inference startuje hned (no reload delay)
   ✓ Per-session instances - izolace
"""

# ============================================================================

# 6. PERFORMANCE NOTES

# ============================================================================

"""
Benchmarks (Expected):

Preview Model:

- Load time: 0 ms (pure Python, no ML library)
- Inference time: < 100 ms
- Total: < 100 ms

Atlas UNet Model (When available):

- Load time: 1-2 seconds (PyTorch initialization)
- Inference time: 5-30 seconds (GPU dependent)
- Total: 6-32 seconds

UI Responsiveness:

- Old system: FROZEN for 5-30 seconds
- New system: RESPONSIVE throughout

Benefits:
✓ Progress indication (update UI during inference)
✓ Can cancel inference (future feature)
✓ Can have multiple sessions inferencing in parallel
✓ Better user experience
"""

# ============================================================================

# 7. TESTING

# ============================================================================

"""
Testing Strategy:

1. Unit test: core/models/test_models.py
   ✓ Registry, Manager (no threading)
   ✓ Model inference (synchronously)
   ✓ Run: python -m core.models.test_models

2. QThread test: core/workers/test_worker.py
   ✓ InferenceWorker (async)
   ✓ WorkerManager (signal flow)
   ✓ Signal connectivity
   ✓ Run: python -m core.workers.test_worker

3. Integration test: Manual in UI
   ✓ Click inference button
   ✓ UI stays responsive
   ✓ Progress indicator updates
   ✓ Results display correctly
   ✓ Next: Phase 4 implementation
"""

# ============================================================================

# 8. NEXT STEPS - Phase 4

# ============================================================================

"""
PHASE 4: UI INTEGRATION

Files to modify:

1. ui/session_screen.py:
   - Import initialize_models, WorkerManager
   - Call initialize_models() at app startup
   - Replace on_inference_clicked() with async version
   - Add signal handler methods
   - Update model_combo to use registry

2. main.py:
   - Call initialize_models() in main() before MainWindow

Files to create:

- core/workers/progress_dialog.py (Optional)
  - Show inference progress dialog
  - Cancel button

Expected result:
✓ Inference doesn't freeze UI anymore
✓ Progress indication during inference
✓ Better user experience
✓ Multi-session parallel inference possible
"""

# ============================================================================

# 9. TROUBLESHOOTING PHASE 4

# ============================================================================

"""
Q: Signals not firing?
A: Ensure QApplication.exec() runs in main thread.
   InferenceWorker lives in worker thread, signals route through Qt event system.

Q: Worker thread not cleaning up?
A: Call manager.stop() on window close.
   Or rely on automatic cleanup via deleteLater().

Q: Inference seems slower with threading?
A: Lazy-loading model adds overhead on first run.
   Second+ invocations will be faster (cached model).

Q: Multiple sessions inferencing - will they interfere?
A: No! Each session_id has separate model instance in manager.
   Thread-safe via mutex in ModelManager.

Q: How to cancel running inference?
A: Call manager.stop() - queues worker stop flag.
   Thread quits gracefully.
"""
