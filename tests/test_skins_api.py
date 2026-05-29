"""
Tests pour l'API Skins (ByMykel CSGO-API)
==========================================
Teste la récupération et le traitement des données de skins
sans effectuer de vraies requêtes réseau (mocks).
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ajouter le dossier parent au path pour importer le module GUI
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On importe uniquement fetch_skins_db depuis le GUI
from csfloat_gui import fetch_skins_db, SKINS_API


# ── Données fictives représentant la structure réelle de l'API ─────────────────
FAKE_SKINS = [
    {
        "id": "skin-ak47-redline",
        "name": "AK-47 | Redline",
        "description": "Field-Tested AK-47",
        "weapon": {"id": "weapon_ak47", "name": "AK-47"},
        "category": {"id": "normal", "name": "Normal"},
        "image": "https://example.com/ak47_redline.png",
        "min_float": 0.10,
        "max_float": 0.70,
        "rarity": {"id": "ancient", "name": "Classified", "color": "#eb4b4b"},
        "stattrak": True,
        "souvenir": False,
    },
    {
        "id": "skin-awp-dragon-lore",
        "name": "AWP | Dragon Lore",
        "description": "Factory New AWP",
        "weapon": {"id": "weapon_awp", "name": "AWP"},
        "category": {"id": "normal", "name": "Normal"},
        "image": "https://example.com/awp_dragonlore.png",
        "min_float": 0.01,
        "max_float": 0.08,
        "rarity": {"id": "ancient", "name": "Covert", "color": "#eb4b4b"},
        "stattrak": False,
        "souvenir": True,
    },
    {
        "id": "skin-m4a4-howl",
        "name": "M4A4 | Howl",
        "description": "Contraband M4A4",
        "weapon": {"id": "weapon_m4a4", "name": "M4A4"},
        "category": {"id": "normal", "name": "Normal"},
        "image": "https://example.com/m4a4_howl.png",
        "min_float": 0.00,
        "max_float": 0.40,
        "rarity": {"id": "contraband", "name": "Contraband", "color": "#e4ae39"},
        "stattrak": False,
        "souvenir": False,
    },
]


class TestFetchSkinsDb(unittest.TestCase):
    """Tests de la récupération de la base de skins."""

    def _make_mock_response(self, json_data, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("csfloat_gui.requests.get")
    def test_retourne_liste_de_skins(self, mock_get):
        """fetch_skins_db doit retourner la liste complète des skins."""
        mock_get.return_value = self._make_mock_response(FAKE_SKINS)

        result = fetch_skins_db()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

    @patch("csfloat_gui.requests.get")
    def test_appel_url_correcte(self, mock_get):
        """L'URL de l'API skins doit être celle définie dans la config."""
        mock_get.return_value = self._make_mock_response(FAKE_SKINS)

        fetch_skins_db()

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], SKINS_API)

    @patch("csfloat_gui.requests.get")
    def test_timeout_present(self, mock_get):
        """Un timeout doit être défini pour l'appel réseau."""
        mock_get.return_value = self._make_mock_response(FAKE_SKINS)

        fetch_skins_db()

        _, kwargs = mock_get.call_args
        self.assertIn("timeout", kwargs)
        self.assertGreater(kwargs["timeout"], 0)

    @patch("csfloat_gui.requests.get")
    def test_structure_skin(self, mock_get):
        """Chaque skin doit contenir les champs attendus."""
        mock_get.return_value = self._make_mock_response(FAKE_SKINS)

        result = fetch_skins_db()

        for skin in result:
            self.assertIn("name", skin)
            self.assertIn("weapon", skin)
            self.assertIn("image", skin)

    @patch("csfloat_gui.requests.get")
    def test_skin_champs_arme(self, mock_get):
        """Le champ 'weapon' doit contenir id et name."""
        mock_get.return_value = self._make_mock_response(FAKE_SKINS)

        result = fetch_skins_db()

        ak47 = next(s for s in result if "AK-47" in s["name"])
        self.assertEqual(ak47["weapon"]["name"], "AK-47")
        self.assertIn("id", ak47["weapon"])

    @patch("csfloat_gui.requests.get")
    def test_erreur_http_propagee(self, mock_get):
        """Une erreur HTTP doit être propagée."""
        mock_resp = self._make_mock_response({}, status_code=503)
        mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")
        mock_get.return_value = mock_resp

        with self.assertRaises(Exception):
            fetch_skins_db()

    @patch("csfloat_gui.requests.get")
    def test_liste_vide(self, mock_get):
        """Une réponse vide est gérée sans erreur."""
        mock_get.return_value = self._make_mock_response([])

        result = fetch_skins_db()

        self.assertEqual(result, [])


class TestSkinsApiRegroupementParArme(unittest.TestCase):
    """
    Tests du regroupement des skins par arme,
    comme le fait l'application dans _load_skins_db.
    """

    def _group_by_weapon(self, skins: list[dict]) -> dict[str, list[dict]]:
        """Reproduit la logique de regroupement de l'application."""
        weapons_map: dict[str, list[dict]] = {}
        for skin in skins:
            weapon_name = skin.get("weapon", {}).get("name", "")
            if not weapon_name:
                continue
            weapons_map.setdefault(weapon_name, []).append(skin)
        return weapons_map

    def test_regroupement_correct(self):
        weapons_map = self._group_by_weapon(FAKE_SKINS)

        self.assertIn("AK-47", weapons_map)
        self.assertIn("AWP", weapons_map)
        self.assertIn("M4A4", weapons_map)

    def test_un_skin_par_arme(self):
        weapons_map = self._group_by_weapon(FAKE_SKINS)

        self.assertEqual(len(weapons_map["AK-47"]), 1)
        self.assertEqual(len(weapons_map["AWP"]), 1)

    def test_skin_sans_arme_ignore(self):
        skins_avec_vide = FAKE_SKINS + [{"name": "Gloves | Test", "image": ""}]
        weapons_map = self._group_by_weapon(skins_avec_vide)

        # Le skin sans arme ne doit pas créer de clé vide
        self.assertNotIn("", weapons_map)

    def test_plusieurs_skins_meme_arme(self):
        skins = FAKE_SKINS + [
            {
                "id": "skin-ak47-asiimov",
                "name": "AK-47 | Asiimov",
                "weapon": {"id": "weapon_ak47", "name": "AK-47"},
                "image": "https://example.com/ak47_asiimov.png",
            }
        ]
        weapons_map = self._group_by_weapon(skins)

        self.assertEqual(len(weapons_map["AK-47"]), 2)
        noms = [s["name"] for s in weapons_map["AK-47"]]
        self.assertIn("AK-47 | Redline", noms)
        self.assertIn("AK-47 | Asiimov", noms)


if __name__ == "__main__":
    unittest.main(verbosity=2)
