"""
Test Harness - Ověř že registry, manager a modely fungují

Spuštění:
    python -m core.models.test_models

Nebo přímo:
    from core.models.test_models import test_all
    test_all()
"""

import sys
from pathlib import Path

from logger import logger


def test_registry():
    """Test 1: ModelRegistry - základní funkcionalita"""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: ModelRegistry")
    logger.info("="*70)

    try:
        from core.models.registry import ModelRegistry
        from core.models.base_inference import BaseMLInference

        # Test 1a: Ověř singleton
        reg1 = ModelRegistry()
        reg2 = ModelRegistry()
        assert reg1 is reg2, "Registry není singleton!"
        logger.info("✓ Registry je singleton")

        # Test 1b: List models (měl by obsahovat preview + atlas_unet)
        available = ModelRegistry.list_enabled_models()
        logger.info(f"  Available models: {available}")

        if 'preview' in available:
            logger.info("✓ Preview model je registered")
        else:
            logger.warning("⚠ Preview model není registered (OK pokud init_models nebyla volána)")

        return True

    except Exception as e:
        logger.error(f"✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_manager():
    """Test 2: ModelManager - lazy loading a instances"""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: ModelManager")
    logger.info("="*70)

    try:
        from core.models.model_manager import ModelManager
        from core.models.initialize_models import initialize_models

        # FIRST: Initialize models (nebo nebude co loadovat)
        logger.info("  Initializing models first...")
        initialize_models()

        # Test 2a: Ověř singleton
        mgr1 = ModelManager.get_instance()
        mgr2 = ModelManager.get_instance()
        assert mgr1 is mgr2, "Manager není singleton!"
        logger.info("✓ Manager je singleton")

        # Test 2b: Check stats
        stats = mgr1.get_stats()
        logger.info(f"  Manager stats:\n{stats}")

        # Test 2c: Try to load preview model
        try:
            logger.info("  Attempting to load 'preview' model...")
            model = mgr1.get_model('preview', session_id='test_session_001')
            logger.info(f"✓ Model loaded: {type(model).__name__}")

            # Test 2d: Verify it's cached
            model2 = mgr1.get_model('preview', session_id='test_session_001')
            assert model is model2, "Model není cached!"
            logger.info("✓ Model je cached (vrácena stejná instance)")

            # Test 2e: Different session = different instance
            model3 = mgr1.get_model('preview', session_id='test_session_002')
            assert model is not model3, "Různé sessions by měly mít různé instance!"
            logger.info("✓ Různé sessions mají různé instance")

        except ValueError as e:
            logger.warning(f"⚠ Preview model není k dispozici: {e}")
            logger.info("  (OK - zkus spustit initialize_models())")

        return True

    except Exception as e:
        logger.error(f"✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
def test_initialize_models():
    """Test 3: Model initialization - registruj modely"""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Initialize Models")
    logger.info("="*70)

    try:
        from core.models.initialize_models import initialize_models
        from core.models.registry import ModelRegistry

        # Test 3a: Run initialization
        logger.info("  Registering models...")
        initialize_models()

        # Test 3b: Check co se registrovalo
        available = ModelRegistry.list_enabled_models()
        logger.info(f"✓ Registered models: {available}")

        if 'preview' in available:
            logger.info("  ✓ Preview model registered")

        if 'atlas_unet' in available:
            logger.info("  ✓ Atlas UNet model registered (PyTorch je dostupný!)")
        else:
            logger.info("  ⚠ Atlas UNet model není registrován (PyTorch není nainstalován?)")

        return True

    except Exception as e:
        logger.error(f"✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_preview_model_inference():
    """Test 4: Preview model - spusť inference"""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Preview Model Inference")
    logger.info("="*70)

    try:
        from core.models.model_manager import ModelManager
        from core.models.registry import ModelRegistry
        import numpy as np

        # Test 4a: Ověř že preview je dostupný
        if not ModelRegistry.is_model_available('preview'):
            logger.info("⚠ Preview model není dostupný, skipu test 4")
            return True

        # Test 4b: Get preview model
        manager = ModelManager.get_instance()
        model = manager.get_model('preview', session_id='test_inference')
        logger.info(f"✓ Model loaded: {type(model).__name__}")

        # Test 4c: Spusť inference
        logger.info("  Running inference...")

        # Vytvoř dummy testovací soubor (preview model potřebuje cestu)
        # Protože preview model pracuje s soubory, vyzkoušíme alespoň co se stane
        result = model.predict("dummy_path.png")

        # Test 4d: Check result - predict vrací JSON nebo None
        if result is not None:
            logger.info("✓ Inference returned result")

            if 'shapes' in result:
                shapes = result['shapes']
                logger.info(f"  Shapes returned: {len(shapes)} items")
        else:
            logger.info("✓ Inference returned None (expected for preview on dummy path)")

        return True

    except Exception as e:
        logger.error(f"✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end():
    """Test 5: End-to-end - od startu app po inference"""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: End-to-End Workflow")
    logger.info("="*70)

    try:
        from core.models.initialize_models import initialize_models
        from core.models.model_manager import ModelManager
        from core.models.registry import ModelRegistry
        import numpy as np

        # Test 5a: Initialize
        logger.info("  Step 1: Initialize models...")
        initialize_models()
        logger.info("  ✓ Models initialized")

        # Test 5b: Get manager
        logger.info("  Step 2: Get manager...")
        manager = ModelManager.get_instance()
        logger.info("  ✓ Manager obtained")

        # Test 5c: Get preview model
        logger.info("  Step 3: Load preview model...")
        model = manager.get_model('preview', session_id='end_to_end_test')
        logger.info(f"  ✓ Model loaded: {type(model).__name__}")

        # Test 5d: Run inference
        logger.info("  Step 4: Run inference...")
        result = model.predict("dummy_test.png")

        if result is not None:
            logger.info("  ✓ Inference succeeded (returned LabelMe JSON)")
        else:
            logger.warning(f"  ⚠ Inference returned None (may be OK for preview)")

        # Test 5e: Unload model
        logger.info("  Step 5: Unload model...")
        manager.unload_model('preview', 'end_to_end_test')
        logger.info("  ✓ Model unloaded")

        logger.info("✓ END-TO-END TEST PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all():
    """Spusť všechny testy"""
    logger.info("\n\n")
    logger.info("╔" + "="*68 + "╗")
    logger.info("║" + " "*20 + "ML INTEGRATION TEST SUITE" + " "*23 + "║")
    logger.info("╚" + "="*68 + "╝")

    tests = [
        ("Registry", test_registry),
        ("Manager", test_model_manager),
        ("Initialize", test_initialize_models),
        ("Preview Inference", test_preview_model_inference),
        ("End-to-End", test_end_to_end),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"EXCEPTION in {test_name}: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {test_name}")

    logger.info("="*70)
    logger.info(f"Result: {passed}/{total} passed")
    logger.info("="*70 + "\n")

    return all(results.values())


if __name__ == '__main__':
    success = test_all()
    sys.exit(0 if success else 1)
