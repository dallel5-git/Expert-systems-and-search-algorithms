"""Vue complète du Module 2 : Algorithmes de recherche dans les espaces d'états.

Fournit :
1. Construction interactive du graphe (sommets, arcs orientés pondérés, heuristiques h(n), coordonnées 2D, clic sur canevas).
2. Rendu graphique dynamique permanent avec Matplotlib (flèches, coûts, heuristiques, coloration par étape).
3. Sélection d'algorithme catégorisée (Non informée / Informée) avec paramètres conditionnels (limite DLS, limite max IDS, mémoire SMA*).
4. Contrôles temporels complets (Précédent, Suivant, Lecture automatique réglable, Tout exécuter, Réinitialiser).
5. Traçabilité détaillée des étapes (nœud courant, frontière avec g/h/f, visités, chemin final en surbrillance épaisse, coût, profondeur).
6. Panneau des propriétés théoriques du cours et vérificateur formel d'admissibilité / consistance de l'heuristique.
"""

from __future__ import annotations
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.search_algorithms import (
    ALGORITHM_PROPERTIES,
    Edge,
    Graph,
    SearchResult,
    SearchStep,
    run_search_algorithm,
    verify_admissibility,
    verify_consistency,
    compare_all_algorithms,
)
from gui.widgets import CardFrame, MessageDialog

DATA_DIR = Path(__file__).parent.parent / "data"


class AddNodeDialog(ctk.CTkToplevel):
    """Dialogue modal pour ajouter un nouveau sommet avec heuristique et coordonnées."""

    def __init__(
        self,
        parent,
        on_save: Callable[[str, Tuple[float, float], float], bool],
        default_pos: Tuple[float, float] = (5.0, 5.0),
    ):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Ajouter un sommet")
        self.geometry("400x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            self,
            text="Nouveau sommet",
            font=ctk.CTkFont(size=17, weight="bold"),
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=20, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Nom / Identifiant :").grid(row=0, column=0, padx=5, pady=6, sticky="w")
        self.entry_name = ctk.CTkEntry(form, placeholder_text="ex: S, A, B...")
        self.entry_name.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="Heuristique h(n) :").grid(row=1, column=0, padx=5, pady=6, sticky="w")
        self.entry_h = ctk.CTkEntry(form, placeholder_text="ex: 0.0, 5.0")
        self.entry_h.insert(0, "0.0")
        self.entry_h.grid(row=1, column=1, padx=5, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="Coordonnées (X, Y) :").grid(row=2, column=0, padx=5, pady=6, sticky="w")
        coord_frame = ctk.CTkFrame(form, fg_color="transparent")
        coord_frame.grid(row=2, column=1, padx=5, pady=6, sticky="ew")
        coord_frame.grid_columnconfigure((0, 1), weight=1)

        self.entry_x = ctk.CTkEntry(coord_frame, width=70)
        self.entry_x.insert(0, str(round(default_pos[0], 1)))
        self.entry_x.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.entry_y = ctk.CTkEntry(coord_frame, width=70)
        self.entry_y.insert(0, str(round(default_pos[1], 1)))
        self.entry_y.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self.lbl_error = ctk.CTkLabel(self, text="", text_color="#ef5350", font=ctk.CTkFont(size=12))
        self.lbl_error.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.grid(row=3, column=0, padx=20, pady=(10, 15), sticky="e")

        ctk.CTkButton(
            btn_box,
            text="Annuler",
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self.destroy,
            width=90,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_box,
            text="Ajouter",
            fg_color="#1f6aa5",
            command=self._submit,
            width=100,
        ).pack(side="left", padx=5)

    def _submit(self) -> None:
        name = self.entry_name.get().strip().upper()
        if not name:
            self.lbl_error.configure(text="Le nom du sommet est obligatoire.")
            return

        try:
            h_val = float(self.entry_h.get().strip())
            if h_val < 0:
                self.lbl_error.configure(text="L'heuristique doit être positive ou nulle (≥ 0).")
                return
        except ValueError:
            self.lbl_error.configure(text="L'heuristique doit être un nombre valide.")
            return

        try:
            x_val = float(self.entry_x.get().strip())
            y_val = float(self.entry_y.get().strip())
        except ValueError:
            self.lbl_error.configure(text="Les coordonnées X et Y doivent être des nombres.")
            return

        success = self.on_save(name, (x_val, y_val), h_val)
        if success:
            self.destroy()
        else:
            self.lbl_error.configure(text=f"Le sommet '{name}' existe déjà dans le graphe.")


class AddEdgeDialog(ctk.CTkToplevel):
    """Dialogue modal pour ajouter ou modifier un arc orienté avec son coût."""

    def __init__(
        self,
        parent,
        nodes: List[str],
        on_save: Callable[[str, str, float], bool],
    ):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Ajouter un arc orienté")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Nouvel arc orienté",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=20, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Sommet Départ (De) :").grid(row=0, column=0, padx=5, pady=8, sticky="w")
        self.combo_from = ctk.CTkComboBox(form, values=nodes)
        self.combo_from.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        ctk.CTkLabel(form, text="Sommet Arrivée (Vers) :").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        self.combo_to = ctk.CTkComboBox(form, values=nodes)
        if len(nodes) > 1:
            self.combo_to.set(nodes[1])
        self.combo_to.grid(row=1, column=1, padx=5, pady=8, sticky="ew")

        ctk.CTkLabel(form, text="Coût de l'arc (> 0) :").grid(row=2, column=0, padx=5, pady=8, sticky="w")
        self.entry_cost = ctk.CTkEntry(form, placeholder_text="ex: 5.0")
        self.entry_cost.insert(0, "1.0")
        self.entry_cost.grid(row=2, column=1, padx=5, pady=8, sticky="ew")

        self.lbl_error = ctk.CTkLabel(self, text="", text_color="#ef5350", font=ctk.CTkFont(size=12))
        self.lbl_error.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.grid(row=3, column=0, padx=20, pady=(10, 15), sticky="e")

        ctk.CTkButton(
            btn_box,
            text="Annuler",
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self.destroy,
            width=90,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_box,
            text="Enregistrer",
            fg_color="#1f6aa5",
            command=self._submit,
            width=100,
        ).pack(side="left", padx=5)

    def _submit(self) -> None:
        u = self.combo_from.get().strip()
        v = self.combo_to.get().strip()
        if not u or not v:
            self.lbl_error.configure(text="Veuillez sélectionner les deux sommets.")
            return

        try:
            cost = float(self.entry_cost.get().strip())
            if cost <= 0:
                self.lbl_error.configure(text="Le coût doit être strictement positif (> 0).")
                return
        except ValueError:
            self.lbl_error.configure(text="Le coût doit être un nombre valide.")
            return

        try:
            success = self.on_save(u, v, cost)
            if success:
                self.destroy()
            else:
                self.lbl_error.configure(text="Impossible d'enregistrer l'arc.")
        except ValueError as ex:
            self.lbl_error.configure(text=str(ex))


