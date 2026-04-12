"""
Model Registry - Centrální evidence dostupných ML modelů

Umožňuje:
- Registraci nových modelů bez změny kódu
- Zjištění které modely jsou dostupné
- Dynamic loading modelů
- Per-session instance vytváření
"""

from typing import Dict, Type, Optional
from core.models.base_inference import BaseMLInference
from logger import logger


class ModelRegistry:
    """
    Singleton registry pro všechny dostupné ML modely.

    Registruje modely a jejich konfigurace.
    Umožňuje query na dostupné modely.
    """

    _instance: Optional['ModelRegistry'] = None
    _models: Dict[str, Dict] = {}  # {model_name: {class, config, enabled}}

    def __new__(cls):
        """Singleton pattern - jen jedna instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize registry (volá se jen poprvé)"""
        if self._initialized:
            return

        self._models = {}
        self._initialized = True
        logger.info("✓ ModelRegistry initialized")

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
        registry = cls()

        if not issubclass(model_class, BaseMLInference):
            raise TypeError(f"{model_class.__name__} must inherit from BaseMLInference")

        registry._models[model_name] = {
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
        registry = cls()

        if model_name not in registry._models:
            available = cls.list_models()
            raise ValueError(
                f"Model '{model_name}' not found. Available: {available}"
            )

        model_info = registry._models[model_name]
        if not model_info['enabled']:
            raise ValueError(f"Model '{model_name}' is disabled")

        return model_info['class']

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict:
        """Vrátí konfiguraci modelu"""
        registry = cls()

        if model_name not in registry._models:
            raise ValueError(f"Model '{model_name}' not registered")

        return registry._models[model_name]['config']

    @classmethod
    def list_models(cls) -> list[str]:
        """Vrátí seznam všech registrovaných modelů"""
        registry = cls()
        return list(registry._models.keys())

    @classmethod
    def list_enabled_models(cls) -> list[str]:
        """Vrátí seznam enabled modelů"""
        registry = cls()
        return [
            name for name, info in registry._models.items()
            if info['enabled']
        ]

    @classmethod
    def is_model_available(cls, model_name: str) -> bool:
        """Ověří, že model existuje a je enabled"""
        registry = cls()

        if model_name not in registry._models:
            return False

        return registry._models[model_name]['enabled']

    @classmethod
    def disable_model(cls, model_name: str) -> None:
        """Zakaž model bez smazání"""
        registry = cls()

        if model_name not in registry._models:
            raise ValueError(f"Model '{model_name}' not registered")

        registry._models[model_name]['enabled'] = False
        logger.info(f"⊘ Model '{model_name}' disabled")

    @classmethod
    def enable_model(cls, model_name: str) -> None:
        """Znovu přivolej model"""
        registry = cls()

        if model_name not in registry._models:
            raise ValueError(f"Model '{model_name}' not registered")

        registry._models[model_name]['enabled'] = True
        logger.info(f"✓ Model '{model_name}' enabled")
