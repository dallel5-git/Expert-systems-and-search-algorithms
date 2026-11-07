#!/usr/bin/env bash
# Script de lancement automatique pour Linux et macOS
# Projet IA ENSI - Systèmes Experts & Algorithmes de Recherche

set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================================"
echo "  Projet IA ENSI - Systèmes Experts & Recherche"
echo "========================================================"

# 1. Vérification si un environnement virtuel existe déjà
if [ -f ".venv/bin/python" ]; then
    echo "[INFO] Environnement virtuel .venv détecté."
    exec .venv/bin/python main.py "$@"
elif [ -f "conda_env/bin/python" ]; then
    echo "[INFO] Environnement Conda conda_env détecté."
    exec conda_env/bin/python main.py "$@"
fi

# 2. Si aucun environnement n'existe, recherche de Python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=python
else
    echo "[ERREUR] Python 3.10+ n'est pas installé ou introuvable dans le PATH."
    exit 1
fi

echo "[INFO] Création de l'environnement virtuel .venv avec $PYTHON_CMD..."
if $PYTHON_CMD -m venv .venv; then
    echo "[INFO] Installation des dépendances depuis requirements.txt..."
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    echo "[INFO] Lancement de l'application..."
    exec .venv/bin/python main.py "$@"
else
    echo "[AVERTISSEMENT] Échec de création du venv (python3-venv manquant ?)."
    echo "[INFO] Tentative d'installation des dépendances utilisateur et lancement direct..."
    $PYTHON_CMD -m pip install -r requirements.txt || true
    exec $PYTHON_CMD main.py "$@"
fi
