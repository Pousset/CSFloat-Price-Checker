"""
CSFloat Price Checker
=====================
Récupère les prix des skins CS2 via l'API officielle CSFloat.

Usage:
    python csfloat_price_checker.py

Prérequis:
    pip install requests

Clé API:
    Créer un compte sur csfloat.com → Profil → onglet "Developer"
"""

import requests
import statistics
import json
import os
from typing import Optional
from dotenv import load_dotenv

# Charge les variables depuis le fichier .env s'il existe
load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE = "https://csfloat.com/api/v1"

API_KEY = os.getenv("CSFLOAT_API_KEY", "")

# Qualités disponibles (wear)
WEAR_OPTIONS = [
    "Factory New",
    "Minimal Wear",
    "Field-Tested",
    "Well-Worn",
    "Battle-Scarred",
]

# Plages de float par qualité
FLOAT_RANGES = {
    "Factory New":    (0.00, 0.07),
    "Minimal Wear":   (0.07, 0.15),
    "Field-Tested":   (0.15, 0.38),
    "Well-Worn":      (0.38, 0.45),
    "Battle-Scarred": (0.45, 1.00),
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def cents_to_usd(cents: int) -> str:
    """Convertit des centimes en dollars."""
    return f"${cents / 100:.2f}"


def fetch_listings(market_hash_name: str, limit: int = 50,
                   min_float: Optional[float] = None,
                   max_float: Optional[float] = None,
                   category: int = 0) -> list[dict]:
    """
    Récupère les listings actifs pour un item donné.

    Args:
        market_hash_name: ex. "AK-47 | Redline (Field-Tested)"
        limit: nombre de listings à récupérer (max 50 par appel)
        min_float / max_float: bornes de float optionnelles
        category: 0=tous, 1=normal, 2=stattrak, 3=souvenir

    Returns:
        Liste de listings (dicts)
    """
    headers = {"Authorization": API_KEY}
    params = {
        "market_hash_name": market_hash_name,
        "limit": limit,
        "sort_by": "lowest_price",
        "type": "buy_now",
        "category": category,
    }
    if min_float is not None:
        params["min_float"] = min_float
    if max_float is not None:
        params["max_float"] = max_float

    resp = requests.get(f"{API_BASE}/listings", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # L'API retourne soit une liste, soit un dict avec une clé "data"
    if isinstance(data, list):
        return data
    return data.get("data", [])


def analyze_prices(listings: list[dict]) -> dict:
    """Calcule les statistiques de prix à partir des listings."""
    prices = [l["price"] for l in listings if "price" in l]

    if not prices:
        return {}

    return {
        "count": len(prices),
        "min":    min(prices),
        "max":    max(prices),
        "mean":   statistics.mean(prices),
        "median": statistics.median(prices),
        "stdev":  statistics.stdev(prices) if len(prices) > 1 else 0,
    }


def print_results(market_hash_name: str, stats: dict, listings: list[dict],
                  show_top: int = 5) -> None:
    """Affiche les résultats de manière lisible."""
    sep = "─" * 55

    print(f"\n{sep}")
    print(f"  {market_hash_name}")
    print(sep)

    if not stats:
        print("  Aucun listing trouvé.")
        return

    print(f"  Listings analysés : {stats['count']}")
    print(f"  Prix minimum      : {cents_to_usd(stats['min'])}")
    print(f"  Prix moyen        : {cents_to_usd(int(stats['mean']))}")
    print(f"  Prix médian       : {cents_to_usd(int(stats['median']))}")
    print(f"  Prix maximum      : {cents_to_usd(stats['max'])}")
    if stats['stdev']:
        print(f"  Écart-type        : {cents_to_usd(int(stats['stdev']))}")

    print(f"\n  ── Top {show_top} moins chers ──")
    for i, listing in enumerate(listings[:show_top], 1):
        price  = cents_to_usd(listing["price"])
        fval   = listing.get("item", {}).get("float_value", "N/A")
        fval_s = f"{fval:.4f}" if isinstance(fval, float) else str(fval)
        print(f"  {i}. {price}  (float: {fval_s})")

    print(sep)


# ── Interface interactive ──────────────────────────────────────────────────────

def select_wear() -> str:
    """Menu de sélection de la qualité."""
    print("\nQualités disponibles :")
    for i, w in enumerate(WEAR_OPTIONS, 1):
        print(f"  {i}. {w}")
    while True:
        try:
            choice = int(input("Choix (1-5) : ").strip())
            if 1 <= choice <= 5:
                return WEAR_OPTIONS[choice - 1]
        except ValueError:
            pass
        print("  → Entrez un chiffre entre 1 et 5.")


def select_category() -> int:
    """Menu de sélection StatTrak / Souvenir / Normal."""
    cats = {1: "Normal", 2: "StatTrak", 3: "Souvenir", 0: "Tous"}
    print("\nType d'item :")
    for k, v in cats.items():
        print(f"  {k}. {v}")
    while True:
        try:
            choice = int(input("Choix : ").strip())
            if choice in cats:
                return choice
        except ValueError:
            pass
        print("  → Choix invalide.")


def main():
    print("╔══════════════════════════════════════════╗")
    print("║        CSFloat Price Checker  v1.0       ║")
    print("╚══════════════════════════════════════════╝")

    if not API_KEY:
        print("\n⚠️  Aucune clé API configurée.")
        print("   → Copie .env.example en .env et renseigne ta clé :")
        print("     CSFLOAT_API_KEY=ta_cle_ici\n")
        return

    while True:
        print("\n" + "═" * 46)
        weapon_name = input("Nom de l'arme  (ex: AK-47 | Redline) : ").strip()
        if not weapon_name:
            print("  Nom invalide.")
            continue

        wear = select_wear()
        category = select_category()

        # Construire le market_hash_name complet
        market_hash_name = f"{weapon_name} ({wear})"

        # Restreindre aussi le float pour plus de précision
        min_f, max_f = FLOAT_RANGES[wear]

        print(f"\n🔍 Recherche : {market_hash_name} …")
        try:
            listings = fetch_listings(
                market_hash_name,
                limit=50,
                min_float=min_f,
                max_float=max_f,
                category=category,
            )
            stats = analyze_prices(listings)
            print_results(market_hash_name, stats, listings)

            # Export JSON optionnel
            export = input("\n  Exporter les données en JSON ? (o/N) : ").strip().lower()
            if export == "o":
                filename = market_hash_name.replace(" ", "_").replace("|", "").replace("/", "") + ".json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump({"query": market_hash_name, "stats": stats,
                               "listings": listings}, f, indent=2, ensure_ascii=False)
                print(f"  ✅ Exporté → {filename}")

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                print("  ❌ Clé API invalide ou expirée.")
            elif e.response.status_code == 429:
                print("  ❌ Rate limit atteint. Attends quelques minutes.")
            else:
                print(f"  ❌ Erreur HTTP {e.response.status_code} : {e}")
        except requests.RequestException as e:
            print(f"  ❌ Erreur réseau : {e}")

        again = input("\n  Nouvelle recherche ? (O/n) : ").strip().lower()
        if again == "n":
            print("\n  À bientôt !")
            break


if __name__ == "__main__":
    main()
