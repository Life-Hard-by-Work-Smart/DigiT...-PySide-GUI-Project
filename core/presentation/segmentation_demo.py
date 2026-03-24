"""Prezentační dialog simulující průběh segmentace obratlů (proof of concept)."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

_DEMO_DIR = Path(__file__).parent.parent.parent / "resources" / "demo"

_STEPS = [
    {
        "title": "Krok 1 / 4 — Načítání snímku",
        "image": None,
        "description": "Načítám RTG snímek a připravuji data pro zpracování...",
    },
    {
        "title": "Krok 2 / 4 — Segmentace obratlů",
        "image": _DEMO_DIR / "01_segmentation_overlay.png",
        "description": (
            "Model identifikuje obratle C2–C7 a vytváří barevný segmentační překryv "
            "nad původním RTG snímkem."
        ),
    },
    {
        "title": "Krok 3 / 4 — Segmentační maska",
        "image": _DEMO_DIR / "02_segmentation_mask.png",
        "description": "Generování binární masky jednotlivých obratlů.",
    },
    {
        "title": "Krok 4 / 4 — Detekce klíčových bodů",
        "image": _DEMO_DIR / "03_keypoints_labels.png",
        "description": (
            "Extrakce klíčových bodů (top left, top right, bottom left, bottom right) "
            "pro každý obratel C2–C7."
        ),
    },
]


class SegmentationDemoDialog(QDialog):
    """Krokový dialog zobrazující průběh segmentace (hardcoded demo)."""

    _IMAGE_MAX = 520  # px – maximální rozměr obrázku

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Segmentace — průběh zpracování")
        self.setModal(True)
        self.setMinimumWidth(600)
        self._step = 0
        self._build_ui()
        self._update_step()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignCenter)
        font = self._title_label.font()
        font.setPointSize(13)
        font.setBold(True)
        self._title_label.setFont(font)
        root.addWidget(self._title_label)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image_label.setMinimumHeight(300)
        root.addWidget(self._image_label, stretch=1)

        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setAlignment(Qt.AlignCenter)
        desc_font = self._desc_label.font()
        desc_font.setPointSize(10)
        self._desc_label.setFont(desc_font)
        root.addWidget(self._desc_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._next_btn = QPushButton("Další →")
        self._next_btn.setFixedHeight(36)
        self._next_btn.setMinimumWidth(110)
        self._next_btn.clicked.connect(self._on_next)
        btn_row.addWidget(self._next_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------

    def _update_step(self):
        step = _STEPS[self._step]
        self._title_label.setText(step["title"])
        self._desc_label.setText(step["description"])

        img_path = step["image"]
        if img_path and Path(img_path).exists():
            pixmap = QPixmap(str(img_path))
            scaled = pixmap.scaled(
                self._IMAGE_MAX,
                self._IMAGE_MAX,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)
        else:
            self._image_label.setPixmap(QPixmap())
            self._image_label.setText("[ načítám... ]" if img_path is None else "[ obrázek není k dispozici ]")

        is_last = self._step == len(_STEPS) - 1
        self._next_btn.setText("Dokončit" if is_last else "Další →")

    def _on_next(self):
        if self._step < len(_STEPS) - 1:
            self._step += 1
            self._update_step()
        else:
            self.accept()
