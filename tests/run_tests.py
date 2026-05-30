"""
Script de lancement des tests avec résumé personnalisé.
"""

import unittest
import time
import sys
import os

# Dossiers nécessaires : racine du projet et dossier App
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "App"))

VERT  = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
GRAS  = "\033[1m"
RESET = "\033[0m"

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.discover(start_dir=os.path.dirname(os.path.abspath(__file__)), pattern="test_*.py")

    print(f"\n{'═' * 55}")
    print(f"  {GRAS}CSFloat Price Checker — Tests{RESET}")
    print(f"{'═' * 55}\n")

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)

    debut = time.perf_counter()
    result = runner.run(suite)
    duree = time.perf_counter() - debut

    total   = result.testsRun
    echecs  = len(result.failures) + len(result.errors)
    reussis = total - echecs

    print(f"\n{'═' * 55}")
    print(f"  {GRAS}Ran {total} tests in {duree:.3f}s{RESET}")

    if echecs == 0:
        print(f"  {VERT}{GRAS}{reussis} sur {total} tests réussis ✓{RESET}")
    else:
        print(f"  {ROUGE}{GRAS}{reussis} sur {total} tests réussis "
              f"({echecs} échoué{'s' if echecs > 1 else ''}) ✗{RESET}")

    print(f"{'═' * 55}\n")

    sys.exit(0 if echecs == 0 else 1)
