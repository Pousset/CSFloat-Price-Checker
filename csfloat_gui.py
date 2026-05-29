"""
CSFloat Price Checker — Interface Graphique v2
==============================================
Navigation 3 étapes :
  1. Choisir une arme (grille visuelle)
  2. Choisir un skin (grille visuelle)
  3. Choisir la qualité → affichage des prix
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import statistics
import json
import os
import io
from PIL import Image, ImageTk
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE    = "https://csfloat.com/api/v1"
SKINS_API   = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"

WEAR_OPTIONS = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
FLOAT_RANGES = {
    "Factory New":    (0.00, 0.07),
    "Minimal Wear":   (0.07, 0.15),
    "Field-Tested":   (0.15, 0.38),
    "Well-Worn":      (0.38, 0.45),
    "Battle-Scarred": (0.45, 1.00),
}
CATEGORY_MAP = {"Tous": 0, "Normal": 1, "StatTrak™": 2, "Souvenir": 3}

# Ordre d'affichage des armes
WEAPON_ORDER = [
    "AK-47", "M4A4", "M4A1-S", "AWP", "Desert Eagle", "USP-S", "Glock-18",
    "P250", "Five-SeveN", "CZ75-Auto", "Tec-9", "MP9", "MP5-SD", "MAC-10",
    "UMP-45", "P90", "PP-Bizon", "Nova", "XM1014", "Sawed-Off", "MAG-7",
    "M249", "Negev", "SG 553", "AUG", "FAMAS", "Galil AR", "SSG 08",
    "G3SG1", "SCAR-20", "MP7", "P2000", "Dual Berettas", "R8 Revolver",
]

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0d0f14"
BG2     = "#13161e"
BG3     = "#1a1e29"
CARD    = "#1e2230"
CARD_H  = "#252a3a"
ACCENT  = "#e8a92a"
ACCENT2 = "#3d8ef0"
GREEN   = "#2ecc71"
RED     = "#e74c3c"
TEXT    = "#e8eaf0"
MUTED   = "#6b7280"
BORDER  = "#2a2f3d"

FONT_TITLE = ("Consolas", 18, "bold")
FONT_HEAD  = ("Consolas", 11, "bold")
FONT_BODY  = ("Consolas", 10)
FONT_SMALL = ("Consolas", 9)
FONT_STAT  = ("Consolas", 20, "bold")

IMG_CACHE: dict[str, ImageTk.PhotoImage] = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def cents_to_usd(c) -> str:
    return f"${c / 100:.2f}"

def load_image(url: str, size=(80, 60)) -> ImageTk.PhotoImage | None:
    key = f"{url}_{size}"
    if key in IMG_CACHE:
        return IMG_CACHE[key]
    try:
        r = requests.get(url, timeout=8)
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        bg = Image.new("RGBA", size, (13, 15, 20, 0))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        bg.paste(img, offset, img)
        tk_img = ImageTk.PhotoImage(bg)
        IMG_CACHE[key] = tk_img
        return tk_img
    except Exception:
        return None

def fetch_skins_db() -> list[dict]:
    r = requests.get(SKINS_API, timeout=20)
    r.raise_for_status()
    return r.json()

def fetch_listings(api_key, market_hash_name, min_float, max_float, category):
    headers = {"Authorization": api_key}
    params  = {
        "market_hash_name": market_hash_name,
        "limit": 50,
        "sort_by": "lowest_price",
        "type": "buy_now",
        "category": category,
        "min_float": min_float,
        "max_float": max_float,
    }
    resp = requests.get(f"{API_BASE}/listings", headers=headers,
                        params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", [])

def analyze_prices(listings):
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

# ── Widgets ───────────────────────────────────────────────────────────────────

class ScrollFrame(tk.Frame):
    """Frame scrollable réutilisable."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.canvas = tk.Canvas(self, bg=BG, bd=0, highlightthickness=0)
        self.vsb    = tk.Scrollbar(self, orient="vertical",
                                   command=self.canvas.yview,
                                   bg=BG2, troughcolor=BG2)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win  = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(
                                 -1*(e.delta//120), "units"))

class SkinCard(tk.Frame):
    """Carte cliquable affichant image + nom."""
    def __init__(self, parent, name, img_url, callback,
                 card_w=120, card_h=110, img_size=(90, 68), **kw):
        super().__init__(parent, bg=CARD, width=card_w, height=card_h,
                         cursor="hand2", **kw)
        self.pack_propagate(False)
        self._cb   = callback
        self._url  = img_url
        self._size = img_size
        self._img_lbl = tk.Label(self, bg=CARD, text="…", fg=MUTED,
                                 font=FONT_SMALL)
        self._img_lbl.pack(expand=True)
        label_text = name if len(name) <= 18 else name[:16] + "…"
        self._name = tk.Label(self, text=label_text, bg=CARD, fg=TEXT,
                              font=FONT_SMALL, wraplength=card_w - 8)
        self._name.pack(pady=(0, 4))
        for w in (self, self._img_lbl, self._name):
            w.bind("<Button-1>", lambda e: self._cb())
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

    def _hover(self, on):
        c = CARD_H if on else CARD
        for w in (self, self._img_lbl, self._name):
            w.config(bg=c)

    def set_image(self, tk_img):
        if tk_img:
            self._img_lbl.config(image=tk_img, text="", bg=CARD)
            self._img_lbl.image = tk_img
        else:
            self._img_lbl.config(text="?", fg=MUTED)

# ── Application principale ────────────────────────────────────────────────────

class CSFloatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSFloat Price Checker")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.api_key    = tk.StringVar(value=os.getenv("CSFLOAT_API_KEY", ""))
        self.skins_db: list[dict] = []
        self.weapons_map: dict[str, list[dict]] = {}
        self.sel_weapon  = ""
        self.sel_skin    = {}
        self.listings_cache: list[dict] = []
        self.stats_cache: dict = {}

        self._build_ui()
        self._load_skins_db()

    # ── UI Globale ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ─────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        hdr_inner = tk.Frame(hdr, bg=BG2, padx=16, pady=12)
        hdr_inner.pack(side="left", fill="both", expand=True)
        tk.Label(hdr_inner, text="◈  CSFLOAT PRICE CHECKER",
                 font=FONT_TITLE, bg=BG2, fg=ACCENT).pack(side="left")
        tk.Label(hdr_inner, text="v2.0", font=FONT_SMALL,
                 bg=BG2, fg=MUTED).pack(side="left", padx=8, pady=(6, 0))

        # Statut API
        self.status_dot = tk.Label(hdr_inner, text="●", font=("Consolas", 13),
                                   bg=BG2, fg=MUTED)
        self.status_dot.pack(side="right", padx=(0, 4))
        self.status_lbl = tk.Label(hdr_inner, text="Clé non validée",
                                   font=FONT_SMALL, bg=BG2, fg=MUTED)
        self.status_lbl.pack(side="right")

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Barre API ───────────────────────────────────────────────────────
        api_bar = tk.Frame(self, bg=BG3, padx=16, pady=8)
        api_bar.pack(fill="x")
        tk.Label(api_bar, text="CLÉ API :", font=FONT_SMALL,
                 bg=BG3, fg=MUTED).pack(side="left")
        self.api_entry = tk.Entry(api_bar, textvariable=self.api_key,
                                  bg=BG, fg=TEXT, insertbackground=ACCENT,
                                  font=FONT_SMALL, bd=0, show="•", width=45,
                                  highlightthickness=1,
                                  highlightbackground=BORDER)
        self.api_entry.pack(side="left", padx=8, ipady=4)
        eye_btn = tk.Label(api_bar, text="👁", bg=BG3, fg=MUTED,
                           cursor="hand2", font=("Consolas", 11))
        eye_btn.pack(side="left")
        eye_btn.bind("<Button-1>", self._toggle_key)
        self._key_visible = False

        val_btn = tk.Label(api_bar, text="  Valider  ", bg=ACCENT, fg=BG,
                           font=FONT_SMALL, cursor="hand2", padx=6, pady=4)
        val_btn.pack(side="left", padx=8)
        val_btn.bind("<Button-1>", lambda e: self._validate_key())

        # ── Breadcrumb ──────────────────────────────────────────────────────
        self.breadcrumb_bar = tk.Frame(self, bg=BG2, padx=16, pady=6)
        self.breadcrumb_bar.pack(fill="x")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        self._update_breadcrumb()

        # ── Zone principale (swappable) ─────────────────────────────────────
        self.main_area = tk.Frame(self, bg=BG)
        self.main_area.pack(fill="both", expand=True)

    def _swap(self, widget):
        """Remplace le contenu de main_area."""
        for w in self.main_area.winfo_children():
            if w is not widget:
                w.destroy()
        widget.pack(fill="both", expand=True)

    # ── Breadcrumb ────────────────────────────────────────────────────────────

    def _update_breadcrumb(self, weapon="", skin_name=""):
        for w in self.breadcrumb_bar.winfo_children():
            w.destroy()

        def crumb(text, cmd=None, active=False):
            fg = ACCENT if active else (ACCENT2 if cmd else MUTED)
            lbl = tk.Label(self.breadcrumb_bar, text=text, font=FONT_SMALL,
                           bg=BG2, fg=fg,
                           cursor="hand2" if cmd else "arrow")
            lbl.pack(side="left")
            if cmd:
                lbl.bind("<Button-1>", lambda e: cmd())

        crumb("Armes", self._show_weapons if weapon else None,
              active=not weapon)
        if weapon:
            crumb("  ›  ", active=False)
            crumb(weapon, self._show_skins if skin_name else None,
                  active=not skin_name)
        if skin_name:
            crumb("  ›  ", active=False)
            crumb(skin_name, active=True)

    # ── Clé API ───────────────────────────────────────────────────────────────

    def _toggle_key(self, _=None):
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
                self._set_status("Clé invalide ✗", RED)
            elif r.status_code in (200, 400):
                self._set_status("Clé valide ✓", GREEN)
                os.environ["CSFLOAT_API_KEY"] = key
            else:
                self._set_status(f"Erreur {r.status_code}", RED)
        except Exception:
            self._set_status("Réseau KO", RED)

    def _set_status(self, text, color):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    # ── Chargement DB skins ───────────────────────────────────────────────────

    def _load_skins_db(self):
        frame = tk.Frame(self.main_area, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="⟳  Chargement des skins…",
                 font=("Consolas", 14), bg=BG, fg=MUTED).place(relx=0.5,
                 rely=0.5, anchor="center")
        threading.Thread(target=self._fetch_db_thread, daemon=True).start()

    def _fetch_db_thread(self):
        try:
            data = fetch_skins_db()
            self.after(0, self._on_db_loaded, data)
        except Exception as e:
            self.after(0, self._on_db_error, str(e))

    def _on_db_loaded(self, data):
        # Regrouper par arme, exclure couteaux/gants/agents
        excluded = {"Knife", "Gloves", "Agent", "Charm", "Sticker",
                    "Graffiti", "Music Kit", "Patch", "Container", "Key", "Pass"}
        grouped: dict[str, list] = {}
        for skin in data:
            name  = skin.get("name", "")
            parts = name.split(" | ")
            if len(parts) < 2:
                continue
            weapon = parts[0].strip()
            # Filtre couteaux/gants via catégorie ou nom
            cat = skin.get("category", {})
            if isinstance(cat, dict) and cat.get("name", "") in excluded:
                continue
            if any(x in weapon for x in ("Knife","Bayonet","Karambit",
                                          "Butterfly","Bowie","Falchion",
                                          "Flip","Gut","Huntsman","M9",
                                          "Navaja","Shadow","Stiletto",
                                          "Talon","Ursus","Classic","Nomad",
                                          "Paracord","Skeleton","Survival",
                                          "Gloves","Hand Wraps","Hydra",
                                          "Bloodhound","Driver","Moto",
                                          "Specialist","Sport","★")):
                continue
            grouped.setdefault(weapon, []).append(skin)

        self.skins_db    = data
        self.weapons_map = grouped
        self._show_weapons()

    def _on_db_error(self, msg):
        for w in self.main_area.winfo_children():
            w.destroy()
        tk.Label(self.main_area,
                 text=f"Erreur chargement skins :\n{msg}",
                 font=FONT_BODY, bg=BG, fg=RED).place(relx=0.5, rely=0.5,
                 anchor="center")

    # ── Écran 1 : Grille des armes ────────────────────────────────────────────

    def _show_weapons(self):
        self.sel_weapon = ""
        self._update_breadcrumb()
        sf = ScrollFrame(self.main_area)
        self._swap(sf)

        tk.Label(sf.inner, text="Choisis une arme",
                 font=FONT_HEAD, bg=BG, fg=MUTED,
                 padx=20, pady=14).pack(anchor="w")

        # Filtre recherche
        search_bar = tk.Frame(sf.inner, bg=BG, padx=20)
        search_bar.pack(fill="x", pady=(0, 10))
        self._weapon_search = tk.StringVar()
        tk.Entry(search_bar, textvariable=self._weapon_search,
                 bg=BG3, fg=TEXT, insertbackground=ACCENT,
                 font=FONT_BODY, bd=0, width=30,
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", ipady=5, padx=(0, 8))
        tk.Label(search_bar, text="🔍", bg=BG, fg=MUTED,
                 font=("Consolas", 11)).pack(side="left")

        self._weapons_grid_frame = tk.Frame(sf.inner, bg=BG, padx=20)
        self._weapons_grid_frame.pack(fill="both")

        self._weapon_search.trace_add("write",
                lambda *_: self._refresh_weapons_grid())
        self._refresh_weapons_grid()

    def _refresh_weapons_grid(self):
        for w in self._weapons_grid_frame.winfo_children():
            w.destroy()

        q = self._weapon_search.get().lower()
        # Trier : ordre prédéfini d'abord, puis alphabétique
        known = [w for w in WEAPON_ORDER if w in self.weapons_map]
        others = sorted(k for k in self.weapons_map if k not in WEAPON_ORDER)
        all_weapons = known + others
        if q:
            all_weapons = [w for w in all_weapons if q in w.lower()]

        cols = 7
        for i, weapon in enumerate(all_weapons):
            skins = self.weapons_map[weapon]
            # Image du premier skin
            img_url = skins[0].get("image", "") if skins else ""
            row, col = divmod(i, cols)

            card = SkinCard(
                self._weapons_grid_frame,
                name=weapon,
                img_url=img_url,
                callback=lambda w=weapon: self._select_weapon(w),
                card_w=130, card_h=115, img_size=(100, 75)
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # Charger l'image en arrière-plan
            def _load(url=img_url, c=card):
                img = load_image(url, (100, 75))
                self.after(0, c.set_image, img)
            threading.Thread(target=_load, daemon=True).start()

        if not all_weapons:
            tk.Label(self._weapons_grid_frame, text="Aucune arme trouvée",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _select_weapon(self, weapon: str):
        self.sel_weapon = weapon
        self._show_skins()

    # ── Écran 2 : Grille des skins ────────────────────────────────────────────

    def _show_skins(self):
        self._update_breadcrumb(weapon=self.sel_weapon)
        sf = ScrollFrame(self.main_area)
        self._swap(sf)

        tk.Label(sf.inner,
                 text=f"Skins — {self.sel_weapon}",
                 font=FONT_HEAD, bg=BG, fg=MUTED,
                 padx=20, pady=14).pack(anchor="w")

        skins = self.weapons_map.get(self.sel_weapon, [])

        # Filtre
        search_bar = tk.Frame(sf.inner, bg=BG, padx=20)
        search_bar.pack(fill="x", pady=(0, 10))
        self._skin_search = tk.StringVar()
        tk.Entry(search_bar, textvariable=self._skin_search,
                 bg=BG3, fg=TEXT, insertbackground=ACCENT,
                 font=FONT_BODY, bd=0, width=30,
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", ipady=5, padx=(0, 8))
        tk.Label(search_bar, text="🔍", bg=BG, fg=MUTED,
                 font=("Consolas", 11)).pack(side="left")

        self._skins_grid_frame = tk.Frame(sf.inner, bg=BG, padx=20)
        self._skins_grid_frame.pack(fill="both")
        self._all_skins = skins

        self._skin_search.trace_add("write",
                lambda *_: self._refresh_skins_grid())
        self._refresh_skins_grid()

    def _refresh_skins_grid(self):
        for w in self._skins_grid_frame.winfo_children():
            w.destroy()

        q = self._skin_search.get().lower()
        skins = [s for s in self._all_skins
                 if q in s.get("name", "").lower()] if q else self._all_skins

        cols = 6
        for i, skin in enumerate(skins):
            parts     = skin.get("name", "").split(" | ")
            skin_name = parts[1] if len(parts) > 1 else skin.get("name", "")
            img_url   = skin.get("image", "")
            row, col  = divmod(i, cols)

            card = SkinCard(
                self._skins_grid_frame,
                name=skin_name,
                img_url=img_url,
                callback=lambda s=skin: self._select_skin(s),
                card_w=148, card_h=120, img_size=(115, 80)
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            def _load(url=img_url, c=card):
                img = load_image(url, (115, 80))
                self.after(0, c.set_image, img)
            threading.Thread(target=_load, daemon=True).start()

        if not skins:
            tk.Label(self._skins_grid_frame, text="Aucun skin trouvé",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _select_skin(self, skin: dict):
        self.sel_skin = skin
        self._show_quality_picker()

    # ── Écran 3 : Qualité + Prix ──────────────────────────────────────────────

    def _show_quality_picker(self):
        skin      = self.sel_skin
        full_name = skin.get("name", "")
        parts     = full_name.split(" | ")
        skin_name = parts[1] if len(parts) > 1 else full_name
        self._update_breadcrumb(weapon=self.sel_weapon, skin_name=skin_name)

        # Qualités disponibles pour ce skin
        min_float = skin.get("min_float", 0.0)
        max_float = skin.get("max_float", 1.0)
        available_wears = []
        for wear, (lo, hi) in FLOAT_RANGES.items():
            if lo < max_float and hi > min_float:
                available_wears.append(wear)

        frame = tk.Frame(self.main_area, bg=BG)
        self._swap(frame)

        # ── Panneau gauche : skin info ──────────────────────────────────────
        left = tk.Frame(frame, bg=BG2, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Frame(frame, bg=BORDER, width=1).pack(side="left", fill="y")

        info = tk.Frame(left, bg=BG2, padx=20, pady=20)
        info.pack(fill="both", expand=True)

        # Image grande
        img_url = skin.get("image", "")
        self._skin_big_lbl = tk.Label(info, bg=BG2, text="…", fg=MUTED,
                                      font=("Consolas", 24))
        self._skin_big_lbl.pack(pady=(10, 8))

        def _load_big(url=img_url):
            img = load_image(url, (220, 160))
            self.after(0, lambda: self._skin_big_lbl.config(
                image=img, text="") if img else None)
            if img:
                self._skin_big_lbl.image = img
        threading.Thread(target=_load_big, daemon=True).start()

        tk.Label(info, text=self.sel_weapon, font=FONT_SMALL,
                 bg=BG2, fg=MUTED).pack()
        tk.Label(info, text=skin_name, font=("Consolas", 13, "bold"),
                 bg=BG2, fg=ACCENT, wraplength=240).pack(pady=(2, 12))

        # Rareté
        rarity = skin.get("rarity", {})
        if isinstance(rarity, dict):
            color = rarity.get("color", MUTED)
            name  = rarity.get("name", "")
            tk.Label(info, text=f"● {name}", font=FONT_SMALL,
                     bg=BG2, fg=color).pack()

        tk.Frame(info, bg=BORDER, height=1).pack(fill="x", pady=12)

        # Type
        tk.Label(info, text="TYPE", font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w")
        self.cat_var = tk.StringVar(value="Normal")
        cat_cb = ttk.Combobox(info, textvariable=self.cat_var,
                              values=list(CATEGORY_MAP.keys()),
                              state="readonly", font=FONT_SMALL, width=14)
        self._style_combobox()
        cat_cb.pack(fill="x", pady=(4, 16))

        tk.Frame(info, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

        # Qualités disponibles
        tk.Label(info, text="QUALITÉ — clique pour voir les prix",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w", pady=(0, 6))
        for wear in available_wears:
            btn = tk.Label(info, text=wear, font=FONT_SMALL,
                           bg=BG3, fg=TEXT, pady=7, padx=10,
                           cursor="hand2", anchor="w",
                           highlightbackground=BORDER, highlightthickness=1)
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-1>",
                     lambda e, w=wear, b=btn: self._start_price_search(w, b, available_wears))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=CARD_H))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG3))

        # ── Panneau droit : résultats ───────────────────────────────────────
        self.results_right = tk.Frame(frame, bg=BG)
        self.results_right.pack(side="left", fill="both", expand=True)

        self._show_results_placeholder()

    def _style_combobox(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TCombobox",
                    fieldbackground=BG3, background=BG3, foreground=TEXT,
                    arrowcolor=ACCENT, bordercolor=BORDER,
                    selectbackground=CARD, selectforeground=TEXT)
        s.map("TCombobox",
              fieldbackground=[("readonly", BG3)],
              foreground=[("readonly", TEXT)],
              background=[("readonly", BG3)])

    def _show_results_placeholder(self):
        for w in self.results_right.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_right, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="◈", font=("Consolas", 40), bg=BG, fg=BORDER).pack()
        tk.Label(f, text="Choisis une qualité\npour voir les prix",
                 font=FONT_BODY, bg=BG, fg=MUTED, justify="center").pack(pady=8)

    def _start_price_search(self, wear, btn_widget, all_btns_parent):
        key = self.api_key.get().strip()
        if not key:
            messagebox.showerror("Clé manquante", "Valide ta clé API d'abord.")
            return

        # Highlight bouton sélectionné
        for w in all_btns_parent:
            pass  # reset géré via hover

        full_name = self.sel_skin.get("name", "")
        market_hash_name = f"{full_name} ({wear})"
        min_f, max_f = FLOAT_RANGES[wear]
        cat = CATEGORY_MAP[self.cat_var.get()]

        self._show_loading_results(market_hash_name)
        threading.Thread(
            target=self._fetch_price_thread,
            args=(key, market_hash_name, min_f, max_f, cat),
            daemon=True
        ).start()

    def _fetch_price_thread(self, key, market_hash_name, min_f, max_f, cat):
        try:
            listings = fetch_listings(key, market_hash_name, min_f, max_f, cat)
            stats    = analyze_prices(listings)
            self.listings_cache = listings
            self.stats_cache    = stats
            self.after(0, self._show_price_results, market_hash_name, listings, stats)
        except requests.HTTPError as e:
            code = e.response.status_code
            msg  = "Clé API invalide." if code == 401 else \
                   "Rate limit atteint." if code == 429 else f"HTTP {code}"
            self.after(0, self._show_error_results, msg)
        except Exception as e:
            self.after(0, self._show_error_results, str(e))

    def _show_loading_results(self, name):
        for w in self.results_right.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_right, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="⟳", font=("Consolas", 32), bg=BG, fg=ACCENT).pack()
        tk.Label(f, text=f"Chargement…\n{name}",
                 font=FONT_BODY, bg=BG, fg=MUTED, justify="center").pack(pady=8)

    def _show_error_results(self, msg):
        for w in self.results_right.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_right, bg=BG)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="✕", font=("Consolas", 32), bg=BG, fg=RED).pack()
        tk.Label(f, text=msg, font=FONT_BODY, bg=BG,
                 fg=RED, wraplength=300, justify="center").pack(pady=8)

    def _show_price_results(self, name, listings, stats):
        for w in self.results_right.winfo_children():
            w.destroy()

        sf = ScrollFrame(self.results_right)
        sf.pack(fill="both", expand=True)
        pad = tk.Frame(sf.inner, bg=BG, padx=20, pady=16)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text=name, font=("Consolas", 12, "bold"),
                 bg=BG, fg=ACCENT, wraplength=500, justify="left").pack(anchor="w")
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(8, 14))

        if not stats:
            tk.Label(pad, text="Aucun listing trouvé.",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(anchor="w")
            return

        # ── Stat cards ──────────────────────────────────────────────────────
        cards_row = tk.Frame(pad, bg=BG)
        cards_row.pack(fill="x", pady=(0, 14))

        for i, (label, value, color) in enumerate([
            ("MINIMUM",  cents_to_usd(stats["min"]),          GREEN),
            ("MOYENNE",  cents_to_usd(int(stats["mean"])),    ACCENT),
            ("MÉDIANE",  cents_to_usd(int(stats["median"])), ACCENT2),
            ("MAXIMUM",  cents_to_usd(stats["max"]),          RED),
        ]):
            c = tk.Frame(cards_row, bg=CARD,
                         highlightbackground=BORDER, highlightthickness=1)
            c.grid(row=0, column=i, padx=(0, 8) if i < 3 else 0, sticky="nsew")
            cards_row.columnconfigure(i, weight=1)
            tk.Label(c, text=label, font=FONT_SMALL, bg=CARD, fg=MUTED
                     ).pack(anchor="w", padx=10, pady=(8, 0))
            tk.Label(c, text=value, font=FONT_STAT, bg=CARD, fg=color
                     ).pack(anchor="w", padx=10)
            tk.Label(c, text=" ", bg=CARD).pack(pady=(0, 6))

        tk.Label(pad,
                 text=f"● {stats['count']} listings  ·  "
                      f"Écart-type : {cents_to_usd(int(stats.get('stdev', 0)))}",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 12))

        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

        # Export
        exp = tk.Label(pad, text="↓ Exporter JSON", font=FONT_SMALL,
                       bg=BG3, fg=TEXT, padx=10, pady=5, cursor="hand2")
        exp.pack(anchor="w", pady=(0, 12))
        exp.bind("<Button-1>", lambda e: self._export_json())
        exp.bind("<Enter>", lambda e: exp.config(bg=BORDER))
        exp.bind("<Leave>", lambda e: exp.config(bg=BG3))

        tk.Label(pad, text="LISTINGS (triés par prix)",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 6))

        # Table
        table = tk.Frame(pad, bg=BG)
        table.pack(fill="x")
        headers = ["#", "Prix", "Float", "Wear", "ST"]
        widths   = [3,    10,    12,      14,     4]
        for col, (h, w_) in enumerate(zip(headers, widths)):
            tk.Label(table, text=h, font=FONT_SMALL, bg=BG3, fg=MUTED,
                     width=w_, anchor="w", padx=8, pady=4
                     ).grid(row=0, column=col, sticky="ew", padx=(0, 1))

        for i, listing in enumerate(listings[:30], 1):
            rb     = CARD if i % 2 == 0 else BG2
            price  = cents_to_usd(listing.get("price", 0))
            item   = listing.get("item", {})
            fval   = item.get("float_value", "N/A")
            fval_s = f"{fval:.6f}" if isinstance(fval, float) else str(fval)
            wear   = item.get("wear_name", "—")
            st     = "✓" if item.get("is_stattrak") else "—"
            pfg    = GREEN if listing.get("price") == stats["min"] else TEXT

            for col, (val, fg) in enumerate(zip(
                [str(i), price, fval_s, wear, st],
                [MUTED,  pfg,   MUTED,  TEXT, ACCENT2 if st == "✓" else MUTED]
            )):
                tk.Label(table, text=val, font=FONT_SMALL,
                         bg=rb, fg=fg, width=widths[col],
                         anchor="w", padx=8, pady=5
                         ).grid(row=i, column=col, sticky="ew",
                                padx=(0, 1), pady=1)

    def _export_json(self):
        if not self.listings_cache:
            messagebox.showinfo("Aucune donnée", "Lance une recherche d'abord.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"stats": self.stats_cache,
                       "listings": self.listings_cache}, f,
                      indent=2, ensure_ascii=False)
        messagebox.showinfo("Exporté ✓", f"Sauvegardé :\n{path}")


# ── Lancement ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = CSFloatApp()
    app.mainloop()