class SearchView(ctk.CTkFrame):
    """Vue principale du Module 2 : Algorithmes de recherche dans les graphes."""

    def __init__(self, master, on_back_to_menu: Callable[[], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_back_to_menu = on_back_to_menu

        # État du graphe
        self.graph = self._load_default_graph()

        # État de l'exécution
        self.current_result: Optional[SearchResult] = None
        self.current_step_index: int = 0
        self.is_auto_playing: bool = False
        self.auto_play_timer_id: Optional[str] = None

        # Configuration de la grille principale
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_main_layout()

        # Affichage initial
        self._refresh_node_combos()
        self._refresh_graph_canvas()
        self._refresh_heuristics_table()

    def _load_default_graph(self) -> Graph:
        path = DATA_DIR / "graphe_cours.json"
        if path.exists():
            try:
                return Graph.load_from_json(path)
            except Exception:
                pass
        # Fallback simple
        g = Graph(name="Graphe Simple", start_node="A", goal_node="C")
        g.add_node("A", (1.0, 2.0), 4.0)
        g.add_node("B", (3.0, 3.0), 2.0)
        g.add_node("C", (5.0, 2.0), 0.0)
        g.add_edge("A", "B", 2.0)
        g.add_edge("B", "C", 3.0)
        return g

    # -----------------------------------------------------------------------
    # 1. Barre supérieure
    # -----------------------------------------------------------------------
    def _build_top_bar(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        top_bar.grid_columnconfigure(1, weight=1)

        btn_back = ctk.CTkButton(
            top_bar,
            text="⬅ Menu principal",
            width=140,
            height=34,
            fg_color=("gray75", "gray25"),
            text_color=("black", "white"),
            hover_color=("gray65", "gray35"),
            command=self._handle_back_to_menu,
        )
        btn_back.grid(row=0, column=0, sticky="w")

        self.lbl_title = ctk.CTkLabel(
            top_bar,
            text=f"Algorithmes de Recherche — {self.graph.name}",
            font=ctk.CTkFont(size=17, weight="bold"),
            anchor="w",
        )
        self.lbl_title.grid(row=0, column=1, padx=20, sticky="w")

        actions_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(
            actions_frame,
            text="📚 Exemple du cours",
            width=135,
            height=32,
            fg_color=("#0284c7", "#0369a1"),
            command=self._load_course_example,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            actions_frame,
            text="📂 Charger JSON",
            width=110,
            height=32,
            fg_color=("#1f6aa5", "#144870"),
            command=self._handle_load_json,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            actions_frame,
            text="💾 Sauvegarder",
            width=110,
            height=32,
            fg_color=("gray75", "gray28"),
            text_color=("black", "white"),
            command=self._handle_save_json,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            actions_frame,
            text="🗑 Vider",
            width=80,
            height=32,
            fg_color=("#ef4444", "#991b1b"),
            hover_color=("#dc2626", "#7f1d1d"),
            command=self._handle_clear_graph,
        ).pack(side="left", padx=4)

    # -----------------------------------------------------------------------
    # 2. Agencement principal (Gauche: Contrôles / Centre: Canvas / Droite: Trace)
    # -----------------------------------------------------------------------
    def _build_main_layout(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        container.grid_columnconfigure(0, weight=3, minsize=320)  # Contrôles
        container.grid_columnconfigure(1, weight=5, minsize=460)  # Graphe Canvas
        container.grid_columnconfigure(2, weight=4, minsize=360)  # Trace & Résultats
        container.grid_rowconfigure(0, weight=1)

        self._build_controls_column(container)
        self._build_canvas_column(container)
        self._build_trace_column(container)

    # -----------------------------------------------------------------------
    # Colonne Gauche : Construction du Graphe & Choix Algorithme
    # -----------------------------------------------------------------------
    def _build_controls_column(self, parent: ctk.CTkFrame) -> None:
        scroll_left = ctk.CTkScrollableFrame(parent)
        scroll_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        scroll_left.grid_columnconfigure(0, weight=1)

        # 1. Carte Configuration Départ / But
        card_endpoints = CardFrame(scroll_left)
        card_endpoints.pack(fill="x", pady=(0, 10))
        card_endpoints.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            card_endpoints,
            text="États Initial & But",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkLabel(card_endpoints, text="Départ :", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=1, column=0, padx=12, pady=2, sticky="w"
        )
        self.combo_start = ctk.CTkComboBox(card_endpoints, values=[""], command=self._on_start_changed, height=28)
        self.combo_start.grid(row=2, column=0, padx=(12, 6), pady=(0, 10), sticky="ew")

        ctk.CTkLabel(card_endpoints, text="Objectif :", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=1, column=1, padx=6, pady=2, sticky="w"
        )
        self.combo_goal = ctk.CTkComboBox(card_endpoints, values=[""], command=self._on_goal_changed, height=28)
        self.combo_goal.grid(row=2, column=1, padx=(6, 12), pady=(0, 10), sticky="ew")

        # 2. Carte Choix Algorithme en 2 étapes liées
        card_algo = CardFrame(scroll_left)
        card_algo.pack(fill="x", pady=10)
        card_algo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_algo,
            text="Choix de l'Algorithme",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 6))

        # Étape 1 : Catégorie
        ctk.CTkLabel(card_algo, text="1. Catégorie de recherche :", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=12, pady=(4, 2)
        )
        self.seg_category = ctk.CTkSegmentedButton(
            card_algo,
            values=["Non informée", "Informée"],
            command=self._on_category_changed,
            height=30,
        )
        self.seg_category.pack(fill="x", padx=12, pady=(0, 8))
        self.seg_category.set("Non informée")

        # Étape 2 : Algorithme
        ctk.CTkLabel(card_algo, text="2. Algorithme :", font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=12, pady=(4, 2)
        )
        self.combo_algo = ctk.CTkComboBox(
            card_algo,
            values=["BFS", "UCS", "DFS", "DLS", "IDS"],
            command=self._on_algo_changed,
            height=30,
        )
        self.combo_algo.pack(fill="x", padx=12, pady=(0, 8))
        self.combo_algo.set("BFS")

        # Champs conditionnels
        self.frame_conditional = ctk.CTkFrame(card_algo, fg_color="transparent")
        self.frame_conditional.pack(fill="x", padx=12, pady=4)
        self.frame_conditional.grid_columnconfigure(1, weight=1)

        self.lbl_cond = ctk.CTkLabel(self.frame_conditional, text="Limite (L) :", font=ctk.CTkFont(size=12))
        self.entry_cond = ctk.CTkEntry(self.frame_conditional, height=28)
        self._update_conditional_fields()

        # Bouton Vérifier Heuristique
        self.btn_check_h = ctk.CTkButton(
            card_algo,
            text="🔍 Vérifier l'Heuristique (h)",
            height=30,
            fg_color=("gray75", "gray28"),
            text_color=("black", "white"),
            command=self._handle_check_heuristics,
        )
        self.btn_check_h.pack(fill="x", padx=12, pady=(8, 12))

        # 3. Carte Construction du Graphe
        card_build = CardFrame(scroll_left)
        card_build.pack(fill="x", pady=10)
        card_build.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            card_build,
            text="Édition du Graphe",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkButton(
            card_build,
            text="+ Sommet",
            height=28,
            fg_color="#1f6aa5",
            command=self._open_add_node_dialog,
        ).grid(row=1, column=0, padx=(12, 4), pady=4, sticky="ew")

        ctk.CTkButton(
            card_build,
            text="+ Arc orienté",
            height=28,
            fg_color="#1f6aa5",
            command=self._open_add_edge_dialog,
        ).grid(row=1, column=1, padx=(4, 12), pady=4, sticky="ew")

        ctk.CTkButton(
            card_build,
            text="- Suppr. Sommet",
            height=28,
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self._delete_selected_node,
        ).grid(row=2, column=0, padx=(12, 4), pady=4, sticky="ew")

        ctk.CTkButton(
            card_build,
            text="- Suppr. Arc",
            height=28,
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self._delete_selected_edge,
        ).grid(row=2, column=1, padx=(4, 12), pady=4, sticky="ew")

        # 4. Table éditable des Heuristiques h(n)
        card_h = CardFrame(scroll_left)
        card_h.pack(fill="x", pady=10)
        card_h.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_h,
            text="Table des Heuristiques h(n)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.scroll_h_table = ctk.CTkFrame(card_h, fg_color="transparent")
        self.scroll_h_table.pack(fill="x", padx=10, pady=(0, 10))
        self.scroll_h_table.grid_columnconfigure(1, weight=1)

    # -----------------------------------------------------------------------
    # Colonne Centre : Visualisation Interactive Matplotlib
    # -----------------------------------------------------------------------
    def _build_canvas_column(self, parent: ctk.CTkFrame) -> None:
        center_card = CardFrame(parent)
        center_card.grid(row=0, column=1, sticky="nsew", padx=4)
        center_card.grid_columnconfigure(0, weight=1)
        center_card.grid_rowconfigure(1, weight=1)

        # En-tête du canevas avec indication interactive
        head_frame = ctk.CTkFrame(center_card, fg_color="transparent")
        head_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        head_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head_frame,
            text="Visualisation Dynamique du Graphe",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head_frame,
            text="💡 Astuce : Cliquez sur un espace vide pour ajouter un sommet",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray",
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        # Canvas Matplotlib intégré
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor("#161b22")  # Fond adapté au mode sombre
        self.ax.set_facecolor("#161b22")

        self.canvas = FigureCanvasTkAgg(self.fig, master=center_card)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Connecter le clic sur canevas
        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)

        # Barre de contrôle de lecture temporelle sous le graphe
        control_bar = ctk.CTkFrame(center_card, fg_color="transparent")
        control_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 12))
        control_bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.btn_prev = ctk.CTkButton(
            control_bar,
            text="◀ Précédent",
            width=90,
            height=32,
            fg_color=("gray75", "gray28"),
            text_color=("black", "white"),
            command=self._step_prev,
        )
        self.btn_prev.grid(row=0, column=0, padx=2)

        self.btn_next = ctk.CTkButton(
            control_bar,
            text="Suivant ▶",
            width=90,
            height=32,
            fg_color=("#0284c7", "#0369a1"),
            command=self._step_next,
        )
        self.btn_next.grid(row=0, column=1, padx=2)

        self.btn_play = ctk.CTkButton(
            control_bar,
            text="⏯ Lecture Auto",
            width=110,
            height=32,
            fg_color=("#16a34a", "#15803d"),
            command=self._toggle_auto_play,
        )
        self.btn_play.grid(row=0, column=2, padx=2)

        self.btn_run_all = ctk.CTkButton(
            control_bar,
            text="⚡ Tout exécuter",
            width=110,
            height=32,
            fg_color="#1f6aa5",
            command=self._run_all,
        )
        self.btn_run_all.grid(row=0, column=3, padx=2)

        self.btn_reset = ctk.CTkButton(
            control_bar,
            text="🔄 Réinitialiser",
            width=100,
            height=32,
            fg_color=("gray75", "gray28"),
            text_color=("black", "white"),
            command=self._reset_execution,
        )
        self.btn_reset.grid(row=0, column=4, padx=2)

        # Slider de vitesse
        speed_frame = ctk.CTkFrame(center_card, fg_color="transparent")
        speed_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        speed_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(speed_frame, text="Vitesse de lecture :", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, padx=(0, 10), sticky="w"
        )
        self.slider_speed = ctk.CTkSlider(speed_frame, from_=200, to=1500, number_of_steps=13)
        self.slider_speed.set(600)  # ms par pas
        self.slider_speed.grid(row=0, column=1, sticky="ew")

    # -----------------------------------------------------------------------
    # Colonne Droite : Trace des Étapes, Frontière & Propriétés
    # -----------------------------------------------------------------------
    def _build_trace_column(self, parent: ctk.CTkFrame) -> None:
        right_container = ctk.CTkFrame(parent, fg_color="transparent")
        right_container.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        right_container.grid_columnconfigure(0, weight=1)
        right_container.grid_rowconfigure(1, weight=1)

        # Bannière de Statut & Résumé du résultat
        self.banner_status = ctk.CTkLabel(
            right_container,
            text="Prêt. Sélectionnez un algorithme et cliquez sur 'Suivant' ou 'Tout exécuter'.",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#e1e4e8", "#21262d"),
            corner_radius=6,
            pady=8,
            wraplength=340,
        )
        self.banner_status.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # Onglets : Trace progressive / Frontière / Propriétés théoriques
        self.tabview_trace = ctk.CTkTabview(right_container, corner_radius=8)
        self.tabview_trace.grid(row=1, column=0, sticky="nsew")

        self.tab_steps = self.tabview_trace.add("Étapes & Métriques")
        self.tab_frontier = self.tabview_trace.add("Frontière (Open)")
        self.tab_props = self.tabview_trace.add("Propriétés Théoriques")
        self.tab_compare = self.tabview_trace.add("Comparaison (Bonus)")

        self._setup_steps_tab()
        self._setup_frontier_tab()
        self._setup_props_tab()
        self._setup_compare_tab()

    def _setup_steps_tab(self) -> None:
        self.tab_steps.grid_columnconfigure(0, weight=1)
        self.tab_steps.grid_rowconfigure(2, weight=1)

        # Métriques clés
        metrics_frame = ctk.CTkFrame(self.tab_steps, fg_color=("#f0fdf4", "#052e16"), corner_radius=6)
        metrics_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        metrics_frame.grid_columnconfigure((0, 1), weight=1)

        self.lbl_cost = ctk.CTkLabel(
            metrics_frame,
            text="Coût total : --",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#15803d", "#4ade80"),
        )
        self.lbl_cost.grid(row=0, column=0, padx=8, pady=4, sticky="w")

        self.lbl_expanded = ctk.CTkLabel(
            metrics_frame,
            text="Nœuds explorés : 0",
            font=ctk.CTkFont(size=12),
        )
        self.lbl_expanded.grid(row=0, column=1, padx=8, pady=4, sticky="e")

        self.lbl_path = ctk.CTkLabel(
            metrics_frame,
            text="Chemin : [En cours]",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=320,
            justify="left",
        )
        self.lbl_path.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="w")

        # Indicateur étape courante
        self.lbl_step_info = ctk.CTkLabel(
            self.tab_steps,
            text="Étape 0 / 0",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        self.lbl_step_info.grid(row=1, column=0, sticky="w", padx=8, pady=(4, 2))

        # Zone de texte de l'historique
        self.txt_trace = ctk.CTkTextbox(
            self.tab_steps,
            font=ctk.CTkFont(family="monospace", size=12),
            wrap="word",
            corner_radius=6,
        )
        self.txt_trace.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

    def _setup_frontier_tab(self) -> None:
        self.tab_frontier.grid_columnconfigure(0, weight=1)
        self.tab_frontier.grid_rowconfigure(1, weight=1)

        self.lbl_visited_summary = ctk.CTkLabel(
            self.tab_frontier,
            text="Visités (Closed) : []",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#7c3aed", "#a78bfa"),
            wraplength=330,
            justify="left",
        )
        self.lbl_visited_summary.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        # Tableau des nœuds dans la frontière
        self.txt_frontier = ctk.CTkTextbox(
            self.tab_frontier,
            font=ctk.CTkFont(family="monospace", size=12),
            wrap="none",
            corner_radius=6,
        )
        self.txt_frontier.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

    def _setup_props_tab(self) -> None:
        self.tab_props.grid_columnconfigure(0, weight=1)
        self.tab_props.grid_rowconfigure(0, weight=1)

        self.txt_props = ctk.CTkTextbox(
            self.tab_props,
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=6,
        )
        self.txt_props.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._update_properties_display()

    def _setup_compare_tab(self) -> None:
        self.tab_compare.grid_columnconfigure(0, weight=1)
        self.tab_compare.grid_rowconfigure(2, weight=1)

        # 1. Bouton de lancement
        top_btn_frame = ctk.CTkFrame(self.tab_compare, fg_color="transparent")
        top_btn_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        top_btn_frame.grid_columnconfigure(0, weight=1)

        btn_run_comp = ctk.CTkButton(
            top_btn_frame,
            text="🚀 Lancer le comparatif de tous les algorithmes",
            height=34,
            fg_color=("#16a34a", "#15803d"),
            hover_color=("#15803d", "#166534"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_run_comparison,
        )
        btn_run_comp.grid(row=0, column=0, sticky="ew")

        # 2. Bannière de mise en avant du meilleur
        self.lbl_compare_summary = ctk.CTkLabel(
            self.tab_compare,
            text="Cliquez sur le bouton ci-dessus pour comparer les algorithmes sur le graphe courant.",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#e1e4e8", "#21262d"),
            corner_radius=6,
            pady=6,
            wraplength=340,
        )
        self.lbl_compare_summary.grid(row=1, column=0, sticky="ew", padx=6, pady=4)

        # 3. Zone avec tableau et graphique
        content_scroll = ctk.CTkScrollableFrame(self.tab_compare, fg_color="transparent")
        content_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        content_scroll.grid_columnconfigure(0, weight=1)

        # Tableau texte formaté
        self.txt_compare_table = ctk.CTkTextbox(
            content_scroll,
            font=ctk.CTkFont(family="monospace", size=11),
            wrap="none",
            height=180,
            corner_radius=6,
        )
        self.txt_compare_table.pack(fill="x", expand=True, pady=(0, 8))
        self.txt_compare_table.insert("1.0", "Le tableau comparatif s'affichera ici après exécution.")
        self.txt_compare_table.configure(state="disabled")

        # Canevas du diagramme à barres
        chart_frame = ctk.CTkFrame(content_scroll, fg_color=("#ffffff", "#161b22"), corner_radius=8)
        chart_frame.pack(fill="x", expand=True, pady=4)
        chart_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            chart_frame,
            text="📊 Nœuds développés par algorithme",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.fig_chart = Figure(figsize=(4.5, 2.5), dpi=90)
        self.ax_chart = self.fig_chart.add_subplot(111)
        self.fig_chart.patch.set_facecolor("#161b22")
        self.ax_chart.set_facecolor("#161b22")

        self.canvas_chart = FigureCanvasTkAgg(self.fig_chart, master=chart_frame)
        self.canvas_chart_widget = self.canvas_chart.get_tk_widget()
        self.canvas_chart_widget.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.ax_chart.text(
            0.5, 0.5, "Diagramme comparatif", ha="center", va="center", color="gray", fontsize=10, transform=self.ax_chart.transAxes
        )
        self.ax_chart.axis("off")
        self.canvas_chart.draw()

    # -----------------------------------------------------------------------
    # Synchronisation des listes et champs
    # -----------------------------------------------------------------------
    def _refresh_node_combos(self) -> None:
        nodes = list(self.graph.nodes)
        self.combo_start.configure(values=nodes)
        self.combo_goal.configure(values=nodes)

        if self.graph.start_node in nodes:
            self.combo_start.set(self.graph.start_node)
        elif nodes:
            self.combo_start.set(nodes[0])
            self.graph.start_node = nodes[0]

        if self.graph.goal_node in nodes:
            self.combo_goal.set(self.graph.goal_node)
        elif len(nodes) > 1:
            self.combo_goal.set(nodes[-1])
            self.graph.goal_node = nodes[-1]

    def _on_start_changed(self, choice: str) -> None:
        self.graph.start_node = choice
        self._refresh_graph_canvas()

    def _on_goal_changed(self, choice: str) -> None:
        self.graph.goal_node = choice
        self._refresh_graph_canvas()

    def _on_category_changed(self, category: str) -> None:
        if "non informée" in category.lower():
            algos = ["BFS", "UCS", "DFS", "DLS", "IDS"]
        else:
            algos = ["Best-First", "A*", "SMA*", "RBFS"]

        self.combo_algo.configure(values=algos)
        self.combo_algo.set(algos[0])
        self._on_algo_changed(algos[0])

    def _on_algo_changed(self, algo: str) -> None:
        self._update_conditional_fields()
        self._update_properties_display()

    def _update_conditional_fields(self) -> None:
        algo = self.combo_algo.get()
        # Vider les widgets conditionnels existants
        for w in self.frame_conditional.winfo_children():
            w.grid_forget()

        if algo == "DLS":
            self.lbl_cond.configure(text="Limite de profondeur (L) :")
            self.lbl_cond.grid(row=0, column=0, padx=4, pady=2, sticky="w")
            self.entry_cond.delete(0, "end")
            self.entry_cond.insert(0, "3")
            self.entry_cond.grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        elif algo == "IDS":
            self.lbl_cond.configure(text="Limite max (L_max) :")
            self.lbl_cond.grid(row=0, column=0, padx=4, pady=2, sticky="w")
            self.entry_cond.delete(0, "end")
            self.entry_cond.insert(0, "10")
            self.entry_cond.grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        elif algo == "SMA*":
            self.lbl_cond.configure(text="Mémoire max (M nœuds) :")
            self.lbl_cond.grid(row=0, column=0, padx=4, pady=2, sticky="w")
            self.entry_cond.delete(0, "end")
            self.entry_cond.insert(0, "5")
            self.entry_cond.grid(row=0, column=1, padx=4, pady=2, sticky="ew")

    def _refresh_heuristics_table(self) -> None:
        for w in self.scroll_h_table.winfo_children():
            w.destroy()

        for i, node in enumerate(self.graph.nodes):
            ctk.CTkLabel(
                self.scroll_h_table,
                text=f"{node} :",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=30,
            ).grid(row=i, column=0, padx=(4, 6), pady=2, sticky="w")

            entry = ctk.CTkEntry(self.scroll_h_table, width=70, height=24)
            entry.insert(0, str(round(self.graph.heuristics.get(node, 0.0), 1)))
            entry.grid(row=i, column=1, padx=4, pady=2, sticky="ew")

            def on_focus_out(event, n=node, e=entry):
                try:
                    val = float(e.get().strip())
                    if val >= 0:
                        self.graph.set_heuristic(n, val)
                        self._refresh_graph_canvas()
                except ValueError:
                    pass

            entry.bind("<FocusOut>", on_focus_out)
            entry.bind("<Return>", on_focus_out)

    def _update_properties_display(self) -> None:
        algo = self.combo_algo.get()
        props = ALGORITHM_PROPERTIES.get(algo, {})
        if not props:
            return

        text = (
            f"═══ {props.get('nom', algo)} ═══\n\n"
            f"• Stratégie : {props.get('strategie', 'N/A')}\n\n"
            f"• Complexité en temps : {props.get('temps', 'N/A')}\n"
            f"• Complexité en espace : {props.get('espace', 'N/A')}\n\n"
            f"• Complétude : {props.get('completude', 'N/A')}\n"
            f"• Optimalité : {props.get('optimalite', 'N/A')}\n"
        )
        self.txt_props.configure(state="normal")
        self.txt_props.delete("1.0", "end")
        self.txt_props.insert("1.0", text)
        self.txt_props.configure(state="disabled")

    # -----------------------------------------------------------------------
    # Rendu Graphique Permanent Matplotlib
    # -----------------------------------------------------------------------
    def _refresh_graph_canvas(
        self,
        current_step: Optional[SearchStep] = None,
        final_path: Optional[List[str]] = None,
    ) -> None:
        """Trace le graphe avec ses nœuds, arêtes, flèches orientées, coûts et heuristiques."""
        self.ax.clear()

        # Thème de couleurs
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#161b22" if is_dark else "#f6f8fa"
        text_color = "white" if is_dark else "black"
        edge_default_color = "#4b5563" if is_dark else "#9ca3af"

        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)

        if not self.graph.nodes:
            self.ax.text(
                0.5,
                0.5,
                "Graphe vide.\nCliquez ou utilisez le panneau de gauche pour ajouter des sommets.",
                ha="center",
                va="center",
                color="gray",
                fontsize=12,
                transform=self.ax.transAxes,
            )
            self.ax.axis("off")
            self.canvas.draw()
            return

        positions = dict(self.graph.positions)
        # S'assurer que chaque sommet a une position
        for i, n in enumerate(self.graph.nodes):
            if n not in positions:
                angle = 2 * math.pi * i / len(self.graph.nodes)
                positions[n] = (5.0 + 3.5 * math.cos(angle), 5.0 + 3.5 * math.sin(angle))
                self.graph.positions[n] = positions[n]

        # Calcul des limites
        xs = [pos[0] for pos in positions.values()]
        ys = [pos[1] for pos in positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        margin_x = max(1.5, (max_x - min_x) * 0.2)
        margin_y = max(1.5, (max_y - min_y) * 0.2)
        self.ax.set_xlim(min_x - margin_x, max_x + margin_x)
        self.ax.set_ylim(min_y - margin_y, max_y + margin_y)
        self.ax.axis("off")

        # États pour la coloration
        cur_node = current_step.current_node if current_step else None
        visited_nodes = set(current_step.visited) if current_step else set()
        frontier_nodes = set(item["state"] for item in current_step.frontier) if current_step else set()
        path_nodes = set(final_path) if final_path else set()

        path_edges: Set[Tuple[str, str]] = set()
        if final_path and len(final_path) > 1:
            for i in range(len(final_path) - 1):
                path_edges.add((final_path[i], final_path[i + 1]))

        # 1. Dessin des arcs orientés (flèches)
        for edge in self.graph.edges:
            u, v, cost = edge.from_node, edge.to_node, edge.cost
            if u not in positions or v not in positions:
                continue

            x1, y1 = positions[u]
            x2, y2 = positions[v]

            # Déterminer si l'arc fait partie du chemin optimal
            is_path_edge = (u, v) in path_edges
            edge_color = "#22c55e" if is_path_edge else edge_default_color
            edge_width = 3.5 if is_path_edge else 1.5
            alpha = 1.0 if is_path_edge else 0.7

            # Calcul d'un raccourcissement pour que la pointe ne touche pas le centre du nœud
            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy)
            if dist == 0:
                continue

            node_radius = 0.45
            ux = dx / dist
            uy = dy / dist
            start_x = x1 + ux * node_radius
            start_y = y1 + uy * node_radius
            end_x = x2 - ux * node_radius
            end_y = y2 - uy * node_radius

            # Arc avec flèche
            self.ax.annotate(
                "",
                xy=(end_x, end_y),
                xytext=(start_x, start_y),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=edge_color,
                    lw=edge_width,
                    mutation_scale=16 if is_path_edge else 12,
                    alpha=alpha,
                ),
            )

            # Étiquette de coût au milieu de l'arc (avec léger décalage orthogonal)
            mid_x = (start_x + end_x) / 2 + (-uy) * 0.22
            mid_y = (start_y + end_y) / 2 + (ux) * 0.22
            self.ax.text(
                mid_x,
                mid_y,
                str(int(cost) if cost.is_integer() else cost),
                fontsize=10,
                fontweight="bold" if is_path_edge else "normal",
                color="#10b981" if is_path_edge else ("#38bdf8" if is_dark else "#0369a1"),
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    fc=bg_color,
                    ec="none",
                    alpha=0.85,
                ),
            )

        # 2. Dessin des sommets (cercles)
        start_node = self.graph.start_node
        goal_node = self.graph.goal_node

        for node, (x, y) in positions.items():
            # Détermination de la couleur du sommet
            if final_path and node in path_nodes:
                circle_color = "#22c55e"  # Vert éclatant
                border_color = "#15803d"
            elif node == cur_node:
                circle_color = "#f59e0b"  # Ambre / Jaune développement
                border_color = "#b45309"
            elif node == start_node:
                circle_color = "#0284c7"  # Bleu ciel départ
                border_color = "#0369a1"
            elif node == goal_node:
                circle_color = "#e11d48"  # Rouge rubis but
                border_color = "#9f1239"
            elif node in frontier_nodes:
                circle_color = "#06b6d4"  # Cyan frontière
                border_color = "#0891b2"
            elif node in visited_nodes:
                circle_color = "#7c3aed"  # Violet visité
                border_color = "#5b21b6"
            else:
                circle_color = "#334155" if is_dark else "#cbd5e1"
                border_color = "#64748b"

            # Cercle du nœud
            circle = matplotlib.patches.Circle(
                (x, y),
                radius=0.45,
                facecolor=circle_color,
                edgecolor=border_color,
                linewidth=2.5 if (node in path_nodes or node == cur_node) else 1.5,
                zorder=10,
            )
            self.ax.add_patch(circle)

            # Nom du sommet au centre
            self.ax.text(
                x,
                y,
                node,
                fontsize=12,
                fontweight="bold",
                color="white" if (is_dark or circle_color not in ["#cbd5e1"]) else "black",
                ha="center",
                va="center",
                zorder=11,
            )

            # Affichage de h(n) sous le nœud
            h_val = self.graph.heuristics.get(node, 0.0)
            h_text = f"h={int(h_val) if h_val.is_integer() else h_val}"
            tag_role = ""
            if node == start_node:
                tag_role = " [DÉPART]"
            elif node == goal_node:
                tag_role = " [BUT]"

            self.ax.text(
                x,
                y - 0.68,
                f"{h_text}{tag_role}",
                fontsize=9,
                fontweight="bold" if tag_role else "normal",
                color="#eab308" if node == goal_node else text_color,
                ha="center",
                va="top",
                zorder=11,
            )

        self.canvas.draw()

    def _on_canvas_click(self, event) -> None:
        """Ajoute un sommet par clic sur un espace vide du canevas."""
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        click_pos = (event.xdata, event.ydata)

        # Vérifier si on a cliqué sur un sommet existant
        for n, (x, y) in self.graph.positions.items():
            if math.hypot(x - click_pos[0], y - click_pos[1]) <= 0.6:
                # Clic sur un sommet existant : proposer de le définir comme départ ou but
                self._prompt_set_start_or_goal(n)
                return

        # Clic sur espace vide : ouvrir dialogue d'ajout
        AddNodeDialog(
            self,
            on_save=lambda name, pos, h: self._handle_add_node(name, pos, h),
            default_pos=click_pos,
        )

    def _prompt_set_start_or_goal(self, node: str) -> None:
        """Permet de définir rapidement un sommet cliqué comme départ ou but."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Sommet « {node} »")
        dialog.geometry("320x180")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"Définir le rôle pour '{node}' :",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(18, 12))

        def set_start():
            self.graph.start_node = node
            self.combo_start.set(node)
            self._refresh_graph_canvas()
            dialog.destroy()

        def set_goal():
            self.graph.goal_node = node
            self.combo_goal.set(node)
            self._refresh_graph_canvas()
            dialog.destroy()

        ctk.CTkButton(dialog, text="🟢 Définir comme DÉPART", fg_color="#0284c7", command=set_start).pack(
            fill="x", padx=30, pady=4
        )
        ctk.CTkButton(dialog, text="🔴 Définir comme BUT", fg_color="#e11d48", command=set_goal).pack(
            fill="x", padx=30, pady=4
        )

    # -----------------------------------------------------------------------
    # Gestion des Actions d'Édition du Graphe
    # -----------------------------------------------------------------------
    def _handle_add_node(self, name: str, pos: Tuple[float, float], h: float) -> bool:
        if self.graph.add_node(name, pos, h):
            if not self.graph.start_node:
                self.graph.start_node = name
            elif not self.graph.goal_node and name != self.graph.start_node:
                self.graph.goal_node = name
            self._refresh_node_combos()
            self._refresh_graph_canvas()
            self._refresh_heuristics_table()
            return True
        return False

    def _open_add_node_dialog(self) -> None:
        # Trouver une position par défaut non occupée
        pos = (len(self.graph.nodes) * 1.5, 3.0)
        AddNodeDialog(
            self,
            on_save=lambda name, p, h: self._handle_add_node(name, p, h),
            default_pos=pos,
        )

    def _open_add_edge_dialog(self) -> None:
        if len(self.graph.nodes) < 2:
            MessageDialog(
                self,
                "Sommets insuffisants",
                "Il faut au moins 2 sommets pour créer un arc.",
                "warning",
            )
            return

        def on_save_edge(u: str, v: str, cost: float) -> bool:
            res = self.graph.add_edge(u, v, cost)
            self._refresh_graph_canvas()
            return res

        AddEdgeDialog(self, self.graph.nodes, on_save=on_save_edge)

    def _delete_selected_node(self) -> None:
        if not self.graph.nodes:
            return
        node = self.combo_start.get()
        if self.graph.remove_node(node):
            self._refresh_node_combos()
            self._refresh_graph_canvas()
            self._refresh_heuristics_table()

    def _delete_selected_edge(self) -> None:
        if not self.graph.edges:
            MessageDialog(self, "Aucun arc", "Le graphe ne contient aucun arc.", "info")
            return

        u = self.combo_start.get()
        neighbors = self.graph.get_neighbors(u)
        if not neighbors:
            MessageDialog(self, "Aucun arc sortant", f"Aucun arc partant de '{u}'.", "info")
            return

        v = neighbors[0][0]
        self.graph.remove_edge(u, v)
        self._refresh_graph_canvas()

    def _load_course_example(self) -> None:
        path = DATA_DIR / "graphe_cours.json"
        if path.exists():
            try:
                self.graph = Graph.load_from_json(path)
                self.lbl_title.configure(text=f"Algorithmes de Recherche — {self.graph.name}")
                self._reset_execution()
                self._refresh_node_combos()
                self._refresh_graph_canvas()
                self._refresh_heuristics_table()
                MessageDialog(self, "Exemple chargé", "Le graphe officiel du cours a été chargé avec succès.", "success")
            except Exception as e:
                MessageDialog(self, "Erreur", f"Échec du chargement : {e}", "error")

    def _handle_clear_graph(self) -> None:
        self.graph = Graph(name="Graphe Vierge")
        self._reset_execution()
        self._refresh_node_combos()
        self._refresh_graph_canvas()
        self._refresh_heuristics_table()

    def _handle_save_json(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Sauvegarder le graphe en JSON",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            initialdir=str(DATA_DIR),
            initialfile="mon_graphe.json",
        )
        if not path:
            return
        try:
            self.graph.save_to_json(path)
            MessageDialog(self, "Sauvegarde réussie", f"Graphe sauvegardé dans :\n{path}", "success")
        except Exception as e:
            MessageDialog(self, "Erreur d'écriture", f"Impossible d'écrire le fichier : {e}", "error")

    def _handle_load_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Charger un graphe JSON",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
            initialdir=str(DATA_DIR),
        )
        if not path:
            return
        try:
            loaded = Graph.load_from_json(path)
            self.graph = loaded
            self.lbl_title.configure(text=f"Algorithmes de Recherche — {self.graph.name}")
            self._reset_execution()
            self._refresh_node_combos()
            self._refresh_graph_canvas()
            self._refresh_heuristics_table()
            MessageDialog(self, "Graphe chargé", f"Le graphe « {loaded.name} » a été chargé ({len(loaded.nodes)} sommets).", "success")
        except Exception as e:
            MessageDialog(self, "Erreur JSON", f"Format de graphe invalide : {e}", "error")

    def _handle_check_heuristics(self) -> None:
        goal = self.graph.goal_node
        if not goal or goal not in self.graph.nodes:
            MessageDialog(self, "But manquant", "Veuillez définir un état but valide pour analyser l'heuristique.", "warning")
            return

        admiss = verify_admissibility(self.graph, goal)
        consist = verify_consistency(self.graph, goal)

        lines = [
            f"═══ ANALYSE DE L'HEURISTIQUE POUR LE BUT « {goal} » ═══\n",
            f"1. ADMISSIBILITÉ (h(n) ≤ h*(n)) :",
            admiss["message"],
        ]
        if admiss["violations"]:
            lines.append("Violations détectées :")
            for v in admiss["violations"]:
                lines.append(f"  • {v}")

        lines.extend([
            "\n2. CONSISTANCE / MONOTONIE (h(n) ≤ c(n,n') + h(n')) :",
            consist["message"],
        ])
        if consist["violations"]:
            lines.append("Violations détectées :")
            for v in consist["violations"]:
                lines.append(f"  • {v}")

        icon = "success" if (admiss["is_admissible"] and consist["is_consistent"]) else "warning"
        MessageDialog(self, "Rapport d'Heuristique", "\n".join(lines), icon_type=icon)

    # -----------------------------------------------------------------------
    # Exécution & Contrôle Pas-à-Pas
    # -----------------------------------------------------------------------
    def _prepare_search(self) -> bool:
        """Valide et initialise l'exécution si elle n'a pas encore été calculée."""
        if self.current_result is not None:
            return True

        algo = self.combo_algo.get()
        start = self.combo_start.get()
        goal = self.combo_goal.get()

        if not start or start not in self.graph.nodes:
            MessageDialog(self, "Départ invalide", "Veuillez sélectionner un sommet de départ valide.", "warning")
            return False
        if not goal or goal not in self.graph.nodes:
            MessageDialog(self, "But invalide", "Veuillez sélectionner un sommet objectif valide.", "warning")
            return False

        # Vérifier si h manque pour un algorithme informé
        category = self.seg_category.get()
        if "informée" in category.lower():
            missing_h = [n for n in self.graph.nodes if n not in self.graph.heuristics]
            if missing_h:
                MessageDialog(
                    self,
                    "Heuristique manquante",
                    f"Les sommets suivants n'ont pas d'heuristique définie : {', '.join(missing_h)}.\n"
                    "Veuillez renseigner leurs valeurs dans le tableau.",
                    "warning",
                )
                return False

        # Paramètres conditionnels
        depth_limit = 3
        max_depth = 10
        max_memory = 5

        try:
            if algo == "DLS":
                depth_limit = int(self.entry_cond.get().strip())
            elif algo == "IDS":
                max_depth = int(self.entry_cond.get().strip())
            elif algo == "SMA*":
                max_memory = int(self.entry_cond.get().strip())
        except ValueError:
            MessageDialog(self, "Paramètre invalide", "Veuillez entrer une valeur numérique entière valide.", "error")
            return False

        try:
            self.current_result = run_search_algorithm(
                self.graph,
                algo,
                start=start,
                goal=goal,
                depth_limit=depth_limit,
                max_depth_limit=max_depth,
                max_memory=max_memory,
            )
            self.current_step_index = 0
            return True
        except Exception as e:
            MessageDialog(self, "Erreur d'exécution", f"Une erreur s'est produite : {e}", "error")
            return False

    def _render_current_step(self) -> None:
        """Affiche l'étape courante dans l'interface et sur le graphe."""
        if not self.current_result or not self.current_result.steps:
            return

        idx = max(0, min(self.current_step_index, len(self.current_result.steps) - 1))
        step = self.current_result.steps[idx]
        total_steps = len(self.current_result.steps)

        # 1. Mise à jour des libellés
        self.lbl_step_info.configure(text=f"Étape {idx + 1} / {total_steps}")

        is_last = (idx == total_steps - 1)
        final_path = self.current_result.path if (is_last and self.current_result.status == "TROUVE") else None

        if self.current_result.status == "TROUVE":
            if is_last:
                self.banner_status.configure(
                    text=f"✔ Objectif atteint ! Coût total : {round(self.current_result.total_cost, 2)}.",
                    fg_color=("#dcfce7", "#14532d"),
                    text_color=("#15803d", "#86efac"),
                )
            else:
                self.banner_status.configure(
                    text=f"Recherche en cours : {step.action_desc}",
                    fg_color=("#e0f2fe", "#075985"),
                    text_color=("#0369a1", "#7dd3fc"),
                )
        elif self.current_result.status == "ECHEC_LIMITE":
            self.banner_status.configure(
                text="⚠ Échec dû à la limite de profondeur ou de mémoire.",
                fg_color=("#fef3c7", "#78350f"),
                text_color=("#b45309", "#fde68a"),
            )
        else:
            self.banner_status.configure(
                text="✘ Aucun chemin trouvé vers l'objectif.",
                fg_color=("#fee2e2", "#7f1d1d"),
                text_color=("#b91c1c", "#fca5a5"),
            )

        # Métriques
        if final_path:
            self.lbl_cost.configure(text=f"Coût total : {round(self.current_result.total_cost, 2)}")
            self.lbl_path.configure(text=f"Chemin : {' ➔ '.join(final_path)}")
        else:
            self.lbl_cost.configure(text="Coût total : --")
            self.lbl_path.configure(text=f"Action : {step.action_desc}")

        self.lbl_expanded.configure(text=f"Nœuds explorés : {len(step.visited)}")

        # 2. Rendu de l'historique dans la zone de texte
        history_lines = []
        for i in range(idx + 1):
            s = self.current_result.steps[i]
            cur_repr = f"[{s.current_node}]" if s.current_node else "[Init]"
            history_lines.append(f"#{s.step_num:02d} {cur_repr} ➔ {s.action_desc}")
        self.txt_trace.delete("1.0", "end")
        self.txt_trace.insert("1.0", "\n".join(history_lines))
        self.txt_trace.see("end")

        # 3. Rendu de la frontière (Open-List)
        self.lbl_visited_summary.configure(text=f"Visités (Closed) : [{', '.join(step.visited)}]")

        frontier_lines = [
            f"{'État':<6} | {'g(n)':<6} | {'h(n)':<6} | {'f(n)':<6} | {'Prof.':<5} | {'Parent'}",
            "-" * 45,
        ]
        for item in step.frontier:
            frontier_lines.append(
                f"{item['state']:<6} | {item['g']:<6.1f} | {item['h']:<6.1f} | {item['f']:<6.1f} | {item['depth']:<5} | {item.get('parent') or '-'}"
            )
        if not step.frontier:
            frontier_lines.append("(Frontière vide)")

        self.txt_frontier.delete("1.0", "end")
        self.txt_frontier.insert("1.0", "\n".join(frontier_lines))

        # 4. Rafraîchissement visuel du graphe
        self._refresh_graph_canvas(current_step=step, final_path=final_path)

    def _step_next(self) -> None:
        if not self._prepare_search():
            return
        if self.current_result and self.current_step_index < len(self.current_result.steps) - 1:
            self.current_step_index += 1
            self._render_current_step()

    def _step_prev(self) -> None:
        if not self.current_result:
            return
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._render_current_step()

    def _run_all(self) -> None:
        if not self._prepare_search():
            return
        self._stop_auto_play()
        if self.current_result:
            self.current_step_index = len(self.current_result.steps) - 1
            self._render_current_step()

    def _reset_execution(self) -> None:
        self._stop_auto_play()
        self.current_result = None
        self.current_step_index = 0
        self.lbl_cost.configure(text="Coût total : --")
        self.lbl_expanded.configure(text="Nœuds explorés : 0")
        self.lbl_path.configure(text="Chemin : [Prêt]")
        self.lbl_step_info.configure(text="Étape 0 / 0")
        self.txt_trace.delete("1.0", "end")
        self.txt_frontier.delete("1.0", "end")
        self.banner_status.configure(
            text="Prêt. Sélectionnez un algorithme et lancez l'exploration.",
            fg_color=("#e1e4e8", "#21262d"),
            text_color=("black", "white"),
        )
        self._refresh_graph_canvas()

    def _toggle_auto_play(self) -> None:
        if self.is_auto_playing:
            self._stop_auto_play()
        else:
            if not self._prepare_search():
                return
            self.is_auto_playing = True
            self.btn_play.configure(text="⏸ Pause", fg_color=("#d97706", "#b45309"))
            self._auto_play_step()

    def _auto_play_step(self) -> None:
        if not self.is_auto_playing or not self.current_result:
            return

        if self.current_step_index < len(self.current_result.steps) - 1:
            self.current_step_index += 1
            self._render_current_step()
            delay = int(self.slider_speed.get())
            self.auto_play_timer_id = self.after(delay, self._auto_play_step)
        else:
            self._stop_auto_play()

    def _stop_auto_play(self) -> None:
        self.is_auto_playing = False
        self.btn_play.configure(text="⏯ Lecture Auto", fg_color=("#16a34a", "#15803d"))
        if self.auto_play_timer_id:
            try:
                self.after_cancel(self.auto_play_timer_id)
            except Exception:
                pass
            self.auto_play_timer_id = None

    def _handle_back_to_menu(self) -> None:
        self._stop_auto_play()
        self.on_back_to_menu()

    def _handle_run_comparison(self) -> None:
        """Exécute la comparaison de tous les algorithmes sur le graphe courant."""
        start = self.combo_start.get().strip()
        goal = self.combo_goal.get().strip()

        if not start or start not in self.graph.nodes:
            MessageDialog(self, "Départ invalide", "Veuillez sélectionner un sommet de départ valide.", "warning")
            return
        if not goal or goal not in self.graph.nodes:
            MessageDialog(self, "But invalide", "Veuillez sélectionner un sommet but valide.", "warning")
            return

        comp = compare_all_algorithms(self.graph, start=start, goal=goal)
        if not comp["success"]:
            MessageDialog(self, "Erreur", comp.get("error", "Erreur lors de la comparaison."), "error")
            return

        best_name = comp["best_algo"]
        min_cost = comp["min_cost"]

        if best_name and min_cost is not None:
            self.lbl_compare_summary.configure(
                text=f"★ Meilleure solution : {best_name} (Coût optimal : {round(min_cost, 2)})",
                fg_color=("#dcfce7", "#14532d"),
                text_color=("#15803d", "#86efac"),
            )
        else:
            self.lbl_compare_summary.configure(
                text="✘ Aucun algorithme n'a pu trouver de chemin vers le but.",
                fg_color=("#fee2e2", "#7f1d1d"),
                text_color=("#b91c1c", "#fca5a5"),
            )

        # Génération du tableau formaté
        headers = f"{'Algorithme':<11} | {'Trouvé?':<7} | {'Coût':<6} | {'Nœuds':<6} | {'Temps (ms)':<10} | {'Optimal?':<8} | {'Chemin'}"
        sep = "-" * len(headers) + "--------------------"
        lines = [headers, sep]

        algos_list = []
        nodes_list = []
        colors_list = []

        for row in comp["results"]:
            algo_str = row["algorithm"]
            found_str = "✔ Oui" if row["found"] else "✘ Non"
            cost_str = f"{row['cost']:.1f}" if row["found"] else "--"
            nodes_str = str(row["nodes_expanded"])
            time_str = f"{row['time_ms']:.2f}"
            opt_str = "★ OUI" if row["is_optimal"] else ("Non" if row["found"] else "--")
            path_str = " ➔ ".join(row["path"]) if row["found"] else "(aucun)"

            lines.append(
                f"{algo_str:<11} | {found_str:<7} | {cost_str:<6} | {nodes_str:<6} | {time_str:<10} | {opt_str:<8} | {path_str}"
            )

            algos_list.append(algo_str)
            nodes_list.append(row["nodes_expanded"])
            if row["algorithm"] == best_name:
                colors_list.append("#22c55e")  # Vert champion
            elif row["is_optimal"]:
                colors_list.append("#3b82f6")  # Bleu optimal
            elif not row["found"]:
                colors_list.append("#ef4444")  # Rouge échec
            else:
                colors_list.append("#eab308")  # Jaune trouvé sous-optimal

        self.txt_compare_table.configure(state="normal")
        self.txt_compare_table.delete("1.0", "end")
        self.txt_compare_table.insert("1.0", "\n".join(lines))
        self.txt_compare_table.configure(state="disabled")

        # Diagramme à barres Matplotlib
        self.ax_chart.clear()
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_col = "#161b22" if is_dark else "#ffffff"
        text_col = "white" if is_dark else "black"
        self.fig_chart.patch.set_facecolor(bg_col)
        self.ax_chart.set_facecolor(bg_col)

        bars = self.ax_chart.bar(algos_list, nodes_list, color=colors_list, width=0.6)
        self.ax_chart.set_ylabel("Nœuds explorés", color=text_col, fontsize=9)
        self.ax_chart.tick_params(axis="x", colors=text_col, labelsize=8, rotation=25)
        self.ax_chart.tick_params(axis="y", colors=text_col, labelsize=8)

        for bar in bars:
            height = bar.get_height()
            self.ax_chart.annotate(
                f"{int(height)}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color=text_col,
                fontweight="bold",
            )

        self.fig_chart.tight_layout()
        self.canvas_chart.draw()
