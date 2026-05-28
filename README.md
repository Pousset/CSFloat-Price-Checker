# 🎯 CSFloat Price Checker

Un outil Python interactif pour récupérer et analyser les prix des skins CS2 directement via l'**API officielle CSFloat**.

---

## 📋 Sommaire

- [🎯 CSFloat Price Checker](#-csfloat-price-checker)
  - [📋 Sommaire](#-sommaire)
  - [✨ Fonctionnalités](#-fonctionnalités)
  - [🔧 Prérequis](#-prérequis)
  - [📦 Installation](#-installation)
  - [🔑 Configuration de la clé API](#-configuration-de-la-clé-api)
  - [🚀 Utilisation](#-utilisation)
  - [📊 Exemple de sortie](#-exemple-de-sortie)
  - [🗂 Structure des données](#-structure-des-données)
  - [⚠️ Limites de l'API](#️-limites-de-lapi)
  - [❓ FAQ](#-faq)
  - [📄 Licence](#-licence)

---

## ✨ Fonctionnalités

- **Recherche par arme & qualité** — saisir le nom du skin et choisir parmi les 5 niveaux d'usure
- **Filtre StatTrak / Souvenir / Normal** — cibler précisément la variante voulue
- **Statistiques de prix** — minimum, maximum, moyenne, médiane et écart-type
- **Top 5 des moins chers** — affichage du prix et du float value pour chaque listing
- **Export JSON** — sauvegarde des données brutes pour une utilisation ultérieure
- **Pas de scraping** — utilise uniquement l'API officielle CSFloat, stable et légale

---

## 🔧 Prérequis

- Python **3.10+**
- Un compte sur [csfloat.com](https://csfloat.com)
- Une clé API CSFloat (gratuite)

---

## 📦 Installation

```bash
# Cloner ou télécharger le projet
git clone https://github.com/ton-user/csfloat-price-checker.git
cd csfloat-price-checker

# Installer la dépendance
pip install requests
```

---

## 🔑 Configuration de la clé API

1. Connecte-toi sur [csfloat.com](https://csfloat.com)
2. Va dans **Profil → onglet "Developer"**
3. Génère une nouvelle clé API
4. Configure-la selon ta préférence :

**Option A — Variable d'environnement (recommandée)**

```bash
# Linux / macOS
export CSFLOAT_API_KEY=ta_cle_ici

# Windows (PowerShell)
$env:CSFLOAT_API_KEY="ta_cle_ici"
```

**Option B — Directement dans le fichier**

Ouvre `csfloat_price_checker.py` et remplace :

```python
API_KEY = os.getenv("CSFLOAT_API_KEY", "VOTRE_CLE_API_ICI")
```

par :

```python
API_KEY = "ta_cle_ici"
```

---

## 🚀 Utilisation

```bash
python csfloat_price_checker.py
```

Le script démarre un menu interactif :

```
╔══════════════════════════════════════════╗
║        CSFloat Price Checker  v1.0       ║
╚══════════════════════════════════════════╝

══════════════════════════════════════════════
Nom de l'arme  (ex: AK-47 | Redline) : AK-47 | Redline

Qualités disponibles :
  1. Factory New
  2. Minimal Wear
  3. Field-Tested
  4. Well-Worn
  5. Battle-Scarred
Choix (1-5) : 3

Type d'item :
  0. Tous
  1. Normal
  2. StatTrak
  3. Souvenir
Choix : 1

🔍 Recherche : AK-47 | Redline (Field-Tested) …
```

---

## 📊 Exemple de sortie

```
───────────────────────────────────────────────────────
  AK-47 | Redline (Field-Tested)
───────────────────────────────────────────────────────
  Listings analysés : 50
  Prix minimum      : $8.50
  Prix moyen        : $11.23
  Prix médian       : $10.80
  Prix maximum      : $18.00
  Écart-type        : $1.74

  ── Top 5 moins chers ──
  1. $8.50   (float: 0.3412)
  2. $8.75   (float: 0.3687)
  3. $9.00   (float: 0.2901)
  4. $9.20   (float: 0.3755)
  5. $9.50   (float: 0.1823)
───────────────────────────────────────────────────────

  Exporter les données en JSON ? (o/N) :
```

---

## 🗂 Structure des données

Lors de l'export JSON, le fichier généré contient :

```json
{
  "query": "AK-47 | Redline (Field-Tested)",
  "stats": {
    "count": 50,
    "min": 850,
    "max": 1800,
    "mean": 1123.4,
    "median": 1080.0,
    "stdev": 174.2
  },
  "listings": [
    {
      "id": "324288155723370196",
      "price": 850,
      "item": {
        "float_value": 0.3412,
        "wear_name": "Field-Tested",
        "market_hash_name": "AK-47 | Redline (Field-Tested)"
      }
    }
  ]
}
```

> ⚠️ **Les prix sont en centimes** dans l'API CSFloat. Diviser par 100 pour obtenir la valeur en dollars.

---

## ⚠️ Limites de l'API

| Limite               | Valeur                                 |
| -------------------- | -------------------------------------- |
| Listings par requête | 50 max                                 |
| Rate limit           | Quelques centaines de requêtes / heure |
| Authentification     | Clé API obligatoire                    |

En cas d'erreur `429 Too Many Requests`, attends quelques minutes avant de relancer.

---

## ❓ FAQ

**Le script retourne "Aucun listing trouvé"**
→ Vérifie l'orthographe du nom (respecte les majuscules et les `|`). Exemples valides :

- `AK-47 | Redline`
- `M4A4 | Poseidon`
- `AWP | Dragon Lore`

**Ma clé API ne fonctionne pas**
→ Assure-toi qu'elle est bien copiée sans espaces, et que l'onglet "Developer" de ton profil CSFloat est activé.

**Comment obtenir le nom exact d'un skin ?**
→ Recherche le skin sur [csfloat.com](https://csfloat.com) et copie le nom tel qu'affiché dans l'URL ou le titre de la page, **sans la partie qualité** (ex: sans `(Field-Tested)`).

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de distribution.
