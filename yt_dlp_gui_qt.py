import sys
import os
import json
import subprocess
import queue
import re
import threading
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QGroupBox, QRadioButton,
    QComboBox, QTextEdit, QProgressBar, QMessageBox, QGridLayout, QCheckBox,
    QDialog, QListWidget, QSizePolicy
)
from PyQt6.QtCore import (
    QThread, pyqtSignal, QObject, Qt, QSize, QTimer
)
from PyQt6.QtGui import QIcon

# Import the logic manager created in the previous step
from download_manager import DownloadManager, load_dummy_config
from version import APP_VERSION

VIDEO_FORMATS = ["mp4", "mkv", "webm", "flv", "avi", "mov"]
AUDIO_FORMATS = ["mp3", "m4a", "wav"]
PROJECT_URL = "https://github.com/btrf/yt-dlp-gui"
TEMPLATE_PRESETS = [
    "%(title)s.%(ext)s",
    "%(upload_date)s - %(title)s.%(ext)s",
    "%(uploader)s - %(title)s.%(ext)s",
    "%(upload_date)s - %(uploader)s - %(title)s.%(ext)s",
    "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s",
    "%(uploader)s/%(title)s.%(ext)s",
    "%(id)s.%(ext)s",
]

class Worker(QObject):
    """Worker object that runs the yt-dlp logic in a separate thread."""
    progress_update = pyqtSignal(float)
    status_update = pyqtSignal(str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, manager: DownloadManager, url: str, playlist_items: str, template: str, download_type: str, quality: str, extra_options: str, output_format: str = ""):
        super().__init__()
        self.manager = manager
        self.url = url
        self.playlist_items = playlist_items
        self.template = template
        self.download_type = download_type
        self.quality = quality
        self.extra_options = extra_options
        self.output_format = output_format
        self.is_running = False

    def run(self):
        self.manager.process = None
        self.manager.output_queue = queue.Queue()

        try:
            if self.manager.cancelled:
                self.status_update.emit("Cancelled")
                return

            self.manager.is_running = True
            self.log_message.emit(f"Starting download: {self.url}")
            cmd = self.manager.build_command(self.url,
                                            is_playlist=bool(self.playlist_items),
                                            playlist_items=self.playlist_items,
                                            filename_template=self.template,
                                            download_type=self.download_type,
                                            quality=self.quality,
                                            extra_options=self.extra_options,
                                            output_format=self.output_format)

            self.manager.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            output_thread = threading.Thread(
                target=self._enqueue_output,
                args=(self.manager.process.stdout, self.manager.output_queue))
            output_thread.daemon = True
            output_thread.start()

            self._process_output_stream()

        except Exception as e:
            if self.manager.cancelled:
                self.status_update.emit("Cancelled")
            else:
                self.log_message.emit(f"Critical Error: {e}")
                self.status_update.emit("Error")
        finally:
            self.manager.is_running = False
            self.manager.process = None
            self.finished.emit()

    def _enqueue_output(self, out, q):
        for line in iter(out.readline, ''):
            q.put(line)
        q.put(None)

    def _process_output_stream(self):
        while self.manager.is_running and not self.manager.cancelled:
            try:
                line = self.manager.output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                break

            self.log_message.emit(line.rstrip())

            progress = self.manager.parse_progress(line)
            if isinstance(progress, (int, float)):
                self.progress_update.emit(float(progress))

            status_parts = self.manager.parse_progress(line)
            if isinstance(status_parts, list):
                self.status_update.emit(" | ".join(status_parts))

        if self.manager.process is not None:
            self.manager.process.wait()

        if self.manager.cancelled:
            self.status_update.emit("Cancelled")
            return

        final_status = self.manager.check_status()
        if "Completed" in final_status:
            self.status_update.emit("Success")
        elif "Failed" in final_status:
            self.status_update.emit("Failure")
        else:
            self.status_update.emit("Stopped")
            
    def terminate(self):
        self.manager.cancelled = True
        self.manager.is_running = False
        process = self.manager.process
        if process is None:
            return True

        try:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=2)
            self.log_message.emit("Download process terminated successfully.")
            return True
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                process.wait(timeout=2)
                self.log_message.emit("Download process forcefully killed.")
                return True
            except Exception as e:
                self.log_message.emit(f"Error killing process: {e}")
                return False
        except Exception as e:
            self.log_message.emit(f"Error terminating process: {e}")
            return False

