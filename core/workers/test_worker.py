"""
Test Harness - InferenceWorker QThread testing

Testuje InferenceWorker bez UI. Spouští QThread, emituje signály,
ověřuje thread-safety a signal connectivity.

Spuštění:
    python -m core.workers.test_worker
"""

import sys
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from logger import logger

from core.models.initialize_models import initialize_models
from core.workers.inference_worker import InferenceWorker, WorkerManager


class TestRunner:
    """Runner pro QThread testy"""

    def __init__(self):
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        self.results = {}
        self.current_test = None

        logger.info("\n" + "="*70)
        logger.info("INFERENCEWOKER TEST SUITE (QThread Based)")
        logger.info("="*70)

    def test_1_simple_inference(self):
        """Test 1: Spusť jednoduchý worker s preview modelem"""
        self.current_test = "Simple Inference"
        logger.info("\n" + "="*70)
        logger.info(f"TEST 1: {self.current_test}")
        logger.info("="*70)

        try:
            # Setup
            initialize_models()

            # Create worker
            worker = InferenceWorker(
                model_name='preview',
                image_path='dummy.png',
                session_id='test_1'
            )

            # Track results
            results = {}

            def on_started():
                logger.info("✓ started signal received")
                results['started'] = True

            def on_progress(pct):
                logger.info(f"  Progress: {pct}%")
                results['progress'] = pct

            def on_result(data):
                logger.info(f"✓ resultReady signal received: status={data.get('status')}")
                results['result'] = data

            def on_error(msg):
                logger.error(f"✗ errorOccurred signal: {msg}")
                results['error'] = msg

            def on_finished():
                logger.info("✓ finished signal received")
                results['finished'] = True
                # Stop app after test
                QCoreApplication.quit()

            # Connect signals
            worker.started.connect(on_started)
            worker.progressUpdate.connect(on_progress)
            worker.resultReady.connect(on_result)
            worker.errorOccurred.connect(on_error)
            worker.finished.connect(on_finished)

            # Create thread and start
            from PySide6.QtCore import QThread
            thread = QThread()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)

            thread.start()

            # Run event loop (will be quit by on_finished)
            logger.info("  Running event loop...")
            self.app.exec()

            # Check results
            if results.get('started') and results.get('finished'):
                logger.info("✓ TEST 1 PASSED")
                self.results['Simple Inference'] = True
                return True
            else:
                logger.error("✗ TEST 1 FAILED: Missing signals")
                self.results['Simple Inference'] = False
                return False

        except Exception as e:
            logger.error(f"✗ TEST 1 FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.results['Simple Inference'] = False
            return False

    def test_2_worker_manager(self):
        """Test 2: WorkerManager - höher level API"""
        self.current_test = "WorkerManager"
        logger.info("\n" + "="*70)
        logger.info(f"TEST 2: {self.current_test}")
        logger.info("="*70)

        try:
            # Setup
            initialize_models()

            # Create manager
            manager = WorkerManager()

            # Track results
            results = {}

            def on_progress(pct):
                logger.info(f"  Progress: {pct}%")
                results['last_progress'] = pct

            def on_result(data):
                logger.info(f"✓ Result: {data.get('status')}")
                results['result'] = data

            def on_error(msg):
                logger.error(f"✗ Error: {msg}")
                results['error'] = msg

            def on_finished():
                logger.info("✓ Worker finished")
                results['finished'] = True
                QCoreApplication.quit()

            # Run inference
            manager.run_inference(
                model_name='preview',
                image_path='test.png',
                session_id='test_2'
            )

            # Connect signals
            manager.connect_signals(
                on_progress=on_progress,
                on_result=on_result,
                on_error=on_error,
                on_finished=on_finished
            )

            # Run event loop
            logger.info("  Running event loop...")
            self.app.exec()

            # Check results
            if results.get('finished') and (results.get('result') or results.get('error')):
                logger.info("✓ TEST 2 PASSED")
                self.results['WorkerManager'] = True
                return True
            else:
                logger.error("✗ TEST 2 FAILED: Incomplete workflow")
                self.results['WorkerManager'] = False
                return False

        except Exception as e:
            logger.error(f"✗ TEST 2 FAILED: {e}")
            import traceback
            traceback.print_exc()
            self.results['WorkerManager'] = False
            return False

    def run_all(self):
        """Spusť všechny testy"""
        logger.info("\nStarting tests...\n")

        try:
            self.test_1_simple_inference()
        except Exception as e:
            logger.error(f"Exception in test 1: {e}")
            self.results['Simple Inference'] = False

        # Restart app for next test
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

        try:
            self.test_2_worker_manager()
        except Exception as e:
            logger.error(f"Exception in test 2: {e}")
            self.results['WorkerManager'] = False

        # Summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)

        for test_name, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"  {status}: {test_name}")

        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)

        logger.info("="*70)
        logger.info(f"Result: {passed}/{total} passed")
        logger.info("="*70 + "\n")

        return all(self.results.values())


if __name__ == '__main__':
    runner = TestRunner()

    # Jednoduchý test bez event loop komplikací
    logger.info("\nNote: These tests use QThread and signals.")
    logger.info("For simpler testing without GUI, use core/models/test_models.py")

    try:
        runner.run_all()
        success = all(runner.results.values())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
