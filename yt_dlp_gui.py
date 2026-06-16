"""
yt-dlp GUI

A simple graphical user interface for yt-dlp, allowing you to download videos
from various websites with a user-friendly interface.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, Menu, simpledialog
import subprocess
import threading
import os
import json
import re
import queue


class YtDlpGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp GUI")
        self.root.geometry("575x555")

        try:
            self.root.iconbitmap("yt_dlp_gui.ico")
        except tk.TclError:
            pass

        self.config_file = "yt-dlp-gui.json"
        self.config = self.load_config()
        self.yt_dlp_path = self.config.get("yt_dlp_path", "bin/yt-dlp.exe")
        self.ffmpeg_path = self.config.get("ffmpeg_path", "bin/ffmpeg.exe")
        self.current_process = None

        self.create_menu()
        self._build_ui()
        self.center_window()
        self.url_entry.focus_set()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        self._create_url_section(main_frame)
        self._create_playlist_section(main_frame)
        self._create_options_section(main_frame)
        self._create_progress_section(main_frame)
        self._create_log_section(main_frame)
        self._create_button_section(main_frame)

        main_frame.rowconfigure(7, weight=1)

    def _create_url_section(self, parent):
        ttk.Label(parent, text="Video URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(parent, width=70)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        self.url_entry.bind("<Button-3>", self.show_url_context_menu)

        ttk.Label(parent, text="Download Path:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.path_entry = ttk.Entry(parent, width=50)
        self.path_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        self.default_dir = self.config.get("default_download_path",
                                            os.path.expanduser("~/Downloads/yt-dlp"))
        os.makedirs(self.default_dir, exist_ok=True)
        self.path_entry.insert(0, self.default_dir)
        ttk.Button(parent, text="Browse", command=self.browse_path).grid(
            row=1, column=2, pady=5, padx=(5, 0))

    def _create_playlist_section(self, parent):
        self.is_playlist = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Download Playlist",
                        variable=self.is_playlist).grid(row=2, column=0, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Playlist Scope:").grid(
            row=2, column=1, sticky=tk.E, padx=(10, 2), pady=5)
        self.playlist_scope_var = tk.StringVar(value="all")
        self.playlist_scope_combo = ttk.Combobox(
            parent, textvariable=self.playlist_scope_var,
            values=["all", "first", "last", "between", "items"],
            state="readonly", width=10)
        self.playlist_scope_combo.grid(row=2, column=2, sticky=tk.W, padx=(2, 0), pady=5)
        self.playlist_scope_combo.config(state="disabled")
        self.is_playlist.trace('w', self.toggle_playlist_scope)

    def _create_options_section(self, parent):
        options_frame = ttk.LabelFrame(parent, text="Download Options", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        options_frame.columnconfigure(0, weight=1)

        self.download_type = tk.StringVar(value="video")
        self.download_type.trace('w', self.on_download_type_change)
        ttk.Radiobutton(options_frame, text="Video + Audio", variable=self.download_type,
                        value="video").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(options_frame, text="Audio Only", variable=self.download_type,
                        value="audio").grid(row=0, column=1, sticky=tk.W)

        ttk.Label(options_frame, text="Quality:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.quality_var = tk.StringVar(value="1080p")
        quality_combo = ttk.Combobox(options_frame, textvariable=self.quality_var,
                                     values=["1080p", "best", "bestvideo", "bestaudio",
                                             "720p", "480p", "360p"],
                                     state="readonly", width=15)
        quality_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))

        ttk.Label(options_frame, text="Format:").grid(row=1, column=2, sticky=tk.E,
                                                      pady=(10, 0), padx=(20, 0))
        self.format_var = tk.StringVar(value="mp4")
        format_combo = ttk.Combobox(options_frame, textvariable=self.format_var,
                                    values=["mp4", "mkv", "webm", "flv", "avi", "mov",
                                            "mp3", "m4a", "wav"],
                                    state="readonly", width=15)
        format_combo.grid(row=1, column=3, sticky=tk.E, pady=(10, 0))

        ttk.Label(options_frame, text="Filename Template:").grid(
            row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.filename_template_var = tk.StringVar(
            value="%(upload_date)s - %(title)s.%(ext)s")
        self.filename_template_entry = ttk.Entry(
            options_frame, textvariable=self.filename_template_var, width=50)
        self.filename_template_entry.grid(
            row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(options_frame, text="Template Help",
                   command=self.show_template_help).grid(
            row=2, column=3, padx=(5, 0), pady=5)

        ttk.Label(options_frame, text="Additional Options:").grid(
            row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.options_entry = ttk.Entry(options_frame, width=70)
        self.options_entry.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(options_frame, text="Example: --limit-rate 1M --retries 5",
                  foreground="gray").grid(row=5, column=0, columnspan=4, sticky=tk.W)

    def _create_progress_section(self, parent):
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        self.status_label = ttk.Label(parent, text="Ready", foreground="blue")
        self.status_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=5)

    def _create_log_section(self, parent):
        ttk.Label(parent, text="Log:").grid(row=6, column=0, sticky=tk.W, pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(parent, height=10, width=80)
        self.log_text.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S),
                           pady=5)
        self.log_text.config(state=tk.DISABLED)

    def _create_button_section(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=8, column=0, columnspan=3, pady=10)

        self.download_btn = ttk.Button(button_frame, text="Download",
                                       command=self.start_download)
        self.download_btn.grid(row=0, column=0, padx=(0, 10))

        self.cancel_btn = ttk.Button(button_frame, text="Cancel",
                                     command=self.cancel_download, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(0, 10))

        ttk.Button(button_frame, text="Load Links from File",
                   command=self.load_links_from_file).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(button_frame, text="Clear Log",
                   command=self.clear_log).grid(row=0, column=3)
        ttk.Button(button_frame, text="Quit",
                   command=self.root.destroy).grid(row=0, column=4)

    def browse_path(self):
        directory = filedialog.askdirectory(initialdir=self.path_entry.get())
        if directory:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, directory)

    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.update()

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        if not self._get_playlist_scope_input():
            return

        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="enabled")
        self.status_label.config(text="Downloading...", foreground="orange")

        thread = threading.Thread(target=self.download_worker, args=(url,))
        thread.daemon = True
        thread.start()

    def download_worker(self, url):
        try:
            cmd = self.build_command(url)
            self.log_message(f"Running command: {' '.join(cmd)}")

            self.current_process = self._run_subprocess(cmd)

            output_queue = queue.Queue()

            def enqueue_output(out, q):
                for line in iter(out.readline, ''):
                    q.put(line)
                q.put(None)

            thread = threading.Thread(
                target=enqueue_output,
                args=(self.current_process.stdout, output_queue))
            thread.daemon = True
            thread.start()

            while thread.is_alive() or not output_queue.empty():
                try:
                    line = output_queue.get(timeout=0.1)
                    if line is None:
                        break
                    self.log_message(line.rstrip())
                    self.parse_progress(line)
                except queue.Empty:
                    if self.current_process and self.current_process.poll() is not None:
                        break

            self.current_process.wait()

            if self.current_process.returncode == 0:
                self.status_label.config(text="Download completed successfully!",
                                         foreground="green")
                self.log_message("Download completed successfully!")
            else:
                if self.current_process.returncode < 0:
                    self.log_message("Download was cancelled by user")
                    self.status_label.config(text="Download cancelled", foreground="red")
                else:
                    self.status_label.config(text="Download failed!", foreground="red")
                    self.log_message(
                        f"Download failed with return code: {self.current_process.returncode}")

        except Exception as e:
            self.status_label.config(text="Download error!", foreground="red")
            self.log_message(f"Error during download: {str(e)}")
        finally:
            self.download_btn.config(state="enabled")
            self.cancel_btn.config(state="disabled")
            self.current_process = None

    def _run_subprocess(self, cmd):
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

    def _get_playlist_scope_input(self):
        if not self.is_playlist.get():
            return True
        scope = self.playlist_scope_var.get()
        if scope == "between":
            range_input = simpledialog.askstring(
                "Playlist Range",
                "Enter range (e.g., '1:5' for first 5, '3:10' for items 3-10):",
                initialvalue="1:5")
            if range_input is None:
                return False
            self.playlist_range_input = range_input.strip()
        elif scope == "items":
            items_input = simpledialog.askstring(
                "Specific Items",
                "Enter specific items (e.g., '1,3,5' for items 1, 3, and 5):",
                initialvalue="1,3,5")
            if items_input is None:
                return False
            self.playlist_items_input = items_input.strip()
        return True

    def open_kofi_link(self):
        import webbrowser
        webbrowser.open("https://ko-fi.com/btrf")

    def open_yoomoney_link(self):
        import webbrowser
        webbrowser.open("https://yoomoney.ru/to/41001937179526")

    def parse_progress(self, line):
        progress_match = re.search(r'\[download\][^]]*?(\d+\.?\d*)%', line)
        if progress_match:
            try:
                progress = float(progress_match.group(1))
                self.progress_var.set(progress)
                self.root.update_idletasks()
            except ValueError:
                pass

        eta_match = re.search(r'ETA (\d{2}:\d{2}:\d{2}|\d{2}:\d{2})', line)
        speed_match = re.search(r'at ([\d.]+\s*[KMGT]iB/s)', line)

        if eta_match or speed_match:
            status_parts = []
            if speed_match:
                status_parts.append(f"Speed: {speed_match.group(1)}")
            if eta_match:
                status_parts.append(f"ETA: {eta_match.group(1)}")
            if status_parts:
                self.status_label.config(text=" | ".join(status_parts), foreground="blue")

    def show_template_help(self):
        help_text = """
