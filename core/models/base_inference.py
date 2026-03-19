"""Abstraktní interface pro ML inference modely"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseMLInference(ABC):
    """Abstraktní base class pro všechny ML inference modely

    Každý model (ať je to PyTorch, TensorFlow, atd.) musí implementovat
    tuto rozhraní. UI nemusí vědět jaký model je pod tím.

    Input: obrázek (cesta)
    Output: JSON s detekovanými body (maskhat format)
    """

    @abstractmethod
    def predict(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Spusť inference na obrázku.

        Args:
            image_path: Cesta k obrázku
            **kwargs: Další parametry specifické pro model (confidence, atd.)

        Returns:
            JSON dict s maskhat formatem (shapes array) nebo None
            {
                "shapes": [
                    {"label": "C2 top left", "points": [[x, y]]},
                    ...
                ]
            }
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Vrátí jméno modelu"""
        pass

    def get_model_description(self) -> str:
        """Vrátí popis modelu (volitelné)"""
        return self.get_model_name()
