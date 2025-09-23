import os
import csv
import os

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
APP_TITLE = "Tool Veo3"
DEFAULT_CSV = "queued.csv"
CSV_HEADERS = ["model", "ratio", "amount", "prompt", "upscale 4k", 'status']
CSV_ENCODING = "utf-8-sig"    
CSV_DELIMITER = "," 

DEFAULT_PAGE_SIZE = 25
PAGE_SIZE_CHOICES = [10, 25, 50, 100]

MODELS = ["Veo3-Fast", "Veo3-Quality", "Veo2-Fast", "Veo2-Quality"]
RATIOS = ["16:9", "9:16"]
AMOUNTS = [1,2,3,4]

def shorten_path(path: str, maxlen: int = 60) -> str:
    if len(path) <= maxlen:
        return path
    head, tail = os.path.split(path)
    if len(tail) + 5 >= maxlen:
        return "..." + tail[-(maxlen-3):]
    remain = maxlen - len(tail) - 5
    return head[:remain] + "..." + os.sep + tail

class CSVManager:
    def __init__(self, path):
        self.path = path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            with open(self.path, "w", newline="", encoding=CSV_ENCODING) as f:
                writer = csv.writer(f, delimiter=CSV_DELIMITER)
                writer.writerow(CSV_HEADERS)

    def append_row(self, row_dict):
        with open(self.path, "a", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, delimiter=CSV_DELIMITER)
            writer.writerow(row_dict)

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", newline="", encoding=CSV_ENCODING) as f:
            return list(csv.DictReader(f, delimiter=CSV_DELIMITER))
    def __init__(self, path: str):
        self.path = path
        self._ensure_file()

    def set_path(self, path: str):
        self.path = path
        self._ensure_file()

    def _ensure_file(self):
        folder = os.path.dirname(os.path.abspath(self.path))
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        need_header = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        if need_header:
            with open(self.path, "w", newline="", encoding=CSV_ENCODING) as f:
                writer = csv.writer(f, delimiter=CSV_DELIMITER)
                writer.writerow(CSV_HEADERS)

    def append_row(self, row_dict: dict):
        # Đảm bảo chỉ ghi các cột định nghĩa
        row = {h: row_dict.get(h, "") for h in CSV_HEADERS}
        with open(self.path, "a", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(
                f, fieldnames=CSV_HEADERS, delimiter=CSV_DELIMITER, quoting=csv.QUOTE_MINIMAL
            )
            writer.writerow(row)

    def read_all(self):
        rows = []
        if not os.path.exists(self.path):
            return rows
        with open(self.path, "r", newline="", encoding=CSV_ENCODING) as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            for r in reader:
                rows.append(r)
        return rows