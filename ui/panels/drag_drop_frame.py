
from PySide6.QtWidgets import QFrame

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent, QColor


class DragDropFrame(QFrame):
    """Frame s drag-and-drop podporou pro snímky"""
    image_loaded = Signal(str)  # Signal - emituje cestu ke snímku

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.image_path = None
        # CRITICAL: Explicitně žádné margins aby se canvas zobrazil na plno
        self.setContentsMargins(0, 0, 0, 0)
        # CRITICAL: Žádné padding ve stylesheedu
        self.setStyleSheet("margin: 0px; padding: 0px; border: 0px;")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Když uživatel táhne soubor nad frame"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Když uživatel pustí soubor na frame"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            file_path = files[0]
            # Zkontroluj, jestli je to snímek
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.load_image(file_path)

    def load_image(self, file_path):
        """Ulož cestu ke snímku a emituj signál"""
        self.image_path = file_path
        self.image_loaded.emit(file_path)
