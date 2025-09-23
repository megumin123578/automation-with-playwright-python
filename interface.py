
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
        
        # state phân trang
        self.page = 1
        self.page_size = tk.IntVar(value=DEFAULT_PAGE_SIZE)
        self.all_rows = []

        self._build_form()
        self._build_table()
        self._build_pagination_bar()
        self._bind_shortcuts()

        self._reload_all_rows()
        self._refresh_table()



    def _build_form(self):
        frm = ttk.LabelFrame(self, text="Enter Data", padding=12)
        frm.pack(fill="x", padx=12, pady=(0, 12))

        # Model
        ttk.Label(frm, text="Model:").grid(row=0, column=0, sticky="w", padx=(0,8), pady=6)
        self.model_var = tk.StringVar(value=MODELS[0])
        self.model_box = ttk.Combobox(frm, textvariable=self.model_var, state="readonly", values=MODELS)
        self.model_box.grid(row=0, column=1, sticky="ew", pady=6)

        # Ratio 
        ttk.Label(frm, text="Ratio:").grid(row=0, column=2, sticky="w", padx=(16,8), pady=6)
        self.ratio_var = tk.StringVar(value=RATIOS[0])
        self.ratio_box = ttk.Combobox(frm, textvariable=self.ratio_var, state="readonly", values=RATIOS)
        self.ratio_box.grid(row=0, column=3, sticky="ew", pady=6)

        # Amount
        
        ttk.Label(frm, text="Amount:").grid(row=1, column=0, sticky="w", padx=(0,8), pady=6)
        self.amount_var = tk.StringVar(value=AMOUNTS[0])
        self.amount_box = ttk.Combobox(frm, textvariable=self.amount_var, state="readonly", values=AMOUNTS)
        self.amount_box.grid(row=1, column=1, sticky="ew", pady=6)


        # Upscale 4K
        self.upscale_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Upscale 4K", variable=self.upscale_var).grid(row=1, column=2, sticky="w", padx=(16,8), pady=6)

        # Prompt (multiline)
        ttk.Label(frm, text="Prompt:").grid(row=2, column=0, sticky="nw", padx=(0,8), pady=(6,4))
        self.prompt_txt = ScrolledText(frm, height=4, wrap="word")
        self.prompt_txt.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(6,4))

        #Status
        self.status_var = tk.StringVar(value="Working")

        # buttons
        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=4, sticky="e", pady=(8,0))
        ttk.Button(btns, text="Save (Ctrl+S)", command=self.save_row).pack(side="right")
        
        for i in (1,3):
            frm.columnconfigure(i, weight=1)

    def _build_table(self):
        self.tree = ttk.Treeview(self, columns=CSV_HEADERS, show="headings")
        for col in CSV_HEADERS:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=140)
        self.tree.pack(fill="both", expand=True, padx=12)

        self.tree.tag_configure("Done", background="#d1f7d1")
        self.tree.tag_configure("Working", background="#fff2b3")


        self.tree.bind("<Double-1>", self._on_row_double_click)

    def _build_pagination_bar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(bar, text="Page size:").pack(side="left")
        cb = ttk.Combobox(bar, values=PAGE_SIZE_CHOICES, state="readonly", textvariable=self.page_size, width=5)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())

        # Nav buttons
        ttk.Button(bar, text="⏮ First", command=lambda: self._goto_page(1)).pack(side="left")
        ttk.Button(bar, text="◀ Before", command=self._prev_page).pack(side="left", padx=(6,0))
        ttk.Button(bar, text="After ▶", command=self._next_page).pack(side="left", padx=(6,0))
        self.last_btn = ttk.Button(bar, text="Last ⏭", command=self._goto_last_page)
        self.last_btn.pack(side="left", padx=(6,12))

        self.page_info = ttk.Label(bar, text="")
        self.page_info.pack(side="left", padx=12)

        # Spacer
        ttk.Label(bar, text="").pack(side="right")

    def _bind_shortcuts(self):
        self.bind_all("<Control-s>", lambda e: self.save_row())
        self.bind_all("<Control-S>", lambda e: self.save_row())
        self.bind_all("<Control-q>", lambda e: self.quit())
        self.bind_all("<Control-Q>", lambda e: self.quit())
        self.bind_all("<Control-l>", lambda e: self.clear_form())
        self.bind_all("<Control-L>", lambda e: self.clear_form())
        self.bind_all("<F5>", lambda e: self._reload_and_refresh())

    # ----- Actions ----
    def _reload_and_refresh(self):
        self._reload_all_rows()
        self._refresh_table()

    def save_row(self):
        model = self.model_var.get().strip()
        ratio = self.ratio_var.get().strip()
        amount_str = self.amount_var.get().strip().replace(",", "")
        prompt = self.prompt_txt.get("1.0", "end").strip()
        upscale = "✔" if self.upscale_var.get() else "✖"
        status = self.status_var.get()

        if not model:
            messagebox.showwarning("Missing Value", "Please choose Model.")
            return
        if not ratio:
            messagebox.showwarning("Missing Value", "Please choose Ratio.")
            return
        if not prompt:
            messagebox.showwarning("Missing Value", "Missing prompt!.")
            return


        row = {
            "model": model,
            "ratio": ratio,
            "amount": int(amount_str),
            "prompt": prompt,
            "upscale 4k": upscale,
            "status": status,
        }
        try:
            self.csv.append_row(row)
        except Exception as e:
            messagebox.showerror("Can't write to file", f"file:\n{e}")
            return

        self._reload_all_rows()
        self._goto_last_page()
        self.clear_form(keep_selections=True)

    def clear_form(self, keep_selections=False):
        if not keep_selections:
            self.model_box.current(0)
            self.ratio_box.current(0)
            self.upscale_var.set(False)
        self.amount_var.set(1)
        self.prompt_txt.delete("1.0", "end")

    # ----- Table helpers -----
    def _reload_all_rows(self):
        try:
            self.all_rows = self.csv.read_all()
        except Exception as e:
            self.all_rows = []
            messagebox.showerror("Lỗi đọc file", f"Không thể đọc CSV:\n{e}")

    def _refresh_table(self):
        # Clear
        for i in self.tree.get_children():
            self.tree.delete(i)

        total = len(self.all_rows)
        ps = max(1, int(self.page_size.get() or DEFAULT_PAGE_SIZE))
        total_pages = max(1, (total + ps - 1) // ps)

        # Clamp page
        if self.page < 1:
            self.page = 1
        if self.page > total_pages:
            self.page = total_pages

        start = (self.page - 1) * ps
        end = min(start + ps, total)
        # Insert rows for current page
        page_rows = self.all_rows[start:end]

        # Nếu file có cột thiếu, vẫn hiển thị trống cho đúng header
        for r in page_rows:
            values = []
            for col in CSV_HEADERS:
                val = r.get(col, "")
                if col == "prompt":
                    # rút gọn khi hiển thị để bảng gọn gàng
                    if val and len(val) > 140:
                        val = val[:137] + "…"
                values.append(val)
            self.tree.insert("", "end", values=values)

        self.page_info.config(text=f"Page {self.page}/{total_pages} (Total {total} lines)")

    def _change_page_size(self):
        self.page = 1
        self._refresh_table()

    def _prev_page(self):
        self.page -= 1
        self._refresh_table()

    def _next_page(self):
        self.page += 1
        self._refresh_table()

    def _goto_page(self, p):
        self.page = int(p)
        self._refresh_table()

    def _goto_last_page(self):
        total = len(self.all_rows)
        ps = max(1, int(self.page_size.get() or DEFAULT_PAGE_SIZE))
        total_pages = max(1, (total + ps - 1) // ps)
        self.page = total_pages
        self._refresh_table()

    def _on_row_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        values = self.tree.item(item_id, "values")
        detail = tk.Toplevel(self)
        detail.title("Chi tiết bản ghi")
        detail.geometry("720x420")
        frame = ttk.Frame(detail, padding=12)
        frame.pack(fill="both", expand=True)

        for idx, col in enumerate(CSV_HEADERS):
            ttk.Label(frame, text=col + ":", font=("", 10, "bold")).grid(row=idx, column=0, sticky="nw", padx=(0,8), pady=4)
            if col == "prompt":
                txt = ScrolledText(frame, height=6, wrap="word")
                txt.grid(row=idx, column=1, sticky="nsew")
                txt.insert("1.0", values[idx] if idx < len(values) else "")
                txt.configure(state="disabled")
            else:
                val_lbl = ttk.Label(frame, text=(values[idx] if idx < len(values) else ""))
                val_lbl.grid(row=idx, column=1, sticky="w")
        frame.columnconfigure(1, weight=1)
        ttk.Button(frame, text="Đóng", command=detail.destroy).grid(row=len(CSV_HEADERS), column=1, sticky="e", pady=(8,0))

def main():
    # Đặt working dir về vị trí file .py khi chạy double-click
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass

    app = App(DEFAULT_CSV)
    app.mainloop()

if __name__ == "__main__":
    main()
