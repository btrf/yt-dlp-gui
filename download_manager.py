import subprocess
import threading
import queue
import os
import json
import re
import sys

class DownloadManager:
    """
    Framework-agnostic manager for handling yt-dlp operations.
    This class encapsulates command building, execution, and progress monitoring.
    """
    def __init__(self, yt_dlp_path, ffmpeg_path, default_dir, config):
        self.yt_dlp_path = yt_dlp_path
        self.ffmpeg_path = ffmpeg_path
        self.default_dir = default_dir
        self.config = config
        self.is_running = False
        self.cancelled = False
        self.process = None
        self.output_queue = queue.Queue()

    def build_command(self, url, is_playlist=False, playlist_items="", filename_template="%(upload_date)s - %(title)s.%(ext)s", download_type="video", quality="1080p", extra_options="", output_format=""):
        """Constructs the full yt-dlp command list."""
        cmd = [self.yt_dlp_path]
        
        # 1. Output Path construction
        output_path = self.config.get("default_download_path", self.default_dir)
        if output_path:
            if not output_path.endswith(os.sep):
                output_path += os.sep
            full_template = f"{output_path}{filename_template}"
            cmd.extend(["-o", full_template])
        else:
            cmd.extend(["-o", filename_template])
        
        # 2. Download Type and Format
        if download_type == "audio":
            audio_format = output_format if output_format in ("mp3", "m4a", "wav") else "mp3"
            cmd.extend(["-x", "--audio-format", audio_format])
            if self.ffmpeg_path != "ffmpeg":
                cmd.extend(["--ffmpeg-location", self.ffmpeg_path])
        else: # Video
            video_format = output_format if output_format in ("mp4", "mkv", "webm", "flv", "avi", "mov") else "mp4"
            cmd.extend(["--merge-output-format", video_format])
            
        # 3. Quality
        mapped_quality = self._map_quality_value(quality)
        cmd.extend(["-f", mapped_quality])
        
        # 4. Playlist options
        if is_playlist:
            spec = (playlist_items or "").strip()
            if spec == "first":
                spec = "1"
            elif spec == "last":
                spec = "-1"
            if spec in ("", "all"):
                cmd.append("--yes-playlist")
            else:
                cmd.extend(["--playlist-items", spec])
        
        cmd.extend(["--embed-metadata"])
        
        # 5. Additional options
        if extra_options:
            cmd.extend(extra_options.split())
            
        cmd.append(url)
        return cmd

    def _map_quality_value(self, quality):
        quality_mapping = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]"
        }
        return quality_mapping.get(quality, quality)

    def start_download(self, url, playlist_items="", filename_template="", download_type="video", quality="1080p", extra_options="", output_format=""):
        """Starts the download process in a separate thread."""
        if self.is_running:
            return False
            
        cmd = self.build_command(url, is_playlist=bool(playlist_items), playlist_items=playlist_items, filename_template=filename_template, download_type=download_type, quality=quality, extra_options=extra_options, output_format=output_format)
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.is_running = True
        
        # Start thread to process output
        output_thread = threading.Thread(
            target=self._enqueue_output,
            args=(self.process.stdout, self.output_queue))
        output_thread.daemon = True
        output_thread.start()
        
        return True

    def _enqueue_output(self, out, q):
        """Reads all stdout lines from the subprocess and puts them in the queue."""
        for line in iter(out.readline, ''):
            q.put(line)
        q.put(None) # Sentinel value to signal end of output

    def get_next_output(self, timeout=0.1):
        """Retrieves the next line of output from the download process."""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def parse_progress(self, line):
        """Parses download progress from a line of stdout."""
        progress_match = re.search(r'\[download\][^]]*?(\d+\.?\d*)%', line)
        if progress_match:
            try:
                return float(progress_match.group(1))
            except ValueError:
                return None
        
        eta_match = re.search(r'ETA (\d{2}:\d{2}:\d{2}|\d{2}:\d{2})', line)
        speed_match = re.search(r'at ([\d.]+\s*[KMGT]iB/s)', line)
        
        status = []
        if speed_match:
            status.append(f"Speed: {speed_match.group(1)}")
        if eta_match:
            status.append(f"ETA: {eta_match.group(1)}")
        
        return status if status else None

    def check_status(self):
        """Checks if the download is complete or failed."""
        if not self.is_running and self.process is None:
            return "Ready"
            
        if self.process and self.process.poll() is not None:
            return "Completed" if self.process.returncode == 0 else f"Failed (RC: {self.process.returncode})"
            
        return "Running"

    def terminate(self):
        """Stops the running process gracefully."""
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.is_running = False
            self.process = None
            return True
        return False

# --- Helper function to mimic config loading for testing ---
def load_dummy_config():
    launch_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    default_download_path = r"C:\Downloads"
    if not os.path.isdir(default_download_path):
        default_download_path = launch_dir
    return {
        "yt_dlp_path": "bin/yt-dlp.exe",
        "ffmpeg_path": "bin/ffmpeg.exe",
        "default_download_path": default_download_path
    }
