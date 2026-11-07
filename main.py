#!/usr/bin/env python3
"""Point d'entrée principal de l'application desktop d'IA.

Devoir universitaire : ENSI - Module « IA et Machine Learning »
Assignment 1 : Systèmes experts et algorithmes de recherche.

Usage:
    python3 main.py
"""

import os
import sys

# Assurer que la racine du projet est dans sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main() -> None:
    try:
        from gui.app import App
    except ImportError as e:
        print(f"Erreur d'importation : {e}")
        print("Veuillez installer les dépendances avec : pip install -r requirements.txt")
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
