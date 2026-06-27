"""
Layer 6 — Folder Watcher
Watches input/ directory for new image drops and triggers pipeline runs.
"""

import logging
import time
from pathlib import Path
from typing import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class ImageDropHandler(FileSystemEventHandler):
    def __init__(self, on_new_image: Callable[[Path], None]):
        super().__init__()
        self.on_new_image = on_new_image

    def on_created(self, event):
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                log.info(f"New image detected: {path.name}")
                # Small delay to ensure file write is complete
                time.sleep(1)
                self.on_new_image(path)


class FolderWatcher:
    def __init__(self, watch_dir: Path, on_new_image: Callable[[Path], None]):
        self.watch_dir = watch_dir
        self.handler = ImageDropHandler(on_new_image)
        self.observer = Observer()

    def start(self):
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        log.info(f"Watching {self.watch_dir} for new images...")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        log.info("Watcher stopped")

    def join(self):
        """Block main thread while watching."""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
