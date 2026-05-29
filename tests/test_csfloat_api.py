"""
Tests pour l'API CSFloat
========================
Teste les fonctions fetch_listings et analyze_prices
sans effectuer de vraies requêtes réseau (mocks).
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ajouter le dossier App au path pour importer le module principal
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "App"))

from csfloat_price_checker import fetch_listings, analyze_prices, cents_to_usd


class TestCentsToUsd(unittest.TestCase):
    """Tests de la conversion centimes → dollars."""

    def test_conversion_basique(self):
        self.assertEqual(cents_to_usd(1000), "$10.00")

    def test_conversion_zero(self):
        self.assertEqual(cents_to_usd(0), "$0.00")

    def test_conversion_arrondi(self):
        self.assertEqual(cents_to_usd(150), "$1.50")

    def test_conversion_grand_montant(self):
        self.assertEqual(cents_to_usd(99999), "$999.99")


class TestAnalyzePrices(unittest.TestCase):
    """Tests du calcul de statistiques sur les listings."""

    def test_listings_vides(self):
        result = analyze_prices([])
        self.assertEqual(result, {})

    def test_listing_sans_prix(self):
        listings = [{"item": {"float_value": 0.1}}, {"item": {"float_value": 0.2}}]
        result = analyze_prices(listings)
        self.assertEqual(result, {})

    def test_un_seul_listing(self):
        listings = [{"price": 5000}]
        result = analyze_prices(listings)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["min"], 5000)
        self.assertEqual(result["max"], 5000)
        self.assertEqual(result["mean"], 5000)
        self.assertEqual(result["median"], 5000)
        self.assertEqual(result["stdev"], 0)

    def test_plusieurs_listings(self):
        listings = [
            {"price": 1000},
            {"price": 2000},
            {"price": 3000},
        ]
        result = analyze_prices(listings)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["min"], 1000)
        self.assertEqual(result["max"], 3000)
        self.assertEqual(result["mean"], 2000)
        self.assertEqual(result["median"], 2000)
        self.assertGreater(result["stdev"], 0)

    def test_ignore_listings_sans_prix(self):
        listings = [
            {"price": 1000},
            {"item": {"float_value": 0.5}},  # pas de "price"
            {"price": 3000},
        ]
        result = analyze_prices(listings)
        self.assertEqual(result["count"], 2)


class TestFetchListings(unittest.TestCase):
    """Tests de la récupération des listings CSFloat."""

    def _make_mock_response(self, json_data, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("csfloat_price_checker.requests.get")
    def test_retourne_liste_directe(self, mock_get):
        """L'API peut retourner directement une liste."""
        fake_listings = [
            {"price": 1500, "item": {"float_value": 0.05}},
            {"price": 2000, "item": {"float_value": 0.06}},
        ]
        mock_get.return_value = self._make_mock_response(fake_listings)

        result = fetch_listings("AK-47 | Redline (Field-Tested)")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["price"], 1500)

    @patch("csfloat_price_checker.requests.get")
    def test_retourne_dict_avec_data(self, mock_get):
        """L'API peut retourner un dict avec une clé 'data'."""
        fake_listings = [{"price": 5000, "item": {"float_value": 0.20}}]
        mock_get.return_value = self._make_mock_response({"data": fake_listings})

        result = fetch_listings("AWP | Dragon Lore (Field-Tested)")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], 5000)

    @patch("csfloat_price_checker.requests.get")
    def test_dict_sans_data_retourne_liste_vide(self, mock_get):
        """Un dict sans clé 'data' renvoie une liste vide."""
        mock_get.return_value = self._make_mock_response({"error": "not found"})

        result = fetch_listings("Skin Inexistant")

        self.assertEqual(result, [])

    @patch("csfloat_price_checker.requests.get")
    def test_parametres_envoyes(self, mock_get):
        """Vérifie que les bons paramètres sont transmis à l'API."""
        mock_get.return_value = self._make_mock_response([])

        fetch_listings(
            market_hash_name="M4A4 | Howl (Factory New)",
            limit=10,
            min_float=0.00,
            max_float=0.07,
            category=2,
        )

        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertEqual(params["market_hash_name"], "M4A4 | Howl (Factory New)")
        self.assertEqual(params["limit"], 10)
        self.assertEqual(params["min_float"], 0.00)
        self.assertEqual(params["max_float"], 0.07)
        self.assertEqual(params["category"], 2)
        self.assertEqual(params["sort_by"], "lowest_price")
        self.assertEqual(params["type"], "buy_now")

    @patch("csfloat_price_checker.requests.get")
    def test_float_optionnels_absents(self, mock_get):
        """Sans min/max float, ces paramètres ne sont pas envoyés."""
        mock_get.return_value = self._make_mock_response([])

        fetch_listings("AK-47 | Redline (Field-Tested)")

        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertNotIn("min_float", params)
        self.assertNotIn("max_float", params)

    @patch("csfloat_price_checker.requests.get")
    def test_erreur_http_propagee(self, mock_get):
        """Une erreur HTTP doit être propagée (raise_for_status)."""
        mock_resp = self._make_mock_response({}, status_code=401)
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_get.return_value = mock_resp

        with self.assertRaises(Exception):
            fetch_listings("AK-47 | Redline (Field-Tested)")

    @patch("csfloat_price_checker.requests.get")
    def test_cle_api_dans_header(self, mock_get):
        """La clé API doit être passée dans le header Authorization."""
        mock_get.return_value = self._make_mock_response([])

        import csfloat_price_checker
        original_key = csfloat_price_checker.API_KEY
        csfloat_price_checker.API_KEY = "ma_cle_test"

        try:
            fetch_listings("AK-47 | Redline (Field-Tested)")
            _, kwargs = mock_get.call_args
            self.assertEqual(kwargs["headers"]["Authorization"], "ma_cle_test")
        finally:
            csfloat_price_checker.API_KEY = original_key


if __name__ == "__main__":
    unittest.main(verbosity=2)
