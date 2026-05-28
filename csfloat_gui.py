"""
CSFloat Price Checker — Interface Graphique
============================================
Lance ce fichier directement ou compile-le en .exe avec build.bat
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import statistics
import json
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Constantes ────────────────────────────────────────────────────────────────
API_BASE = "https://csfloat.com/api/v1"

WEAR_OPTIONS = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
FLOAT_RANGES = {
    "Factory New":    (0.00, 0.07),
    "Minimal Wear":   (0.07, 0.15),
    "Field-Tested":   (0.15, 0.38),
    "Well-Worn":      (0.38, 0.45),
    "Battle-Scarred": (0.45, 1.00),
}
CATEGORY_MAP = {"Tous": 0, "Normal": 1, "StatTrak™": 2, "Souvenir": 3}

# ── Palette ───────────────────────────────────────────────────────────────────
BG        = "#0d0f14"
BG2       = "#13161e"
BG3       = "#1a1e29"
CARD      = "#1e2230"
ACCENT    = "#e8a92a"        # orange-or CSFloat
ACCENT2   = "#3d8ef0"        # bleu highlight
GREEN     = "#2ecc71"
RED       = "#e74c3c"
TEXT      = "#e8eaf0"
MUTED     = "#6b7280"
BORDER    = "#2a2f3d"

FONT_TITLE  = ("Consolas", 20, "bold")
FONT_HEAD   = ("Consolas", 11, "bold")
FONT_BODY   = ("Consolas", 10)
FONT_SMALL  = ("Consolas", 9)
FONT_STAT   = ("Consolas", 22, "bold")

# ── Helpers API ───────────────────────────────────────────────────────────────

def cents_to_usd(cents) -> str:
    return f"${cents / 100:.2f}"

def fetch_listings(api_key: str, market_hash_name: str,
                   min_float: float, max_float: float,
                   category: int) -> list[dict]:
    headers = {"Authorization": api_key}
    params = {
        "market_hash_name": market_hash_name,
        "limit": 50,
        "sort_by": "lowest_price",
        "type": "buy_now",
        "category": category,
        "min_float": min_float,
        "max_float": max_float,
    }
    resp = requests.get(f"{API_BASE}/listings", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("data", [])

def analyze_prices(listings: list[dict]) -> dict:
    prices = [l["price"] for l in listings if "price" in l]
    if not prices:
        return {}
    return {
        "count":  len(prices),
        "min":    min(prices),
        "max":    max(prices),
        "mean":   statistics.mean(prices),
        "median": statistics.median(prices),
        "stdev":  statistics.stdev(prices) if len(prices) > 1 else 0,
    }

# ── Widgets custom ─────────────────────────────────────────────────────────────

class HoverButton(tk.Label):
    def __init__(self, parent, text, command, bg=ACCENT, fg=BG,
                 hover_bg=None, font=FONT_HEAD, padx=20, pady=8, **kw):
        self._bg = bg
        self._hbg = hover_bg or ACCENT2
        self._cmd = command
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font,
                         padx=padx, pady=pady, cursor="hand2", **kw)
        self.bind("<Enter>",  lambda e: self.config(bg=self._hbg))
        self.bind("<Leave>",  lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: command())

class Separator(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, height=1, bg=BORDER, **kw)

# ── Application principale ────────────────────────────────────────────────────

class CSFloatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSFloat Price Checker")
        self.geometry("860x700")
        self.minsize(760, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        # État
        self.api_key    = tk.StringVar(value=os.getenv("CSFLOAT_API_KEY", ""))
        self.weapon_var = tk.StringVar()
        self.wear_var   = tk.StringVar(value="Field-Tested")
        self.cat_var    = tk.StringVar(value="Normal")
        self.listings_cache: list[dict] = []
        self.stats_cache: dict = {}

        self._build_ui()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        # En-tête
        header = tk.Frame(self, bg=BG2, pady=0)
        header.pack(fill="x")

        tk.Frame(header, bg=ACCENT, width=4).pack(side="left", fill="y")
        inner_h = tk.Frame(header, bg=BG2, padx=20, pady=14)
        inner_h.pack(side="left", fill="both", expand=True)

        tk.Label(inner_h, text="◈  CSFLOAT PRICE CHECKER",
                 font=FONT_TITLE, bg=BG2, fg=ACCENT).pack(side="left")
        tk.Label(inner_h, text="v1.0", font=FONT_SMALL,
                 bg=BG2, fg=MUTED).pack(side="left", padx=(8, 0), pady=(6, 0))

        # Indicateur statut API
        self.status_dot = tk.Label(inner_h, text="●", font=("Consolas", 14),
                                   bg=BG2, fg=MUTED)
        self.status_dot.pack(side="right", padx=(0, 4))
        self.status_lbl = tk.Label(inner_h, text="Non configurée",
                                   font=FONT_SMALL, bg=BG2, fg=MUTED)
        self.status_lbl.pack(side="right")

        Separator(self).pack(fill="x")

        # Corps principal (2 colonnes)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Colonne gauche : formulaire ─────────────────────────────────────
        left = tk.Frame(body, bg=BG2, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Frame(left, bg=BORDER, width=1).pack(side="right", fill="y")

        form = tk.Frame(left, bg=BG2, padx=20, pady=20)
        form.pack(fill="both", expand=True)

        # Clé API
        self._section(form, "CLÉ API")
        api_frame = tk.Frame(form, bg=BG3, highlightbackground=BORDER,
                             highlightthickness=1)
        api_frame.pack(fill="x", pady=(4, 12))
        self.api_entry = tk.Entry(api_frame, textvariable=self.api_key,
                                  bg=BG3, fg=TEXT, insertbackground=ACCENT,
                                  font=FONT_SMALL, bd=0, show="•",
                                  highlightthickness=0)
        self.api_entry.pack(fill="x", padx=8, pady=6)

        show_btn = tk.Label(form, text="Afficher / Masquer la clé",
                            font=FONT_SMALL, bg=BG2, fg=ACCENT2,
                            cursor="hand2")
        show_btn.pack(anchor="w")
        show_btn.bind("<Button-1>", self._toggle_key_visibility)
        self._key_visible = False

        HoverButton(form, "✓  Valider la clé", self._validate_key,
                    bg=BG3, fg=ACCENT, hover_bg=BORDER, padx=14, pady=6
                    ).pack(fill="x", pady=(6, 16))

        Separator(form).pack(fill="x", pady=(0, 16))

        # Arme
        self._section(form, "ARME")
        weapon_frame = tk.Frame(form, bg=BG3, highlightbackground=BORDER,
                                highlightthickness=1)
        weapon_frame.pack(fill="x", pady=(4, 12))
        tk.Entry(weapon_frame, textvariable=self.weapon_var,
                 bg=BG3, fg=TEXT, insertbackground=ACCENT,
                 font=FONT_BODY, bd=0, highlightthickness=0,
                 ).pack(fill="x", padx=8, pady=8)

        tk.Label(form, text="ex: AK-47 | Redline  ou  AWP | Dragon Lore",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w", pady=(0, 12))

        # Qualité
        self._section(form, "QUALITÉ")
        wear_cb = ttk.Combobox(form, textvariable=self.wear_var,
                               values=WEAR_OPTIONS, state="readonly",
                               font=FONT_BODY)
        self._style_combobox(wear_cb)
        wear_cb.pack(fill="x", pady=(4, 12))

        # Type
        self._section(form, "TYPE")
        cat_cb = ttk.Combobox(form, textvariable=self.cat_var,
                              values=list(CATEGORY_MAP.keys()), state="readonly",
                              font=FONT_BODY)
        self._style_combobox(cat_cb)
        cat_cb.pack(fill="x", pady=(4, 16))

        Separator(form).pack(fill="x", pady=(0, 16))

        # Bouton recherche
        self.search_btn = HoverButton(form, "⌕  RECHERCHER",
                                      self._start_search,
                                      bg=ACCENT, fg=BG,
                                      hover_bg="#f5bc3a",
                                      font=("Consolas", 12, "bold"),
                                      pady=10)
        self.search_btn.pack(fill="x")

        # Bouton export
        HoverButton(form, "↓  Exporter JSON", self._export_json,
                    bg=BG3, fg=TEXT, hover_bg=BORDER,
                    padx=14, pady=6
                    ).pack(fill="x", pady=(8, 0))

        # ── Colonne droite : résultats ──────────────────────────────────────
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self.results_frame = tk.Frame(right, bg=BG)
        self.results_frame.pack(fill="both", expand=True)

        self._show_placeholder()

    def _section(self, parent, text):
        tk.Label(parent, text=text, font=FONT_SMALL,
                 bg=BG2, fg=MUTED).pack(anchor="w")

    def _style_combobox(self, cb):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TCombobox",
                        fieldbackground=BG3,
                        background=BG3,
                        foreground=TEXT,
                        arrowcolor=ACCENT,
                        bordercolor=BORDER,
                        lightcolor=BG3,
                        darkcolor=BG3,
                        insertcolor=TEXT,
                        selectbackground=CARD,
                        selectforeground=TEXT)
        style.map("TCombobox",
                  fieldbackground=[("readonly", BG3)],
                  foreground=[("readonly", TEXT)],
                  background=[("readonly", BG3)])

    # ── Placeholder ───────────────────────────────────────────────────────────

    def _show_placeholder(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        ph = tk.Frame(self.results_frame, bg=BG)
        ph.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(ph, text="◈", font=("Consolas", 48),
                 bg=BG, fg=BORDER).pack()
        tk.Label(ph, text="Lance une recherche\npour voir les prix",
                 font=FONT_BODY, bg=BG, fg=MUTED,
                 justify="center").pack(pady=8)

    # ── Validation clé ────────────────────────────────────────────────────────

    def _toggle_key_visibility(self, _=None):
        self._key_visible = not self._key_visible
        self.api_entry.config(show="" if self._key_visible else "•")

    def _validate_key(self):
        key = self.api_key.get().strip()
        if not key:
            self._set_status("Clé vide", RED)
            return
        self._set_status("Vérification…", ACCENT)
        self.update()
        try:
            r = requests.get(f"{API_BASE}/listings",
                             headers={"Authorization": key},
                             params={"limit": 1}, timeout=10)
            if r.status_code == 401:
                self._set_status("Clé invalide", RED)
            elif r.status_code in (200, 400):
                self._set_status("Clé valide ✓", GREEN)
                os.environ["CSFLOAT_API_KEY"] = key
            else:
                self._set_status(f"Erreur {r.status_code}", RED)
        except Exception:
            self._set_status("Réseau KO", RED)

    def _set_status(self, text: str, color: str):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    # ── Recherche ─────────────────────────────────────────────────────────────

    def _start_search(self):
        key    = self.api_key.get().strip()
        weapon = self.weapon_var.get().strip()
        wear   = self.wear_var.get()
        cat    = CATEGORY_MAP[self.cat_var.get()]

        if not key:
            messagebox.showerror("Clé manquante", "Entre ta clé API CSFloat.")
            return
        if not weapon:
            messagebox.showerror("Arme manquante", "Entre le nom d'une arme.")
            return

        market_hash_name = f"{weapon} ({wear})"
        min_f, max_f = FLOAT_RANGES[wear]

        self._show_loading(market_hash_name)
        self.search_btn.config(state="disabled") if hasattr(self.search_btn, "config") else None

        threading.Thread(
            target=self._fetch_thread,
            args=(key, market_hash_name, min_f, max_f, cat),
            daemon=True
        ).start()

    def _fetch_thread(self, key, market_hash_name, min_f, max_f, cat):
        try:
            listings = fetch_listings(key, market_hash_name, min_f, max_f, cat)
            stats    = analyze_prices(listings)
            self.after(0, self._show_results, market_hash_name, listings, stats)
        except requests.HTTPError as e:
            code = e.response.status_code
            msg  = "Clé API invalide." if code == 401 else \
                   "Rate limit atteint, attends quelques minutes." if code == 429 else \
                   f"Erreur HTTP {code}"
            self.after(0, self._show_error, msg)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    # ── Affichage résultats ───────────────────────────────────────────────────

    def _show_loading(self, name):
        for w in self.results_frame.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_frame, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="⟳", font=("Consolas", 36),
                 bg=BG, fg=ACCENT).pack()
        tk.Label(f, text=f"Recherche en cours…\n{name}",
                 font=FONT_BODY, bg=BG, fg=MUTED,
                 justify="center").pack(pady=8)

    def _show_error(self, msg):
        for w in self.results_frame.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_frame, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="✕", font=("Consolas", 36),
                 bg=BG, fg=RED).pack()
        tk.Label(f, text=msg, font=FONT_BODY, bg=BG,
                 fg=RED, justify="center", wraplength=300).pack(pady=8)

    def _show_results(self, name: str, listings: list, stats: dict):
        self.listings_cache = listings
        self.stats_cache    = stats

        for w in self.results_frame.winfo_children():
            w.destroy()

        canvas = tk.Canvas(self.results_frame, bg=BG, bd=0, highlightthickness=0)
        scroll = tk.Scrollbar(self.results_frame, orient="vertical",
                              command=canvas.yview, bg=BG2,
                              troughcolor=BG2, activebackground=ACCENT)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)

        inner = tk.Frame(canvas, bg=BG)
        canvas_win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Scroll souris
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        pad = tk.Frame(inner, bg=BG, padx=24, pady=20)
        pad.pack(fill="both", expand=True)

        # Titre
        tk.Label(pad, text=name, font=("Consolas", 13, "bold"),
                 bg=BG, fg=ACCENT, wraplength=520, justify="left"
                 ).pack(anchor="w")
        Separator(pad).pack(fill="x", pady=(8, 16))

        if not stats:
            tk.Label(pad, text="Aucun listing trouvé pour cette recherche.",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(anchor="w")
            return

        # ── Cartes stats ──────────────────────────────────────────────────
        cards_row = tk.Frame(pad, bg=BG)
        cards_row.pack(fill="x", pady=(0, 16))

        stat_items = [
            ("MINIMUM",  cents_to_usd(stats["min"]),   GREEN),
            ("MOYENNE",  cents_to_usd(int(stats["mean"])), ACCENT),
            ("MÉDIANE",  cents_to_usd(int(stats["median"])), ACCENT2),
            ("MAXIMUM",  cents_to_usd(stats["max"]),   RED),
        ]
        for i, (label, value, color) in enumerate(stat_items):
            card = tk.Frame(cards_row, bg=CARD,
                            highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, padx=(0, 8) if i < 3 else 0,
                      sticky="nsew")
            cards_row.columnconfigure(i, weight=1)

            tk.Label(card, text=label, font=FONT_SMALL,
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=12, pady=(10, 0))
            tk.Label(card, text=value, font=FONT_STAT,
                     bg=CARD, fg=color).pack(anchor="w", padx=12)
            tk.Label(card, text=" ", font=FONT_SMALL,
                     bg=CARD, fg=MUTED).pack(pady=(0, 8))

        # Infos secondaires
        info_row = tk.Frame(pad, bg=BG)
        info_row.pack(fill="x", pady=(0, 16))

        tk.Label(info_row,
                 text=f"● {stats['count']} listings analysés",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left")
        if stats.get("stdev"):
            tk.Label(info_row,
                     text=f"  ±  Écart-type : {cents_to_usd(int(stats['stdev']))}",
                     font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left")

        Separator(pad).pack(fill="x", pady=(0, 14))

        # ── Table listings ────────────────────────────────────────────────
        tk.Label(pad, text="LISTINGS (triés par prix croissant)",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 6))

        table = tk.Frame(pad, bg=BG)
        table.pack(fill="x")

        headers = ["#", "Prix", "Float", "Wear", "StatTrak"]
        widths   = [3, 12, 12, 16, 10]
        for col, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(table, text=h, font=FONT_SMALL,
                     bg=BG3, fg=MUTED, width=w, anchor="w",
                     padx=8, pady=4
                     ).grid(row=0, column=col, sticky="ew", padx=(0, 1))
        for col in range(len(headers)):
            table.columnconfigure(col, weight=widths[col])

        for i, listing in enumerate(listings[:30], 1):
            row_bg = CARD if i % 2 == 0 else BG2
            price  = cents_to_usd(listing.get("price", 0))
            item   = listing.get("item", {})
            fval   = item.get("float_value", "N/A")
            fval_s = f"{fval:.6f}" if isinstance(fval, float) else str(fval)
            wear   = item.get("wear_name", "—")
            st     = "✓" if item.get("is_stattrak") else "—"

            is_min = listing.get("price") == stats["min"]
            price_fg = GREEN if is_min else TEXT

            row_data = [str(i), price, fval_s, wear, st]
            fgs      = [MUTED, price_fg, MUTED, TEXT, ACCENT2 if st == "✓" else MUTED]

            for col, (val, fg) in enumerate(zip(row_data, fgs)):
                tk.Label(table, text=val, font=FONT_SMALL,
                         bg=row_bg, fg=fg,
                         width=widths[col], anchor="w",
                         padx=8, pady=5
                         ).grid(row=i, column=col, sticky="ew", padx=(0, 1), pady=1)

        if len(listings) > 30:
            tk.Label(pad,
                     text=f"… et {len(listings)-30} autres listings (exporte en JSON pour voir tout)",
                     font=FONT_SMALL, bg=BG, fg=MUTED
                     ).pack(anchor="w", pady=(8, 0))

    # ── Export JSON ───────────────────────────────────────────────────────────

    def _export_json(self):
        if not self.listings_cache:
            messagebox.showinfo("Aucune donnée", "Lance d'abord une recherche.")
            return
        weapon = self.weapon_var.get().strip()
        wear   = self.wear_var.get()
        name   = f"{weapon} ({wear})".replace(" ", "_").replace("|", "").replace("/", "")
        path   = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=name,
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "query":    f"{weapon} ({wear})",
                "stats":    self.stats_cache,
                "listings": self.listings_cache,
            }, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exporté ✓", f"Fichier sauvegardé :\n{path}")


# ── Lancement ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = CSFloatApp()
    app.mainloop()
