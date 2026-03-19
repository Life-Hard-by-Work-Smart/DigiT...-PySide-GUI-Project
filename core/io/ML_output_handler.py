"""Zpracování výstupu z ML inference - transformace JSON na VertebralPoints"""

import json
import re
from typing import Optional, Dict, Any

from core.models.data_structures import Point, VertebralPoints
from logger import logger


class InferenceOutputHandler:
    """Zpracovává JSON výstup z ML inference (nebo ML simulátoru)

    Input: JSON s maskhat formatem (shapes array)
    Output: VertebralPoints objekty pro UI
    """

    @staticmethod
    def parse_inference_output(inference_json: Dict[str, Any]) -> list[VertebralPoints]:
        """Parsuj JSON výstup z ML inference do VertebralPoints objektů

        Args:
            inference_json: JSON dict s maskhat formatem (shapes array)

        Returns:
            Seznam VertebralPoints objektů
        """
        if not inference_json:
            return []

        vertebrals_dict = {}
        shapes = inference_json.get('shapes', [])

        for shape in shapes:
            label = shape.get('label', '').strip()
            points = shape.get('points', [])

            if not points or len(points) == 0:
                continue

            # Parsuj label - formát: "C2 top left", "C3 bottom right", atd.
            match = re.match(r'([A-Z]\d+)\s+(.*)', label)
            if not match:
                continue

            vertebral_name = match.group(1)  # C2, C3, ...

            # Inicializuj vertebral pokud neexistuje
            if vertebral_name not in vertebrals_dict:
                vertebrals_dict[vertebral_name] = VertebralPoints(name=vertebral_name, points=[])

            # Přidej bod s plným labelem
            x, y = points[0][0], points[0][1]
            point = Point(x=x, y=y, label=label, original_x=x, original_y=y)  # Phase 3.3: Ulož originální coords
            vertebrals_dict[vertebral_name].points.append(point)

        # Seřaď obratlů podle jména (C2, C3, C4, ...)
        vertebrals_list = sorted(vertebrals_dict.values(), key=lambda v: v.name)
        return vertebrals_list

    @staticmethod
    def load_from_json_file(json_path: str) -> list[VertebralPoints]:
        """Načti JSON výstup z souboru a zpracuj ho

        Args:
            json_path: Cesta k XXX_maskhat.json souboru

        Returns:
            Seznam VertebralPoints objektů
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"JSON soubor načten: {json_path}")
            return InferenceOutputHandler.parse_inference_output(data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Chyba při načítání JSON: {e}")
            return []
