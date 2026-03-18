"""ML inference simulator - implementace BaseMLInference pro testování"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

from core.models.base_inference import BaseMLInference
from config import TEST_IMAGE_PATH, TEST_RESULTS_PATH
from logger import logger


class MLInferenceSimulator(BaseMLInference):
    """Simulátor ML inference - má stejný interface jako opravdový ML model

    Používá se pro testování. ML tým bude vytvářet podtřídy s opravdovými modely.

    Input: obrázek (cesta)
    Output: JSON s detekovanými body (maskhat format)
    """

    def __init__(self):
        """Inicializuj ML simulátor - automaticky najde testovací data"""
        self.test_image_path = TEST_IMAGE_PATH
        self.expected_results_path = TEST_RESULTS_PATH
        self.test_image_hash = None
        self.expected_results = None

        try:
            self._load_test_image_hash()
            self._load_expected_results()
            logger.info("MLInferenceSimulator inicializován")
        except FileNotFoundError as e:
            logger.error(f"Chyba při inicializaci MLInferenceSimulator: {e}")
            raise

    def _load_test_image_hash(self) -> None:
        """Načti hash testovacího obrázku pro porovnání"""
        if not self.test_image_path.exists():
            raise FileNotFoundError(f"Testovací obrázek nenalezen: {self.test_image_path}")

        with open(self.test_image_path, "rb") as f:
            self.test_image_hash = hashlib.sha256(f.read()).hexdigest()

    def _load_expected_results(self) -> None:
        """Načti očekávané výsledky z JSON souboru"""
        if not self.expected_results_path.exists():
            raise FileNotFoundError(f"JSON soubor s výsledky nenalezen: {self.expected_results_path}")

        with open(self.expected_results_path, "r", encoding="utf-8") as f:
            self.expected_results = json.load(f)

    def _calculate_image_hash(self, image_path: str) -> str:
        """Vypočítej SHA256 hash obrázku"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Obrázek nenalezen: {image_path}")

        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    @staticmethod
    def _get_sample_results() -> Dict[str, Any]:
        """Vygeneruj sample JSON výsledky pro fallback

        Returns:
            JSON s maskhat formatem (shapes array)
        """
        sample_json = {
            "shapes": [
                # C2
                {"label": "C2 top left", "points": [[125.50, 180.75]]},
                {"label": "C2 top right", "points": [[225.30, 182.10]]},
                {"label": "C2 centroid", "points": [[128.80, 265.40]]},
                # C3
                {"label": "C3 top left", "points": [[130.20, 275.60]]},
                {"label": "C3 top right", "points": [[220.90, 278.30]]},
                {"label": "C3 bottom left", "points": [[132.50, 360.15]]},
                {"label": "C3 bottom right", "points": [[218.75, 362.95]]},
                # C4
                {"label": "C4 top left", "points": [[128.95, 370.10]]},
                {"label": "C4 top right", "points": [[222.15, 372.80]]},
                {"label": "C4 bottom left", "points": [[131.60, 455.25]]},
                {"label": "C4 bottom right", "points": [[219.40, 458.05]]},
            ]
        }
        return sample_json

    def predict(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Spusť ML inference na obrázku (simulace).

        Interface kompatibilní s opravdovým ML modelem.

        Args:
            image_path: Cesta k obrázku
            **kwargs: Další parametry specifické pro model

        Returns:
            JSON dict s maskhat formatem (shapes array) nebo None
        """
        try:
            # Vypočítej hash obrázku
            uploaded_hash = self._calculate_image_hash(image_path)

            # Porovnáj s testovacím obrázkem
            if uploaded_hash == self.test_image_hash:
                logger.info("✓ Obrázek je validní testovací obrázek - vráceny expected results")
                return self.expected_results
            else:
                logger.info("✗ Obrázek se nejedná o testovací obrázek - vrácena sample data")
                return self._get_sample_results()

        except FileNotFoundError as e:
            logger.warning(f"Soubor nenalezen: {e} - fallback na sample data")
            return self._get_sample_results()
        except Exception as e:
            logger.error(f"Neočekávaná chyba při inference: {e} - fallback na sample data")
            return self._get_sample_results()

    def get_model_name(self) -> str:
        """Vrátí jméno modelu"""
        return "ML Inference Simulator"