class YtDlpGUI(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        
        self.url_list = []
        self.url_queue = []
        self.batch_active = False
        self.batch_total = 0
        self.batch_current = 0
        self.worker_thread = None
        self.worker = None
        self.format_selections = {"video": "mp4", "audio": "mp3"}
        
        self.init_ui()
        self.center_window()

    def init_ui(self):
        self.setWindowTitle(f"yt-dlp GUI {APP_VERSION}")
        self.base_window_title = f"yt-dlp GUI {APP_VERSION}"
        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("Help")
        template_help_action = help_menu.addAction("Filename Templates")
        template_help_action.triggered.connect(self.show_template_help)
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt-dlp-gui.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(QSize(860, 505))
        self.resize(860, 505)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 1. Source & Output ---
        self.source_group = QGroupBox("Source / Output")
        source_layout = QGridLayout(self.source_group)
        
        source_layout.addWidget(QLabel("Video URL:"), 0, 0)
        self.url_entry = QLineEdit()
        source_layout.addWidget(self.url_entry, 0, 1)
        self.url_entry.returnPressed.connect(self.try_start_download)
        self.paste_url_btn = QPushButton("◀ Clipboard")
        self.paste_url_btn.setToolTip("Paste a video link from the clipboard")
        self.paste_url_btn.clicked.connect(self.paste_url_from_clipboard)
        source_layout.addWidget(self.paste_url_btn, 0, 2)

        source_layout.addWidget(QLabel("Download Path:"), 1, 0)
        self.path_entry = QLineEdit()
        self.path_entry.setText(self.manager.config.get("default_download_path", ""))
        self.browse_path_btn = QPushButton("Browse")
        self.browse_path_btn.clicked.connect(self.browse_path)
        source_layout.addWidget(self.path_entry, 1, 1)
        source_layout.addWidget(self.browse_path_btn, 1, 2)
        
        main_layout.addWidget(self.source_group)

        # --- 2. Playlist Control ---
        self.playlist_group = QGroupBox("Playlist Control")
        playlist_layout = QHBoxLayout(self.playlist_group)
        
        self.playlist_check = QCheckBox("Download Playlist")
        self.playlist_check.toggled.connect(self.toggle_playlist_scope)
        playlist_layout.addWidget(self.playlist_check)
        
        self.playlist_scope_combo = QComboBox()
        self.playlist_scope_combo.addItems(["all", "first", "last", "between", "items"])
        self.playlist_scope_combo.currentIndexChanged.connect(self.toggle_playlist_scope)
        self.playlist_scope_combo.setEnabled(False)
        playlist_layout.addWidget(self.playlist_scope_combo)
        
        self.playlist_spec_label = QLabel("Items:")
        self.playlist_spec_label.setVisible(False)
        playlist_layout.addWidget(self.playlist_spec_label)
        
        self.playlist_spec_edit = QLineEdit()
        self.playlist_spec_edit.setFixedWidth(140)
        self.playlist_spec_edit.setVisible(False)
        playlist_layout.addWidget(self.playlist_spec_edit)
        
        playlist_layout.addStretch()
        
        main_layout.addWidget(self.playlist_group)
        
        # --- 3. Options Section ---
        self.options_group = QGroupBox("Download Options")
        options_layout = QGridLayout(self.options_group)
        
        options_row = QHBoxLayout()
        
        def make_block(label_text, widget):
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(5)
            label = QLabel(label_text)
            label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            lay.addWidget(label)
            lay.addWidget(widget)
            holder.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            return holder
        
        self.download_type = QComboBox()
        self.download_type.addItems(["video", "audio"])
        self.download_type.currentIndexChanged.connect(self.on_download_type_change)
        options_row.addWidget(make_block("Type:", self.download_type))
        options_row.addSpacing(10)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "best", "bestvideo", "bestaudio", "720p", "480p", "360p"])
        self.quality_combo.currentIndexChanged.connect(self.on_quality_change)
        options_row.addWidget(make_block("Quality:", self.quality_combo))
        options_row.addSpacing(10)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(VIDEO_FORMATS)
        self.format_combo.currentIndexChanged.connect(self.on_format_change)
        options_row.addWidget(make_block("Format:", self.format_combo))
        options_row.addSpacing(10)
        
        self.filename_template_entry = QLineEdit()
        self.filename_template_entry.setText("%(upload_date)s - %(title)s.%(ext)s")
        self.filename_template_entry.setFixedWidth(190)
        options_row.addWidget(make_block("Filename:", self.filename_template_entry))
        options_row.addSpacing(10)
        
        self.options_entry = QLineEdit()
        self.options_entry.setPlaceholderText("e.g., --limit-rate 1M")
        self.options_entry.setFixedWidth(118)
        options_row.addWidget(make_block("Extra Args:", self.options_entry))
        
        options_layout.addLayout(options_row, 0, 0, 1, 4)
        
        main_layout.addWidget(self.options_group)

        # --- 4. Progress/Status Section ---
        self.status_group = QGroupBox("Status")
        status_layout = QHBoxLayout(self.status_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.status_label)
        main_layout.addWidget(self.status_group)

        # --- 5. Log Section ---
        self.log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(self.log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_btn_clear = QPushButton("Clear Log")
        self.log_btn_clear.clicked.connect(self.clear_log)
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(self.log_btn_clear)
        main_layout.addWidget(self.log_group)

        # --- 6. Button Section ---
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton("▶ Download")
        self.download_btn.clicked.connect(self.try_start_download)
        self.cancel_btn = QPushButton("■ Stop")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        self.load_links_btn = QPushButton("Load Links from File")
        self.load_links_btn.clicked.connect(self.load_links_from_file)
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.close)

        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.load_links_btn)
        button_layout.addWidget(self.quit_btn)
        
        main_layout.addLayout(button_layout)

    def center_window(self):
        # Simple centering logic for PyQt
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # --- UI Event Handlers ---
    def browse_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.path_entry.text())
        if directory:
            self.path_entry.setText(directory)
            self.manager.config["default_download_path"] = directory
            self.manager.default_dir = directory
            
    def paste_url_from_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if not text:
            QMessageBox.information(self, "Paste", "The clipboard is empty.")
            return
        first_line = text.splitlines()[0].strip()
        self.url_entry.setText(first_line)
        self.url_entry.setFocus()

    def toggle_playlist_scope(self, *_):
        self.playlist_scope_combo.setEnabled(self.playlist_check.isChecked())
        if not self.playlist_check.isChecked():
            self.playlist_scope_combo.setCurrentText("all")
        scope = self.playlist_scope_combo.currentText()
        needs_input = self.playlist_check.isChecked() and scope in ("between", "items")
        self.playlist_spec_label.setVisible(needs_input)
        self.playlist_spec_edit.setVisible(needs_input)
        if scope == "between":
            self.playlist_spec_label.setText("From - To:")
            self.playlist_spec_edit.setPlaceholderText("2:5")
        elif scope == "items":
            self.playlist_spec_label.setText("Items:")
            self.playlist_spec_edit.setPlaceholderText("1,3,5")
        self.playlist_spec_edit.setEnabled(needs_input)

    def resolve_playlist_spec(self):
        if not self.playlist_check.isChecked():
            return "", ""
        scope = self.playlist_scope_combo.currentText()
        if scope in ("all", "first", "last"):
            return scope, ""
        raw = self.playlist_spec_edit.text().strip()
        if scope == "between":
            match = re.fullmatch(r"(\d+)\s*:\s*(\d+)", raw)
            if not match:
                return None, "Enter a range as START:END, for example 2:5"
            start, end = int(match.group(1)), int(match.group(2))
            if start < 1 or end < start:
                return None, "START must be 1 or more, and END must not be less than START"
            return f"{start}:{end}", ""
        if scope == "items":
            parts = [part.strip() for part in raw.split(",")]
            if not raw or not all(re.fullmatch(r"\d+", part) and int(part) >= 1 for part in parts):
                return None, "Enter item numbers separated by commas, for example 1,3,5"
            return ",".join(str(int(part)) for part in parts), ""
        return scope, ""

    def on_download_type_change(self, index):
        download_type = self.download_type.currentText()
        if download_type == "audio":
            self.quality_combo.setCurrentText("bestaudio")
        else:
            self.quality_combo.setCurrentText("1080p")
        self._set_format_options(download_type)

    def _set_format_options(self, download_type):
        formats = AUDIO_FORMATS if download_type == "audio" else VIDEO_FORMATS
        selected = self.format_selections.get(download_type, formats[0])
        if selected not in formats:
            selected = formats[0]
        self.format_combo.blockSignals(True)
        try:
            self.format_combo.clear()
            self.format_combo.addItems(formats)
            self.format_combo.setCurrentText(selected)
        finally:
            self.format_combo.blockSignals(False)

    def on_quality_change(self, index):
        pass # Handled by worker

    def on_format_change(self, index):
        if index >= 0:
            self.format_selections[self.download_type.currentText()] = self.format_combo.currentText()

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About yt-dlp GUI")
        dialog.setFixedWidth(460)
        layout = QVBoxLayout(dialog)

        title = QLabel(f"<b>yt-dlp GUI {APP_VERSION}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        description = QLabel("Qt desktop wrapper for yt-dlp.")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        link = QLabel(f'<a href="{PROJECT_URL}">{PROJECT_URL}</a>')
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(link)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        dialog.exec()

    def show_template_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Template Help")
        dialog.resize(760, 520)
        layout = QVBoxLayout(dialog)

        instruction = QLabel("Select a template, then copy it to the clipboard.")
        layout.addWidget(instruction)

        template_list = QListWidget(dialog)
        template_list.addItems(TEMPLATE_PRESETS)
        template_list.setCurrentRow(0)
        layout.addWidget(template_list, 1)

        reference = QTextEdit(dialog)
        reference.setReadOnly(True)
        reference.setPlainText(
            "Common fields:\n"
            "%(title)s - video or audio title\n"
            "%(uploader)s - uploader name\n"
            "%(upload_date)s - upload date\n"
            "%(playlist_index)s - playlist item number\n"
            "%(playlist_title)s - playlist title\n"
            "%(id)s - media ID\n"
            "%(ext)s - output extension"
        )
        reference.setMaximumHeight(150)
        layout.addWidget(reference)

        feedback = QLabel("")
        buttons = QHBoxLayout()
        copy_selected_button = QPushButton("Copy selected")
        copy_all_button = QPushButton("Copy all")
        close_button = QPushButton("Close")
        buttons.addWidget(copy_selected_button)
        buttons.addWidget(copy_all_button)
        buttons.addWidget(feedback, 1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        def selected_template():
            item = template_list.currentItem()
            return item.text() if item else ""

        def copy_selected():
            template = selected_template()
            if template:
                QApplication.clipboard().setText(template)
                feedback.setText("Selected template copied")

        def copy_all():
            QApplication.clipboard().setText("\n".join(TEMPLATE_PRESETS))
            feedback.setText("All templates copied")

        copy_selected_button.clicked.connect(copy_selected)
        copy_all_button.clicked.connect(copy_all)
        close_button.clicked.connect(dialog.accept)
        template_list.itemDoubleClicked.connect(lambda _: copy_selected())
        template_list.currentItemChanged.connect(lambda *_: feedback.clear())
        dialog.exec()

    def load_links_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file with URLs", "", "Text files (*.txt);;All files (*.*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                urls = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(('#', ';', ']')):
                        urls.append(line)
                
                self.url_list = urls
                self.log_message(f"Loaded {len(urls)} URLs from {file_path}")
                self.log_message(f"First few URLs: {urls[:3]}")
                
                if len(urls) == 1:
                    self.url_entry.setText(urls[0])
                else:
                    if QMessageBox.question(self, "Batch Download", f"Loaded {len(urls)} URLs. Start batch download?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                        self.start_batch_download()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error reading file: {str(e)}")

    def try_start_download(self):
        url = self.url_entry.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL")
            return

        playlist_items, error = self.resolve_playlist_spec()
        if error:
            QMessageBox.warning(self, "Error", error)
            return

        self.start_download_worker(url, playlist_items, self.filename_template_entry.text(), 
                                   self.download_type.currentText(), self.quality_combo.currentText(), self.options_entry.text(), self.format_combo.currentText())

    def start_batch_download(self):
        if not self.url_list:
            QMessageBox.warning(self, "Error", "No URLs loaded. Load URLs from a file first.")
            return
            
        self.start_batch_worker()

    def set_input_sections_enabled(self, enabled):
        for group in (self.source_group, self.playlist_group, self.options_group):
            group.setEnabled(enabled)

    def start_download_worker(self, url, playlist_items, template, download_type, quality, options, output_format=""):
        self.status_label.setText("Initializing...")
        self.progress_bar.setValue(0)
        
        # Instantiate Manager
        config = self.manager.config
        selected_path = self.path_entry.text().strip()
        if selected_path:
            config["default_download_path"] = selected_path
        manager = DownloadManager(
            yt_dlp_path=config["yt_dlp_path"],
            ffmpeg_path=config["ffmpeg_path"],
            default_dir=config["default_download_path"],
            config=config
        )
        manager.cancelled = False
        self.manager = manager
        
        self.worker = Worker(manager, url, playlist_items, template, download_type, quality, options, output_format)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status)
        self.worker.log_message.connect(self.log_message)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.download_finished)
        
        # Connect thread control
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.set_input_sections_enabled(False)
        self.worker_thread.start()

    def start_batch_worker(self):
        if self.worker is not None:
            QMessageBox.warning(self, "Error", "A download is already running.")
            return
        self.batch_active = True
        self.batch_total = len(self.url_list)
        self.batch_current = 0
        self.url_queue = list(self.url_list)
        self.status_label.setText(f"Batch downloading {self.batch_total} URLs...")
        self.progress_bar.setValue(0)
        self._start_next_batch_item()

    def _start_next_batch_item(self):
        if not self.url_queue:
            return
        url = self.url_queue.pop(0)
        self.batch_current += 1
        self.log_message(f"--- Starting Batch Download ({self.batch_current}/{self.batch_total}) ---")
        self.setWindowTitle(f"{self.base_window_title} - Batch {self.batch_current}/{self.batch_total}")
        self.start_download_worker(url, "", self.filename_template_entry.text(), self.download_type.currentText(), self.quality_combo.currentText(), self.options_entry.text(), self.format_combo.currentText())

    def update_progress(self, progress):
        self.progress_bar.setValue(int(progress))

    def update_status(self, status):
        self.status_label.setText(status)
        if status == "Success":
            self.status_label.setStyleSheet("color: green;")
        elif status == "Failure":
            self.status_label.setStyleSheet("color: red;")
        elif status == "Error":
            self.status_label.setStyleSheet("color: red;")
        elif status == "Cancelled":
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setStyleSheet("color: blue;")

    def log_message(self, message):
        self.log_text.append(message)

    def clear_log(self):
        self.log_text.clear()

    def download_finished(self):
        cancelled = bool(self.manager.cancelled) if self.manager is not None else False
        if self.batch_active and not cancelled and self.url_queue:
            QTimer.singleShot(0, self._start_next_batch_item)
            return
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.set_input_sections_enabled(True)
        if cancelled:
            self.update_status("Cancelled")
        if self.batch_active:
            self.log_message(f"--- Batch finished: {self.batch_current}/{self.batch_total} ---")
            self.batch_active = False
            self.url_queue = []
        self.setWindowTitle(self.base_window_title)
        self.worker_thread = None
        self.worker = None
        if self.manager is not None:
            self.manager.is_running = False

    def cancel_download(self):
        if self.worker is None:
            return
        self.status_label.setText("Stopping...")
        self.cancel_btn.setEnabled(False)
        self.manager.cancelled = True
        self.worker.terminate()
        
    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.terminate()
        if self.worker_thread is not None:
            self.worker_thread.quit()
            self.worker_thread.wait(3000)
        event.accept()


# --- Configuration/Helper Functions ---
def load_dummy_config():
    if getattr(sys, "frozen", False):
        resource_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
        launch_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        resource_dir = os.path.dirname(os.path.abspath(__file__))
        launch_dir = resource_dir

    config_path = os.path.join(resource_dir, "yt-dlp-gui.json")
    config = {
        "yt_dlp_path": os.path.join(resource_dir, "bin", "yt-dlp.exe"),
        "ffmpeg_path": os.path.join(resource_dir, "bin", "ffmpeg.exe"),
        "default_download_path": r"C:\Downloads"
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config.update(json.load(file))
        except (OSError, ValueError):
            pass

    for key in ("yt_dlp_path", "ffmpeg_path"):
        value = config.get(key, "")
        if value and not os.path.isabs(value):
            config[key] = os.path.join(resource_dir, value)

    default_path = os.path.expanduser(config.get("default_download_path", r"C:\Downloads"))
    if not os.path.isdir(default_path):
        default_path = launch_dir
    config["default_download_path"] = default_path
    return config

def main():
    # Initialize Configuration
    config = load_dummy_config()
    
    # Initialize Manager (this holds the state)
    manager = DownloadManager(
        yt_dlp_path=config["yt_dlp_path"],
        ffmpeg_path=config["ffmpeg_path"],
        default_dir=config["default_download_path"],
        config=config
    )
    
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("yt-dlp-gui")

    app = QApplication(sys.argv)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt-dlp-gui.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    main_window = YtDlpGUI(manager)
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
