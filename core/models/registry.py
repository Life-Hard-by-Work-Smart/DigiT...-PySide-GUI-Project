"""
Model Registry - Centrální evidence dostupných ML modelů

Umožňuje:
- Registraci nových modelů bez změny kódu
- Zjištění které modely jsou dostupné
- Dynamic loading modelů
- Per-session instance vytváření
"""

from typing import Dict, Type, Optional
from threading import Lock
from core.models.base_inference import BaseMLInference
from logger import logger


class ModelRegistry:
    """
    Singleton registry pro všechny dostupné ML modely.

    Registruje modely a jejich konfigurace.
    Umožňuje query na dostupné modely.
    """

    _instance: Optional['ModelRegistry'] = None
    _models: Dict[str, Dict] = {}  # {model_name: {class, config, enabled}} - CLASS LEVEL!
    _lock: Lock = Lock()
    _initialized: bool = False  # CLASS LEVEL!

    def __new__(cls):
        """Singleton pattern - jen jedna instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize registry - NE, init se dělá jen v register"""
        # Registry se inicilizuje když se zavolá register()
        pass

    @classmethod
    def register(cls,
                 model_name: str,
                 model_class: Type[BaseMLInference],
                 config: Optional[Dict] = None,
                 enabled: bool = True) -> None:
        """
        Zaregistruj nový model v registry

        Args:
            model_name: Identifier modelu (např. "atlas_unet", "preview")
            model_class: Třída implementující BaseMLInference
            config: Optional config dict (např. model-specific paths, hyperparams)
            enabled: Je model dostupný? (umožňuje disable bez smazání)
        """
        with cls._lock:
            if not issubclass(model_class, BaseMLInference):
                raise TypeError(f"{model_class.__name__} must inherit from BaseMLInference")

            # Ulož přímo do class-level _models (thread-safe s lockem)
            cls._models[model_name] = {
                'class': model_class,
                'config': config or {},
                'enabled': enabled
            }

            logger.info(f"✓ Model '{model_name}' registered: {model_class.__name__}")

    @classmethod
    def get_model_class(cls, model_name: str) -> Type[BaseMLInference]:
        """
        Vrátí model třídu

        Args:
            model_name: Identifier modelu

        Returns:
            Model class implementující BaseMLInference

        Raises:
            ValueError: Pokud model neexistuje nebo je disabled
        """
        logger.info(f"[Registry.get_model_class] Looking for model '{model_name}'")
        logger.info(f"[Registry.get_model_class] _models content: {list(cls._models.keys())}")
        logger.info(f"[Registry.get_model_class] _models details: {cls._models}")

        if model_name not in cls._models:
            available = cls.list_models()
            logger.error(f"[Registry] Model '{model_name}' NOT FOUND in cls._models. Available: {available}")
            raise ValueError(
                f"Model '{model_name}' not found. Available: {available}"
            )

        model_info = cls._models[model_name]
        if not model_info['enabled']:
            raise ValueError(f"Model '{model_name}' is disabled")

        return model_info['class']

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict:
        """Vrátí konfiguraci modelu"""
        if model_name not in cls._models:
            raise ValueError(f"Model '{model_name}' not registered")

        return cls._models[model_name]['config']

    @classmethod
    def list_models(cls) -> list[str]:
        """Vrátí seznam všech registrovaných modelů"""
        return list(cls._models.keys())

    @classmethod
    def list_enabled_models(cls) -> list[str]:
        """Vrátí seznam enabled modelů"""
        return [
            name for name, info in cls._models.items()
            if info['enabled']
        ]

    @classmethod
    def is_model_available(cls, model_name: str) -> bool:
        """Ověří, že model existuje a je enabled"""
        if model_name not in cls._models:
            return False

        return cls._models[model_name]['enabled']

    @classmethod
    def disable_model(cls, model_name: str) -> None:
        """Zakaž model bez smazání"""
        registry = cls()


        if model_name not in cls._models:
            raise ValueError(f"Model '{model_name}' not registered")

        cls._models[model_name]['enabled'] = False
        logger.info(f"⊘ Model '{model_name}' disabled")

    @classmethod
    def enable_model(cls, model_name: str) -> None:
        """Znovu přivolej model"""
        if model_name not in cls._models:
            raise ValueError(f"Model '{model_name}' not registered")

        cls._models[model_name]['enabled'] = True
        logger.info(f"✓ Model '{model_name}' enabled")

