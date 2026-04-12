"""
Model Initialization - Registruje dostupné modely v registry

Měl by být volán NA POČÁTKU aplikace (v main.py nebo config.py)
"""

from core.models.registry import ModelRegistry
from core.models.preview.preview_model import MLInferenceSimulator
from logger import logger


def initialize_models() -> None:
    """
    Registruj všechny dostupné modely v centrálním registry

    Volej toto na startu aplikace jednou:
        from core.models.initialize_models import initialize_models
        initialize_models()

    Poté můžeš modelů přistupovat přes:
        manager = ModelManager.get_instance()
        model = manager.get_model('atlas_unet', session_id='sess_001')
    """

    logger.info("━" * 60)
    logger.info("Registering ML Models...")
    logger.info("━" * 60)

    # ========== PREVIEW MODEL (SIMULATOR) ==========
    try:
        ModelRegistry.register(
            model_name='preview',
            model_class=MLInferenceSimulator,
            config={},
            enabled=True
        )
        logger.info("✓ Preview (Simulator) model registered")

    except Exception as e:
        logger.error(f"✗ Failed to register Preview model: {e}")

    # ========== ATLAS UNET MODEL ==========
    try:
        # Import se dělá tady (lazy), ne na začátku, aby se nepřetahoval torch
        from core.models.atlas_unet.atlas_model import AtlasUNetModel

        ModelRegistry.register(
            model_name='atlas_unet',
            model_class=AtlasUNetModel,
            config={'device': 'cpu'},  # CPU inference (no CUDA available on this system)
            enabled=True
        )
        logger.info("✓ Atlas UNet model registered")

    except Exception as e:
        logger.warning(f"⚠ Atlas UNet model registration failed: {e}")
        logger.info("  (This is OK if you don't have PyTorch/MONAI installed)")

    # ========== PRINT SUMMARY ==========
    available = ModelRegistry.list_enabled_models()
    logger.info("━" * 60)
    logger.info(f"Models ready: {available}")
    logger.info("━" * 60)
