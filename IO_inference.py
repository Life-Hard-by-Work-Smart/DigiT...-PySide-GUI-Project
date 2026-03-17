import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any


class InferenceSimulator:
    """Simulátor inference pipeline - ověřuje testovací obrázek a vrací predefinované výsledky"""

    def __init__(self, test_image_path: str, expected_results_path: str):
        """
        Inicializuj simulátor s cestami k testovacímu obrázku a výsledkům.

        Args:
            test_image_path: Cesta k testovacímu obrázku pro validaci
            expected_results_path: Cesta k JSON souboru s očekávanými výsledky
        """
        self.test_image_path = Path(test_image_path)
        self.expected_results_path = Path(expected_results_path)
        self.test_image_hash = None
        self.expected_results = None

        self._load_test_image_hash()
        self._load_expected_results()

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
        """Vypočítej SHA256 hash nahraného obrázku"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Obrázek nenalezen: {image_path}")

        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run_inference(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Spusť simulaci inference.

        Ověří, zda je nahraný obrázek shodný s testovacím obrázkem.
        Pokud ano, vrátí JSON s očekávanými výsledky.

        Args:
            image_path: Cesta k nahranimu obrázku

        Returns:
            Dict s výsledky, pokud je obrázek validní, jinak None
        """
        try:
            # Vypočítej hash nahraniho obrázku
            uploaded_hash = self._calculate_image_hash(image_path)

            # Porovnáj s testovacím obrázkem
            if uploaded_hash == self.test_image_hash:
                print("[Inference] ✓ Obrázek je validní testovací obrázek")
                return self.expected_results
            else:
                print("[Inference] ✗ Obrázek se nejedná o testovací obrázek")
                return None

        except FileNotFoundError as e:
            print(f"[Inference] Chyba: {e}")
            return None
        except Exception as e:
            print(f"[Inference] Neočekávaná chyba: {e}")
            return None

    def get_results_as_json(self, image_path: str) -> Optional[str]:
        """
        Spusť inference a vrátí výsledky jako JSON string.

        Args:
            image_path: Cesta k nahranimu obrázku

        Returns:
            JSON string s výsledky nebo None
        """
        results = self.run_inference(image_path)
        if results:
            return json.dumps(results, indent=2, ensure_ascii=False)
        return None


def inference_simulation(image_path: str, test_image_path: str, results_json_path: str) -> Optional[Dict[str, Any]]:
    """
    Pomocná funkce pro spuštění inference simulace.

    Args:
        image_path: Cesta k nahranimu obrázku
        test_image_path: Cesta k testovacímu obrázku
        results_json_path: Cesta k JSON souboru s výsledky

    Returns:
        Dict s výsledky nebo None
    """
    simulator = InferenceSimulator(test_image_path, results_json_path)
    return simulator.run_inference(image_path)
