"""
QThread-based Inference Worker

Umožňuje spuštění inference bez blokování UI thread.

Architektura:
1. Main thread (UI) vytvoří InferenceWorker
2. Přesune worker na QThread
3. Zavolá worker.start()
4. Worker běží v Background threadu
5. Emituje signály (progress, result, error) do main thread
6. Main thread si signály connectne a updates UI
"""

from typing import Dict, Any, Optional
from PySide6.QtCore import QThread, Signal, QObject
import traceback

from core.models.model_manager import ModelManager
from logger import logger


class InferenceWorker(QObject):
    """
    Worker pro spuštění inference v background threadu.

    Komunikuje s main thread přes signály (thread-safe).

    Signály:
    - started: Inference se startuje
    - progressUpdate: Pokrok inference (0-100%)
    - resultReady: Inference hotova, vrátí výsledky
    - errorOccurred: Chyba během inference
    - finished: Worker se končí (cleanup)
    """

    # Definuj signály
    started = Signal()
    progressUpdate = Signal(int)  # int: procenta (0-100)
    resultReady = Signal(dict)    # dict: {"status": "success", "keypoints": {...}, ...}
    errorOccurred = Signal(str)   # str: error message
    finished = Signal()

    def __init__(self, model_name: str, image_path: str, session_id: str, **kwargs):
        """
        Inicializuj worker

        Args:
            model_name: 'preview' nebo 'atlas_unet'
            image_path: Cesta k obrázku
            session_id: ID session pro model manager
            **kwargs: Další parametry pro model.predict()
        """
        super().__init__()

        self.model_name = model_name
        self.image_path = image_path
        self.session_id = session_id
        self.kwargs = kwargs

        self.manager = ModelManager.get_instance()
        self._is_running = False

        logger.info(
            f"✓ InferenceWorker created: model={model_name}, "
            f"session={session_id}, image={image_path}"
        )

    def run(self):
        """
        Main worker loop - volá se automaticky když QThread.start()

        Toto běží v BACKGROUND threadu!
        """
        try:
            # Emit started signal
            self.started.emit()
            self._is_running = True
            logger.info(f"▶ Worker.run() started in background thread")

            # Update progress
            self.progressUpdate.emit(10)  # Loading model...

            # Get model (lazy-loads if needed)
            logger.debug(f"Loading model '{self.model_name}'...")
            model = self.manager.get_model(self.model_name, self.session_id)

            self.progressUpdate.emit(30)  # Model loaded, running inference...

            # Run inference
            logger.debug(f"Running inference on {self.image_path}...")
            result = model.predict(self.image_path)

            self.progressUpdate.emit(80)  # Post-processing...

            # Check result
            if result is None:
                logger.warning("Inference returned None")
                self.resultReady.emit({
                    'status': 'error',
                    'error': 'Model returned None'
                })
            else:
                logger.info(f"✓ Inference succeeded")
                self.resultReady.emit({
                    'status': 'success',
                    'result': result
                })

            self.progressUpdate.emit(100)  # Done

        except Exception as e:
            logger.error(f"✗ Inference failed: {str(e)}")
            logger.debug(traceback.format_exc())

            self.errorOccurred.emit(str(e))

        finally:
            self._is_running = False
            self.finished.emit()
            logger.info(f"✓ Worker.run() finished")

    def stop(self):
        """Zastavit worker (graceful shutdown)"""
        logger.info(f"Stopping worker...")
        self._is_running = False


class WorkerManager:
    """
    Helper pro management InferenceWorker + QThread

    Jednoduchý interface pro spuštění async inference.

    Typické použití:
        manager = WorkerManager()
        manager.run_inference(
            model_name='preview',
            image_path='path/to/image.png',
            session_id='session_001'
        )
        manager.connect_signals(
            on_result=lambda r: print(r),
            on_error=lambda e: print(f"Error: {e}")
        )
    """

    def __init__(self):
        """Initialize manager"""
        self.worker: Optional[InferenceWorker] = None
        self.thread: Optional[QThread] = None
        logger.info("✓ WorkerManager created")

    def run_inference(self,
                     model_name: str,
                     image_path: str,
                     session_id: str,
                     **kwargs) -> None:
        """
        Spusť inference v background threadu

        Args:
            model_name: 'preview' nebo 'atlas_unet'
            image_path: Cesta k obrázku
            session_id: ID session
            **kwargs: Další parametry
        """
        # Stop stary worker pokud je
        if self.worker is not None:
            self.stop()

        # Create worker
        self.worker = InferenceWorker(model_name, image_path, session_id, **kwargs)

        # Create thread
        self.thread = QThread()

        # Move worker do thread
        self.worker.moveToThread(self.thread)

        # Connect start signal
        self.thread.started.connect(self.worker.run)

        # Connect finish signal
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Start thread
        self.thread.start()

        logger.info(
            f"✓ Inference started in background: {model_name} / {session_id}"
        )

    def connect_signals(self,
                       on_started: Optional[callable] = None,
                       on_progress: Optional[callable] = None,
                       on_result: Optional[callable] = None,
                       on_error: Optional[callable] = None,
                       on_finished: Optional[callable] = None) -> None:
        """
        Connect worker signály na callbacks

        Args:
            on_started: Callback když se inference startuje
            on_progress: Callback na progress update (int: 0-100)
            on_result: Callback na результат (dict)
            on_error: Callback na error (str)
            on_finished: Callback když se worker končí
        """
        if self.worker is None:
            logger.warning("No worker running - no signals to connect")
            return

        if on_started:
            self.worker.started.connect(on_started)

        if on_progress:
            self.worker.progressUpdate.connect(on_progress)

        if on_result:
            self.worker.resultReady.connect(on_result)

        if on_error:
            self.worker.errorOccurred.connect(on_error)

        if on_finished:
            self.worker.finished.connect(on_finished)

        logger.info("✓ Signals connected")

    def stop(self) -> None:
        """Zastavit worker a počkat na QThread shutdown"""
        if self.worker is None:
            return

        logger.info("Stopping worker and thread...")
        self.worker.stop()

        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
            logger.info("✓ Thread stopped")

        self.worker = None
        self.thread = None

    def is_running(self) -> bool:
        """Ověř, že worker běží"""
        if self.worker is None:
            return False

        return self.worker._is_running

    def __del__(self):
        """Cleanup na konci"""
        self.stop()
