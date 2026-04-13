"""
Model Manager - Lazy-loading model singleton manager

Spravuje:
- Lazy loading modelů (načte až když se poprvé použije)
- Singleton instance per model (thread-safe per session)
- Model lifecycle (init, cleanup, error handling)
- Thread-safe access s mutexem

Typické použití:
    manager = ModelManager.get_instance()
    model = manager.get_model('atlas_unet', session_id='session_001')
    result = model.infer(image_data)
"""

from typing import Dict, Optional, Any
from threading import Lock
import importlib

from core.models.registry import ModelRegistry
from core.models.base_inference import BaseMLInference
from logger import logger


class ModelManager:
    """
    Singleton manager pro model instances.

    Umožňuje:
    - Lazy loading modelů (nenačítá dokud se nepoužijí)
    - Per-session instances (každá session má vlastní instanci)
    - Thread-safe access s mutexem
    - Graceful error handling

    Architecture:
        _instances[model_name][session_id] = model_instance
    """

    _instance: Optional['ModelManager'] = None
    _lock: Lock = Lock()
    _instances: Dict[str, Dict[str, BaseMLInference]] = {}  # CLASS LEVEL - SHARED!
    _initialized: bool = False  # CLASS LEVEL!

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False

        return cls._instance

    def __init__(self):
        """Initialize manager - NE, vše je class-level"""
        # Nic se neděje - vše je inicializované na class-level
        pass

    @classmethod
    def get_instance(cls) -> 'ModelManager':
        """Get singleton instance"""
        return cls()

    def get_model(self,
                  model_name: str,
                  session_id: str = "default",
                  force_reload: bool = False) -> BaseMLInference:
        """
        Vrátí model instanci (lazy-loads pokud ještě není v paměti)

        Args:
            model_name: Identifier modelu (z registry)
            session_id: ID session (umožňuje per-session instances)
            force_reload: Reloadni model (smaž a znovu vytvoř)

        Returns:
            Model instance

        Raises:
            ValueError: Pokud model neexistuje/je disabled
            RuntimeError: Pokud model selže při inicializaci
        """
        with self._lock:
            # Initialize model dict if needed
            if model_name not in self._instances:
                self._instances[model_name] = {}

            # Check if already loaded
            if session_id in self._instances[model_name] and not force_reload:
                logger.debug(
                    f"↻ Using cached model '{model_name}' for session '{session_id}'"
                )
                return self._instances[model_name][session_id]

            # Force reload - delete old instance
            if force_reload and session_id in self._instances[model_name]:
                old_instance = self._instances[model_name][session_id]
                if hasattr(old_instance, 'cleanup'):
                    try:
                        old_instance.cleanup()
                        logger.info(f"⊘ Cleaned up old model '{model_name}' instance")
                    except Exception as e:
                        logger.warning(
                            f"⚠ Error cleaning up model '{model_name}': {e}"
                        )

                del self._instances[model_name][session_id]

            # Load new instance (lazy loading)
            logger.info(
                f"⟳ Lazy-loading model '{model_name}' for session '{session_id}'"
            )

            try:
                model_instance = self._load_model(model_name)
                self._instances[model_name][session_id] = model_instance

                logger.info(
                    f"✓ Model '{model_name}' loaded for session '{session_id}'"
                )

                return model_instance

            except Exception as e:
                logger.error(
                    f"✗ Failed to load model '{model_name}': {str(e)}"
                )
                raise RuntimeError(
                    f"Failed to initialize model '{model_name}': {str(e)}"
                ) from e

    def _load_model(self, model_name: str) -> BaseMLInference:
        """
        Interně: load a instantiate model

        Args:
            model_name: Model identifier z registry

        Returns:
            Initialized model instance
        """
        # Zjistí model třídu z registry
        model_class = ModelRegistry.get_model_class(model_name)

        # Zjistí config
        config = ModelRegistry.get_model_config(model_name)

        # Vytvoří instanci
        if config:
            model_instance = model_class(**config)
        else:
            model_instance = model_class()

        return model_instance

    def unload_model(self,
                     model_name: str,
                     session_id: str = "default") -> None:
        """
        Odebere model ze paměti (volá cleanup)

        Args:
            model_name: Model identifier
            session_id: Session ID
        """
        with self._lock:
            if model_name not in self._instances:
                logger.warning(f"Model '{model_name}' not loaded")
                return

            if session_id not in self._instances[model_name]:
                logger.warning(
                    f"Model '{model_name}' not loaded for session '{session_id}'"
                )
                return

            try:
                model_instance = self._instances[model_name][session_id]

                if hasattr(model_instance, 'cleanup'):
                    model_instance.cleanup()

                del self._instances[model_name][session_id]

                logger.info(
                    f"✓ Model '{model_name}' unloaded for session '{session_id}'"
                )

            except Exception as e:
                logger.error(
                    f"✗ Error unloading model '{model_name}': {e}"
                )

    def unload_all(self) -> None:
        """Unload všechny modely"""
        with self._lock:
            for model_name in list(self._instances.keys()):
                for session_id in list(self._instances[model_name].keys()):
                    try:
                        self.unload_model(model_name, session_id)
                    except Exception as e:
                        logger.error(
                            f"⚠ Error during cleanup: {e}"
                        )

            self._instances.clear()
            logger.info("✓ All models unloaded")

    def get_loaded_models(self) -> Dict[str, list[str]]:
        """Vrátí dict {model_name: [session_ids]}"""
        with self._lock:
            return {
                model_name: list(sessions.keys())
                for model_name, sessions in self._instances.items()
            }

    def is_model_loaded(self,
                       model_name: str,
                       session_id: str = "default") -> bool:
        """Ověř, že model je v paměti"""
        with self._lock:
            if model_name not in self._instances:
                return False

            return session_id in self._instances[model_name]

    def get_stats(self) -> str:
        """Vrátí statistics o loadnutých modelech"""
        with self._lock:
            total_models = len(self._instances)
            total_instances = sum(
                len(sessions) for sessions in self._instances.values()
            )

            details = []
            for model_name, sessions in self._instances.items():
                details.append(
                    f"  - {model_name}: {len(sessions)} instance(s) "
                    f"({list(sessions.keys())})"
                )

            stats = (
                f"ModelManager Stats:\n"
                f"  Total models loaded: {total_models}\n"
                f"  Total instances: {total_instances}\n"
            )

            if details:
                stats += "\n".join(details)

            return stats
