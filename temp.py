
import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import tkinter.font as tkfont
from interface_module import *



class App(tk.Tk):
    def __init__(self, csv_path=DEFAULT_CSV):
        super().__init__()
        self.title(APP_TITLE)
        self.state("zoomed")

        font = tkfont.nametofont("TkDefaultFont")
        font.configure(size=12)
        self.option_add("*Font", font)

        self.csv = CSVManager(csv_path)
        self.page = 1
        self.page_size = tk.IntVar(value=DEFAULT_PAGE_SIZE)
        self.all_rows = []

        self._build_form()
        self._build_table()
        self._build_pagination()

        self._reload_all_rows()
        self._goto_last_page()

    def _build_form(self):
        frm = ttk.LabelFrame(self, text="Nhập dữ liệu", padding=12)
        frm.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(frm, text="Model:").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar(value=MODELS[0])
        ttk.Combobox(frm, textvariable=self.model_var, values=MODELS, state="readonly").grid(row=0, column=1, sticky="ew")

        ttk.Label(frm, text="Ratio:").grid(row=0, column=2, sticky="w")
        self.ratio_var = tk.StringVar(value=RATIOS[0])
        ttk.Combobox(frm, textvariable=self.ratio_var, values=RATIOS, state="readonly").grid(row=0, column=3, sticky="ew")

        ttk.Label(frm, text="Amount:").grid(row=1, column=0, sticky="w")
        self.amount_var = tk.StringVar(value=AMOUNTS[0])
        ttk.Combobox(frm, textvariable=self.amount_var, values=AMOUNTS, state="readonly").grid(row=1, column=1, sticky="ew")

        ttk.Label(frm, text="Upscale 4K").grid(row=1, column=2, sticky="w")
        self.upscale_var = tk.BooleanVar()
        ttk.Checkbutton(frm, variable=self.upscale_var).grid(row=1, column=3, sticky="w")

        ttk.Label(frm, text="Prompt:").grid(row=2, column=0, sticky="nw")
        self.prompt_txt = ScrolledText(frm, height=3)
        self.prompt_txt.grid(row=2, column=1, columnspan=3, sticky="ew")

        self.status_var = tk.StringVar(value="Working")

        ttk.Button(frm, text="Lưu", command=self.save_row).grid(row=3, column=3, sticky="e")
        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(3, weight=1)

    def _build_table(self):
        self.tree = ttk.Treeview(self, columns=CSV_HEADERS, show="headings")
        for col in CSV_HEADERS:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=140)
        self.tree.pack(fill="both", expand=True, padx=12)

        self.tree.tag_configure("done", background="#d1f7d1")
        self.tree.tag_configure("working", background="#fff2b3")

    def _build_pagination(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(bar, text="Page size:").pack(side="left")
        cb = ttk.Combobox(bar, values=PAGE_SIZE_CHOICES, state="readonly", textvariable=self.page_size, width=5)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())

        ttk.Button(bar, text="<<", command=lambda: self._goto_page(1)).pack(side="left")
        ttk.Button(bar, text="<", command=self._prev_page).pack(side="left")
        ttk.Button(bar, text=">", command=self._next_page).pack(side="left")
        ttk.Button(bar, text=">>", command=self._goto_last_page).pack(side="left")

        self.page_info = ttk.Label(bar, text="")
        self.page_info.pack(side="left", padx=12)

    def save_row(self):
        row = {
            "model": self.model_var.get(),
            "ratio": self.ratio_var.get(),
            "amount": self.amount_var.get(),
            "prompt": self.prompt_txt.get("1.0", "end").strip(),
            "upscale 4k": "yes" if self.upscale_var.get() else "no",
            "status": self.status_var.get()
        }
        self.csv.append_row(row)
        self._reload_all_rows()
        self._goto_last_page()

    def _reload_all_rows(self):
        self.all_rows = self.csv.read_all()

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        ps = self.page_size.get()
        total = len(self.all_rows)
        pages = max(1, (total + ps - 1) // ps)
        self.page = min(max(1, self.page), pages)
        start = (self.page - 1) * ps
        end = start + ps
        rows = self.all_rows[start:end]

        for row in rows:
            tag = "done" if row.get("status") == "Done" else "working"
            self.tree.insert("", "end", values=[row.get(h, "") for h in CSV_HEADERS], tags=(tag,))

        self.page_info.config(text=f"Page {self.page}/{pages} ({total} rows)")

    def _goto_page(self, p):
        self.page = p
        self._refresh_table()

    def _prev_page(self):
        self.page -= 1
        self._refresh_table()

    def _next_page(self):
        self.page += 1
        self._refresh_table()

    def _goto_last_page(self):
        total = len(self.all_rows)
        ps = self.page_size.get()
        pages = max(1, (total + ps - 1) // ps)
        self.page = pages
        self._refresh_table()

if __name__ == "__main__":
    App().mainloop()