Common Template Variables:
  %(title)s - Video title
  %(uploader)s - Channel/Uploader name
  %(upload_date)s - Upload date (YYYYMMDD)
  %(id)s - Video ID
  %(ext)s - File extension
  %(resolution)s - Video resolution
  %(duration)s - Video duration (seconds)
  %(view_count)s - View count
  %(like_count)s - Like count
  %(average_rating)s - Average rating
  %(playlist_title)s - Playlist title (if downloading from playlist)
  %(playlist_index)s - Playlist index (if downloading from playlist)

Examples:
  %(title)s.%(ext)s
  %(upload_date)s - %(title)s.%(ext)s
  %(uploader)s - %(title)s.%(ext)s
  %(title)s [%(id)s].%(ext)s
  %(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s
        """.strip()

        messagebox.showinfo("Filename Template Help", help_text)

    def load_links_from_file(self):
        file_path = filedialog.askopenfilename(
            title="Select file with URLs",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                urls = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(('#', ';', ']')):
                        urls.append(line)

                if urls:
                    self.url_list = urls
                    self.log_message(f"Loaded {len(urls)} URLs from {file_path}")
                    self.log_message(f"First few URLs: {urls[:3]}")

                    if len(urls) == 1:
                        self.url_entry.delete(0, tk.END)
                        self.url_entry.insert(0, urls[0])
                        self.log_message("Single URL loaded into the URL field")
                    else:
                        if messagebox.askyesno(
                                "Batch Download",
                                f"Loaded {len(urls)} URLs. Start batch download?"):
                            self.start_batch_download()
                else:
                    messagebox.showinfo("Info", "No valid URLs found in the file.")

            except Exception as e:
                messagebox.showerror("Error", f"Error reading file: {str(e)}")

    def start_batch_download(self):
        if not hasattr(self, 'url_list') or not self.url_list:
            messagebox.showerror("Error", "No URLs loaded. Load URLs from a file first.")
            return

        if not self._get_playlist_scope_input():
            return

        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="enabled")
        self.status_label.config(text=f"Batch downloading {len(self.url_list)} URLs...",
                                 foreground="orange")

        thread = threading.Thread(target=self.batch_download_worker)
        thread.daemon = True
        thread.start()

    def batch_download_worker(self):
        try:
            for i, url in enumerate(self.url_list):
                self.log_message(f"Downloading ({i+1}/{len(self.url_list)}): {url}")
                single_download_cmd = self.build_command(url)
                self.log_message(f"Running command: {' '.join(single_download_cmd)}")

                self.current_process = self._run_subprocess(single_download_cmd)

                for line in self.current_process.stdout:
                    self.log_message(f"[{i+1}/{len(self.url_list)}] {line.rstrip()}")
                    self.parse_progress(line)

                self.current_process.wait()

                if self.current_process.returncode == 0:
                    self.log_message(f"\u2713 Download completed for URL #{i+1}")
                else:
                    self.log_message(
                        f"\u2717 Download failed for URL #{i+1} "
                        f"with return code: {self.current_process.returncode}")

            self.status_label.config(text="Batch download completed!", foreground="green")
            self.log_message("All downloads completed!")

        except Exception as e:
            self.status_label.config(text="Batch download error!", foreground="red")
            self.log_message(f"Error during batch download: {str(e)}")
        finally:
            self.download_btn.config(state="enabled")
            self.cancel_btn.config(state="disabled")
            self.current_process = None

    def build_command(self, url):
        cmd = [self.yt_dlp_path]

        output_path = self.path_entry.get().strip()
        filename_template = self.filename_template_var.get().strip()
        if not filename_template:
            filename_template = "%(upload_date)s - %(title)s.%(ext)s"

        if output_path:
            if not output_path.endswith(os.sep):
                output_path += os.sep
            full_template = f"{output_path}{filename_template}"
            cmd.extend(["-o", full_template])
        else:
            cmd.extend(["-o", filename_template])

        if self.download_type.get() == "audio":
            cmd.extend(["-x", "--audio-format", self.format_var.get()])
            if self.ffmpeg_path != "ffmpeg":
                cmd.extend(["--ffmpeg-location", self.ffmpeg_path])
        else:
            cmd.extend(["--merge-output-format", self.format_var.get()])

        if self.quality_var.get() != "1080p":
            mapped_quality = self.map_quality_value(self.quality_var.get())
            cmd.extend(["-f", mapped_quality])

        self.add_playlist_items_option(cmd)
        cmd.append("--embed-metadata")

        additional_options = self.options_entry.get().strip()
        if additional_options:
            cmd.extend(additional_options.split())

        cmd.append(url)
        return cmd

    def cancel_download(self):
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.log_message("Download was cancelled by user")
            self.status_label.config(text="Download cancelled", foreground="red")
            self.progress_var.set(0)

        self.download_btn.config(state="enabled")
        self.cancel_btn.config(state="disabled")

    def toggle_playlist_scope(self, *args):
        if self.is_playlist.get():
            self.playlist_scope_combo.config(state="readonly")
        else:
            self.playlist_scope_combo.config(state="disabled")

    def add_playlist_items_option(self, cmd):
        scope = self.playlist_scope_var.get()

        if not self.is_playlist.get():
            return

        if scope == "all":
            cmd.append("--yes-playlist")
        elif scope == "first":
            cmd.extend(["--playlist-items", "1"])
        elif scope == "last":
            cmd.extend(["--playlist-items", "-1"])
        elif scope == "between":
            if hasattr(self, 'playlist_range_input'):
                cmd.extend(["--playlist-items", self.playlist_range_input])
            else:
                cmd.append("--yes-playlist")
        elif scope == "items":
            if hasattr(self, 'playlist_items_input'):
                cmd.extend(["--playlist-items", self.playlist_items_input])
            else:
                cmd.append("--yes-playlist")

    def load_config(self):
        default_config = {
            "yt_dlp_path": "bin/yt-dlp.exe",
            "ffmpeg_path": "bin/ffmpeg.exe",
            "default_download_path": os.path.expanduser("~/Downloads/yt-dlp")
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
                    return default_config
            else:
                self.save_config(default_config)
                return default_config
        except Exception as e:
            self.log_message(f"Error loading config: {e}, using defaults")
            return default_config

    def save_config(self, config=None):
        if config is None:
            config = {
                "yt_dlp_path": self.yt_dlp_path,
                "ffmpeg_path": self.ffmpeg_path,
                "default_download_path": self.default_dir
            }

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log_message(f"Error saving config: {e}")

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)

        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def open_settings(self):
        SettingsWindow(self)

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About yt-dlp GUI")
        about_window.geometry("500x300")
        about_window.resizable(True, True)
        about_window.transient(self.root)
        about_window.grab_set()

        main_frame = ttk.Frame(about_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="yt-dlp GUI",
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))

        version_label = ttk.Label(main_frame, text="Version 1.0",
                                  font=("Arial", 10))
        version_label.pack(pady=(0, 5))

        kofi_label = ttk.Label(main_frame,
                               text="Support the developer on Ko-fi",
                               font=("Arial", 10), foreground="blue",
                               cursor="hand2")
        kofi_label.pack(pady=(0, 5))
        kofi_label.bind("<Button-1>", lambda e: self.open_kofi_link())

        yoomoney_label = ttk.Label(main_frame,
                                   text="Support via YooMoney",
                                   font=("Arial", 10), foreground="blue",
                                   cursor="hand2")
        yoomoney_label.pack(pady=(0, 15))
        yoomoney_label.bind("<Button-1>", lambda e: self.open_yoomoney_link())

        description_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD,
                                                     width=60, height=15)
        description_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        about_text = """yt-dlp GUI

A graphical user interface for yt-dlp, a powerful command-line tool for downloading videos from YouTube and other sites.

Features:
\u2022 Download videos from hundreds of supported sites
\u2022 Choose video quality and format
\u2022 Extract audio only
\u2022 Download entire playlists
\u2022 Batch download from file
\u2022 Embed metadata in downloaded files
\u2022 Customize filename templates

This is a simple wrapper around yt-dlp that provides a user-friendly interface for common download tasks.

yt-dlp is a free software project that can download videos from many sites.
For more information about yt-dlp, visit: https://github.com/yt-dlp/yt-dlp

This GUI application is provided as-is with no warranty. Use at your own risk.
"""
        description_text.insert(tk.END, about_text)
        description_text.config(state=tk.DISABLED)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))

        ok_button = ttk.Button(button_frame, text="OK",
                               command=about_window.destroy)
        ok_button.pack()

        about_window.update_idletasks()
        x = (self.root.winfo_x() + self.root.winfo_width() // 2
             - about_window.winfo_width() // 2)
        y = (self.root.winfo_y() + self.root.winfo_height() // 2
             - about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")

    def map_quality_value(self, quality):
        quality_mapping = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]"
        }
        return quality_mapping.get(quality, quality)

    def on_download_type_change(self, *args):
        download_type = self.download_type.get()
        if download_type == "audio":
            self.quality_var.set("bestaudio")
            self.format_var.set("mp3")
        elif download_type == "video":
            self.quality_var.set("1080p")
            self.format_var.set("mp4")

    def show_url_context_menu(self, event):
        context_menu = Menu(self.root, tearoff=0)
        context_menu.add_command(label="Paste", command=self.paste_url,
                                 accelerator="Ctrl+V")
        context_menu.add_command(label="Clear", command=self.clear_url)
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=self.select_all_url)

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def paste_url(self):
        try:
            clipboard_content = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_content)
        except tk.TclError:
            pass

    def clear_url(self):
        self.url_entry.delete(0, tk.END)

    def select_all_url(self):
        self.url_entry.select_range(0, tk.END)
        self.url_entry.focus()

    def center_window(self):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"+{x}+{y}")


class SettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent.root)
        self.window.title("Settings")
        self.window.geometry("550x170")
        self.window.resizable(True, False)
        self.window.transient(parent.root)
        self.window.grab_set()

        settings_frame = ttk.Frame(self.window, padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(settings_frame, text="yt-dlp executable path:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.yt_dlp_path_var = tk.StringVar(value=parent.yt_dlp_path)
        self.yt_dlp_entry = ttk.Entry(settings_frame,
                                      textvariable=self.yt_dlp_path_var, width=50)
        self.yt_dlp_entry.grid(row=0, column=1, pady=5, padx=(5, 0))
        ttk.Button(settings_frame, text="Browse",
                   command=self.browse_yt_dlp).grid(row=0, column=2, pady=5, padx=(5, 0))

        ttk.Label(settings_frame, text="ffmpeg executable path:").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.ffmpeg_path_var = tk.StringVar(value=parent.ffmpeg_path)
        self.ffmpeg_entry = ttk.Entry(settings_frame,
                                      textvariable=self.ffmpeg_path_var, width=50)
        self.ffmpeg_entry.grid(row=1, column=1, pady=5, padx=(5, 0))
        ttk.Button(settings_frame, text="Browse",
                   command=self.browse_ffmpeg).grid(row=1, column=2, pady=5, padx=(5, 0))

        ttk.Label(settings_frame, text="Default download path:").grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.download_path_var = tk.StringVar(value=parent.default_dir)
        self.download_path_entry = ttk.Entry(
            settings_frame, textvariable=self.download_path_var, width=50)
        self.download_path_entry.grid(row=2, column=1, pady=5, padx=(5, 0))
        ttk.Button(settings_frame, text="Browse",
                   command=self.browse_download_path).grid(
            row=2, column=2, pady=5, padx=(5, 0))

        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="Save",
                   command=self.save_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel",
                   command=self.window.destroy).pack(side=tk.LEFT)

        self.center_window()

    def center_window(self):
        self.window.update_idletasks()
        x = (self.parent.root.winfo_x() + self.parent.root.winfo_width() // 2
             - self.window.winfo_width() // 2)
        y = (self.parent.root.winfo_y() + self.parent.root.winfo_height() // 2
             - self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

    def browse_yt_dlp(self):
        file_path = filedialog.askopenfilename(
            title="Select yt-dlp executable",
            filetypes=[("Executable files", "*"), ("All files", "*.*")])
        if file_path:
            self.yt_dlp_path_var.set(file_path)

    def browse_ffmpeg(self):
        file_path = filedialog.askopenfilename(
            title="Select ffmpeg executable",
            filetypes=[("Executable files", "*"), ("All files", "*.*")])
        if file_path:
            self.ffmpeg_path_var.set(file_path)

    def browse_download_path(self):
        dir_path = filedialog.askdirectory(
            title="Select default download directory",
            initialdir=self.download_path_var.get())
        if dir_path:
            self.download_path_var.set(dir_path)

    def save_settings(self):
        self.parent.yt_dlp_path = self.yt_dlp_path_var.get()
        self.parent.ffmpeg_path = self.ffmpeg_path_var.get()
        self.parent.default_dir = self.download_path_var.get()
        self.parent.save_config()
        messagebox.showinfo("Settings", "Settings saved successfully!")
        self.window.destroy()


if __name__ == "__main__":
    try:
        root = tk.Tk()
        YtDlpGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Error running GUI: {e}")
        import traceback
        traceback.print_exc()
