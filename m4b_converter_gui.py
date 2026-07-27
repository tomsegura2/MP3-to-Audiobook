#!/usr/bin/env python3
"""
MP3 to M4B Audiobook Converter — PyQt6 GUI

Merges a folder of MP3 files into a single .m4b audiobook file with an
embedded cover image, using ffmpeg under the hood.

Requirements:
    pip install PyQt6
    ffmpeg must be installed and on your system PATH.
"""

import os
import sys
import subprocess

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QFileDialog,
    QProgressBar,
    QPlainTextEdit,
    QMessageBox,
    QGroupBox,
    QSplitter,
)


# --------------------------------------------------------------------------
# Worker thread: runs ffmpeg without blocking the GUI
# --------------------------------------------------------------------------
class ConversionWorker(QThread):
    log_line = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    finished_error = pyqtSignal(str)

    def __init__(self, mp3_files, cover_image_path, output_path, bitrate="64k"):
        super().__init__()
        self.mp3_files = mp3_files
        self.cover_image_path = cover_image_path
        self.output_path = output_path
        self.bitrate = bitrate
        self._process = None
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def run(self):
        output_dir = os.path.dirname(self.output_path) or "."
        input_list_path = os.path.join(output_dir, "._m4b_input_list.txt")

        try:
            with open(input_list_path, "w", encoding="utf-8") as f:
                for mp3 in self.mp3_files:
                    safe_path = mp3.replace("\\", "/").replace("'", r"'\''")
                    f.write(f"file '{safe_path}'\n")

            command = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", input_list_path,
                "-i", self.cover_image_path,
                "-map", "0:a", "-map", "1:v",
                "-c:a", "aac", "-b:a", self.bitrate,
                "-c:v", "mjpeg",
                "-disposition:v", "attached_pic",
                "-movflags", "+faststart",
                "-metadata:s:v", "title=Cover",
                "-f", "mp4",
                self.output_path,
            ]

            self.log_line.emit("Running: " + " ".join(command))

            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in self._process.stdout:
                if self._cancelled:
                    break
                self.log_line.emit(line.rstrip())

            returncode = self._process.wait()

            if self._cancelled:
                self.finished_error.emit("Conversion cancelled by user.")
            elif returncode == 0:
                self.finished_ok.emit(self.output_path)
            else:
                self.finished_error.emit(
                    f"ffmpeg exited with code {returncode}. See log for details."
                )

        except FileNotFoundError:
            self.finished_error.emit(
                "ffmpeg was not found. Make sure it's installed and on your PATH."
            )
        except Exception as e:
            self.finished_error.emit(str(e))
        finally:
            if os.path.exists(input_list_path):
                try:
                    os.remove(input_list_path)
                except OSError:
                    pass


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
class M4BConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP3 to M4B Audiobook Converter")
        self.resize(820, 640)
        self.setAcceptDrops(True)

        self.cover_image_path = None
        self.worker = None

        self._build_ui()

    # ---------------- UI construction ----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Vertical)
        outer_layout.addWidget(splitter)

        # --- Top group: file list + controls ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        files_group = QGroupBox("MP3 Files (drag to reorder, or drop files/folder here)")
        files_layout = QVBoxLayout(files_group)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        files_layout.addWidget(self.file_list)

        file_buttons = QHBoxLayout()
        self.btn_add_files = QPushButton("Add MP3 Files…")
        self.btn_add_folder = QPushButton("Add Folder…")
        self.btn_remove_selected = QPushButton("Remove Selected")
        self.btn_clear_all = QPushButton("Clear All")
        self.btn_move_up = QPushButton("Move Up")
        self.btn_move_down = QPushButton("Move Down")
        for b in (
            self.btn_add_files,
            self.btn_add_folder,
            self.btn_remove_selected,
            self.btn_clear_all,
            self.btn_move_up,
            self.btn_move_down,
        ):
            file_buttons.addWidget(b)
        files_layout.addLayout(file_buttons)

        top_layout.addWidget(files_group)

        # --- Cover image + output settings ---
        settings_group = QGroupBox("Output Settings")
        form = QFormLayout(settings_group)

        cover_row = QHBoxLayout()
        self.cover_preview = QLabel("No cover selected")
        self.cover_preview.setFixedSize(80, 80)
        self.cover_preview.setStyleSheet("border: 1px solid #999;")
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview.setScaledContents(True)
        self.btn_choose_cover = QPushButton("Choose Cover Image…")
        cover_row.addWidget(self.cover_preview)
        cover_row.addWidget(self.btn_choose_cover)
        cover_row.addStretch()
        form.addRow("Cover Image:", cover_row)

        output_row = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Path to output .m4b file")
        self.btn_choose_output = QPushButton("Browse…")
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(self.btn_choose_output)
        form.addRow("Output File:", output_row)

        self.bitrate_edit = QLineEdit("64k")
        self.bitrate_edit.setFixedWidth(100)
        form.addRow("Audio Bitrate:", self.bitrate_edit)

        top_layout.addWidget(settings_group)

        # --- Action buttons ---
        action_row = QHBoxLayout()
        self.btn_convert = QPushButton("Convert to M4B")
        self.btn_convert.setStyleSheet("font-weight: bold; padding: 8px;")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        action_row.addWidget(self.btn_convert)
        action_row.addWidget(self.btn_cancel)
        top_layout.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate; ffmpeg doesn't give easy % here
        self.progress_bar.setVisible(False)
        top_layout.addWidget(self.progress_bar)

        splitter.addWidget(top_widget)

        # --- Bottom: log output ---
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        splitter.addWidget(log_group)

        splitter.setSizes([420, 220])

        # --- Wire up signals ---
        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove_selected.clicked.connect(self.remove_selected)
        self.btn_clear_all.clicked.connect(self.clear_all)
        self.btn_move_up.clicked.connect(self.move_up)
        self.btn_move_down.clicked.connect(self.move_down)
        self.btn_choose_cover.clicked.connect(self.choose_cover)
        self.btn_choose_output.clicked.connect(self.choose_output)
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_cancel.clicked.connect(self.cancel_conversion)

    # ---------------- Drag & drop ----------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        added = 0
        for path in paths:
            if os.path.isdir(path):
                added += self._add_mp3s_from_folder(path)
            elif path.lower().endswith(".mp3"):
                self._add_file_item(path)
                added += 1
            elif path.lower().endswith((".png", ".jpg", ".jpeg")):
                self._set_cover(path)
        if added:
            self.log(f"Added {added} MP3 file(s) via drag-and-drop.")

    # ---------------- File list management ----------------
    def _add_file_item(self, path):
        # avoid duplicates
        existing = [
            self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.file_list.count())
        ]
        if path in existing:
            return
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self.file_list.addItem(item)

    def _add_mp3s_from_folder(self, folder):
        mp3s = sorted(
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".mp3")
        )
        for m in mp3s:
            self._add_file_item(m)
        return len(mp3s)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select MP3 Files", "", "Audio Files (*.mp3)"
        )
        for f in files:
            self._add_file_item(f)
        if files:
            self.log(f"Added {len(files)} MP3 file(s).")

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing MP3 Files")
        if not folder:
            return
        count = self._add_mp3s_from_folder(folder)
        if count == 0:
            QMessageBox.information(self, "No MP3s Found", "That folder has no .mp3 files.")
        else:
            self.log(f"Added {count} MP3 file(s) from folder.")
            # Suggest an output path if none set yet
            if not self.output_path_edit.text().strip():
                suggested = os.path.join(folder, os.path.basename(folder) + ".m4b")
                self.output_path_edit.setText(suggested)

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def clear_all(self):
        self.file_list.clear()

    def move_up(self):
        row = self.file_list.currentRow()
        if row > 0:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row - 1, item)
            self.file_list.setCurrentRow(row - 1)

    def move_down(self):
        row = self.file_list.currentRow()
        if 0 <= row < self.file_list.count() - 1:
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row + 1, item)
            self.file_list.setCurrentRow(row + 1)

    # ---------------- Cover / output pickers ----------------
    def choose_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self._set_cover(path)

    def _set_cover(self, path):
        self.cover_image_path = path
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.cover_preview.setPixmap(pixmap)
        else:
            self.cover_preview.setText("Invalid image")

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose Output File", "", "Audiobook (*.m4b)"
        )
        if path:
            if not path.lower().endswith(".m4b"):
                path += ".m4b"
            self.output_path_edit.setText(path)

    # ---------------- Logging ----------------
    def log(self, text):
        self.log_view.appendPlainText(text)

    # ---------------- Conversion ----------------
    def _gather_mp3_paths(self):
        return [
            self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.file_list.count())
        ]

    def start_conversion(self):
        mp3_files = self._gather_mp3_paths()
        output_path = self.output_path_edit.text().strip()
        bitrate = self.bitrate_edit.text().strip() or "64k"

        if not mp3_files:
            QMessageBox.warning(self, "No Files", "Add at least one MP3 file first.")
            return
        if not self.cover_image_path or not os.path.isfile(self.cover_image_path):
            QMessageBox.warning(self, "No Cover Image", "Choose a valid cover image first.")
            return
        if not output_path:
            QMessageBox.warning(self, "No Output Path", "Choose an output .m4b path first.")
            return
        if not output_path.lower().endswith(".m4b"):
            output_path += ".m4b"
            self.output_path_edit.setText(output_path)

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, "Error", f"Couldn't create output folder:\n{e}")
                return

        self.log_view.clear()
        self.log(f"Starting conversion of {len(mp3_files)} file(s)...")

        self._set_busy(True)

        self.worker = ConversionWorker(mp3_files, self.cover_image_path, output_path, bitrate)
        self.worker.log_line.connect(self.log)
        self.worker.finished_ok.connect(self._on_finished_ok)
        self.worker.finished_error.connect(self._on_finished_error)
        self.worker.start()

    def cancel_conversion(self):
        if self.worker:
            self.log("Cancelling...")
            self.worker.cancel()

    def _set_busy(self, busy):
        self.btn_convert.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.progress_bar.setVisible(busy)

    def _on_finished_ok(self, output_path):
        self._set_busy(False)
        self.log(f"Done. Saved to: {output_path}")
        QMessageBox.information(self, "Success", f"Audiobook created:\n{output_path}")

    def _on_finished_error(self, message):
        self._set_busy(False)
        self.log(f"Error: {message}")
        QMessageBox.critical(self, "Conversion Failed", message)


def main():
    app = QApplication(sys.argv)
    window = M4BConverterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
