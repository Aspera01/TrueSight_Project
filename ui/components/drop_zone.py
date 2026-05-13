"""
Drop zone widget with media preview.
- Images: shows thumbnail
- Video: shows first frame as thumbnail + metadata
- Audio: shows waveform + metadata
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen

SUPPORTED = (
    "Media Files (*.jpg *.jpeg *.png *.bmp *.tiff *.webp "
    "*.mp4 *.avi *.mov *.mkv *.wmv *.webm "
    "*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;"
    "All Files (*.*)"
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}


class DropZoneWidget(QWidget):
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        self.setMinimumHeight(220)
        self._file_path: str | None = None
        self._build_empty()

    # ---------------------------------------------------------------- Build

    def _build_empty(self):
        self._clear_layout()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 30, 20, 30)

        icon = QLabel("⬆")
        icon.setObjectName("dropIcon")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        main_lbl = QLabel("Click to upload or drag and drop")
        main_lbl.setObjectName("dropMainLabel")
        main_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(main_lbl)

        sub_lbl = QLabel("Supported formats: MP4, AVI, MOV, MP3, WAV, JPG, PNG and more")
        sub_lbl.setObjectName("dropSubLabel")
        sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_lbl)

        browse_btn = QPushButton("Browse file")
        browse_btn.setObjectName("browseBtn")
        browse_btn.setFixedWidth(130)
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn, alignment=Qt.AlignCenter)

    def _build_preview(self, path: str):
        self._clear_layout()
        ext = Path(path).suffix.lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        if ext in IMAGE_EXTS:
            self._build_image_preview(layout, path)
        elif ext in VIDEO_EXTS:
            self._build_video_preview(layout, path)
        elif ext in AUDIO_EXTS:
            self._build_audio_preview(layout, path)
        else:
            self._build_generic_preview(layout, path)

        # Change file link
        change_btn = QPushButton("↩  Change file")
        change_btn.setObjectName("browseBtn")
        change_btn.setFixedWidth(130)
        change_btn.clicked.connect(self._browse)
        layout.addWidget(change_btn, alignment=Qt.AlignCenter)

    def _build_image_preview(self, layout: QVBoxLayout, path: str):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            thumb = pixmap.scaled(340, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setObjectName("previewImage")
            img_label.setPixmap(thumb)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)

        self._add_file_info(layout, path, "IMAGE",
                            f"{pixmap.width()} × {pixmap.height()} px" if not pixmap.isNull() else "")

    def _build_video_preview(self, layout: QVBoxLayout, path: str):
        # Extract first frame using OpenCV
        thumb_pixmap = self._extract_video_thumb(path)
        if thumb_pixmap and not thumb_pixmap.isNull():
            img_label = QLabel()
            img_label.setObjectName("previewImage")
            img_label.setPixmap(thumb_pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)

        meta = self._get_video_meta(path)
        self._add_file_info(layout, path, "VIDEO", meta)

    def _build_audio_preview(self, layout: QVBoxLayout, path: str):
        # Draw a simple waveform placeholder
        wave_label = self._build_waveform_widget(path)
        layout.addWidget(wave_label)
        meta = self._get_audio_meta(path)
        self._add_file_info(layout, path, "AUDIO", meta)

    def _build_generic_preview(self, layout: QVBoxLayout, path: str):
        icon = QLabel("📄")
        icon.setAlignment(Qt.AlignCenter)
        icon.setObjectName("dropIcon")
        layout.addWidget(icon)
        self._add_file_info(layout, path, "FILE", "")

    def _add_file_info(self, layout: QVBoxLayout, path: str, tag: str, extra: str):
        info_row = QHBoxLayout()

        tag_lbl = QLabel(tag)
        tag_lbl.setObjectName("previewTypeTag")
        tag_lbl.setFixedHeight(20)

        name_lbl = QLabel(Path(path).name)
        name_lbl.setObjectName("previewFileName")
        name_lbl.setWordWrap(False)

        size = Path(path).stat().st_size
        size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.1f} KB"
        meta_parts = [size_str]
        if extra:
            meta_parts.append(extra)
        meta_lbl = QLabel("  ·  ".join(meta_parts))
        meta_lbl.setObjectName("previewMeta")

        info_row.addWidget(tag_lbl)
        info_row.addSpacing(8)
        info_row.addWidget(name_lbl)
        info_row.addStretch()

        info_col = QVBoxLayout()
        info_col.addLayout(info_row)
        info_col.addWidget(meta_lbl)
        layout.addLayout(info_col)

    # ---------------------------------------------------------------- Media helpers

    def _extract_video_thumb(self, path: str) -> QPixmap | None:
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return None
            import numpy as np
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            from PySide6.QtGui import QImage
            qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            return pixmap.scaled(340, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            return None

    def _get_video_meta(self, path: str) -> str:
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            duration = total / fps if fps > 0 else 0
            mins = int(duration // 60)
            secs = int(duration % 60)
            return f"{w}×{h}  ·  {mins}:{secs:02d}  ·  {fps:.0f} fps"
        except Exception:
            return ""

    def _get_audio_meta(self, path: str) -> str:
        try:
            import librosa
            duration = librosa.get_duration(path=path)
            mins = int(duration // 60)
            secs = int(duration % 60)
            return f"{mins}:{secs:02d} duration"
        except Exception:
            return ""

    def _build_waveform_widget(self, path: str) -> QLabel:
        """Draw a simple waveform visualization using librosa + QPainter."""
        label = QLabel()
        label.setFixedSize(340, 80)
        label.setAlignment(Qt.AlignCenter)

        canvas = QPixmap(340, 80)
        canvas.fill(QColor("#0a1520"))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            import librosa
            import numpy as np
            y, sr = librosa.load(path, sr=None, mono=True, duration=30.0)
            # Downsample to 340 points
            n = 340
            step = max(1, len(y) // n)
            samples = np.array([np.abs(y[i:i+step]).mean() for i in range(0, len(y)-step, step)])[:n]
            if samples.max() > 0:
                samples = samples / samples.max()

            pen = QPen(QColor("#3d8fd4"), 1.5)
            painter.setPen(pen)
            mid = 40
            for i, amp in enumerate(samples):
                h = int(amp * 35)
                painter.drawLine(i, mid - h, i, mid + h)
        except Exception:
            # Fallback: draw flat line
            pen = QPen(QColor("#1a3a55"), 1)
            painter.setPen(pen)
            painter.drawLine(0, 40, 340, 40)

        painter.end()
        label.setPixmap(canvas)
        return label

    # ---------------------------------------------------------------- Slots / Events

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", str(Path.home()), SUPPORTED)
        if path:
            self.file_selected.emit(path)

    def set_file(self, path: str):
        self._file_path = path
        self._build_preview(path)

    def reset(self):
        self._file_path = None
        self._build_empty()

    def _clear_layout(self):
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.layout().deleteLater()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.file_selected.emit(urls[0].toLocalFile())
