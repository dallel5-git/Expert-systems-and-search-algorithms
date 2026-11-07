"""Vue principale du Module 1 : Systèmes Experts.

Offre une interface interactive complète :
- Visualisation et gestion dynamique des faits et règles (ajout, modif, suppression).
- Chargement prédéfini (bases du cours) et import/export JSON.
- Sélection de l'objectif avec indicateur en temps réel de présence dans les faits.
- Choix de l'algorithme : Chaînage avant, Chaînage arrière, Chaînage mixte.
- Modes d'exécution pas-à-pas ('Étape suivante') et continu ('Exécuter tout').
- Tableau de trace d'inférence, arbre de preuve indenté et panneau d'explications.
"""

from __future__ import annotations
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional
import customtkinter as ctk

from core.expert_system import (
    KnowledgeBase,
    Rule,
    ForwardResult,
    BackwardResult,
    MixedResult,
    ForwardStepper,
    forward_chaining,
    backward_chaining,
    mixed_chaining,
    normalize_fact,
)
from gui.widgets import (
    CardFrame,
    TraceTableView,
    ProofTreeView,
    AddRuleDialog,
    MessageDialog,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class ExpertView(ctk.CTkFrame):
    """Vue complète pour l'exécution et l'administration du système expert."""

    def __init__(self, master, on_back_to_menu: Callable[[], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_back_to_menu = on_back_to_menu

        # État interne
        self.initial_kb: KnowledgeBase = self._load_default_kb()
        self.current_kb: KnowledgeBase = self.initial_kb.clone()
        self.stepper: Optional[ForwardStepper] = None

        # Configuration de la grille principale
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_main_layout()

        # Initialisation de l'affichage
        self._refresh_kb_view()
        self._update_goal_combobox()
        self._check_goal_status()

    # -----------------------------------------------------------------------
    # Chargement initial
    # -----------------------------------------------------------------------
    def _load_default_kb(self) -> KnowledgeBase:
        default_file = DATA_DIR / "kb_exercice.json"
        if default_file.exists():
            try:
                return KnowledgeBase.load_from_json(default_file)
            except Exception:
                pass
        return KnowledgeBase(
            name="Base Exemple",
            description="Exemple par défaut",
            facts=["A"],
            rules=[Rule("R1", ["A"], "B")],
        )

    # -----------------------------------------------------------------------
    # 1. Barre supérieure de navigation et d'actions globales
    # -----------------------------------------------------------------------
    def _build_top_bar(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        top_bar.grid_columnconfigure(1, weight=1)

        # Bouton retour
        btn_back = ctk.CTkButton(
            top_bar,
            text="⬅ Menu principal",
            width=140,
            height=34,
            fg_color=("gray75", "gray25"),
            text_color=("black", "white"),
            hover_color=("gray65", "gray35"),
            command=self.on_back_to_menu,
        )
        btn_back.grid(row=0, column=0, sticky="w")

        # Titre de la base active
        self.lbl_kb_title = ctk.CTkLabel(
            top_bar,
            text=f"Système Expert — {self.current_kb.name}",
            font=ctk.CTkFont(size=17, weight="bold"),
            anchor="w",
        )
        self.lbl_kb_title.grid(row=0, column=1, padx=20, sticky="w")

        # Actions sur la base
        actions_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="e")

        btn_load = ctk.CTkButton(
            actions_frame,
            text="📂 Charger JSON",
            width=110,
            height=32,
            fg_color=("#1f6aa5", "#144870"),
            command=self._handle_load_json,
        )
        btn_load.pack(side="left", padx=4)

        btn_save = ctk.CTkButton(
            actions_frame,
            text="💾 Sauvegarder JSON",
            width=120,
            height=32,
            fg_color=("gray75", "gray28"),
            text_color=("black", "white"),
            hover_color=("gray65", "gray38"),
            command=self._handle_save_json,
        )
        btn_save.pack(side="left", padx=4)

    # -----------------------------------------------------------------------
    # 2. Agencement principal en 2 colonnes
    # -----------------------------------------------------------------------
    def _build_main_layout(self) -> None:
        main_panes = ctk.CTkFrame(self, fg_color="transparent")
        main_panes.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        main_panes.grid_columnconfigure(0, weight=4, minsize=420)  # Colonne gauche (Base)
        main_panes.grid_columnconfigure(1, weight=6, minsize=550)  # Colonne droite (Raisonnement)
        main_panes.grid_rowconfigure(0, weight=1)

        self._build_left_column(main_panes)
        self._build_right_column(main_panes)

    # -----------------------------------------------------------------------
    # Colonne gauche : Gestionnaire de base (Faits & Règles)
    # -----------------------------------------------------------------------
    def _build_left_column(self, parent: ctk.CTkFrame) -> None:
        left_card = CardFrame(parent)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_card.grid_columnconfigure(0, weight=1)
        left_card.grid_rowconfigure(2, weight=1)

        # En-tête avec sélecteur de bases prédéfinies du cours
        preset_frame = ctk.CTkFrame(left_card, fg_color="transparent")
        preset_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 8))
        preset_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            preset_frame,
            text="Exemples du cours :",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.preset_combo = ctk.CTkComboBox(
            preset_frame,
            values=[
                "Exercice théorique (C)",
                "Pâtisserie (Les Tartes)",
                "Géométrie (Triangles)",
                "Zoologie (Autruche)",
            ],
            command=self._handle_preset_change,
            height=30,
        )
        self.preset_combo.grid(row=0, column=1, sticky="ew")

        # Description de la base
        self.lbl_kb_desc = ctk.CTkLabel(
            left_card,
            text=self.current_kb.description or "Base de connaissances active",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray",
            anchor="w",
        )
        self.lbl_kb_desc.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        # Onglets Faits / Règles
        self.tabview_kb = ctk.CTkTabview(left_card, corner_radius=8)
        self.tabview_kb.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))

        self.tab_facts = self.tabview_kb.add("Base de Faits (BF)")
        self.tab_rules = self.tabview_kb.add("Base de Règles (BR)")

        self._setup_facts_tab()
        self._setup_rules_tab()

    def _setup_facts_tab(self) -> None:
        self.tab_facts.grid_columnconfigure(0, weight=1)
        self.tab_facts.grid_rowconfigure(1, weight=1)

        # Barre d'ajout de fait
        add_frame = ctk.CTkFrame(self.tab_facts, fg_color="transparent")
        add_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 8))
        add_frame.grid_columnconfigure(0, weight=1)

        self.entry_new_fact = ctk.CTkEntry(
            add_frame, placeholder_text="Nouveau fait (ex: farine)...", height=32
        )
        self.entry_new_fact.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.entry_new_fact.bind("<Return>", lambda e: self._handle_add_fact())

        btn_add = ctk.CTkButton(
            add_frame,
            text="+ Ajouter",
            width=90,
            height=32,
            fg_color="#1f6aa5",
            command=self._handle_add_fact,
        )
        btn_add.grid(row=0, column=1, sticky="e")

        # Liste défilante des faits
        self.scroll_facts = ctk.CTkScrollableFrame(self.tab_facts, fg_color="transparent")
        self.scroll_facts.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_facts.grid_columnconfigure(0, weight=1)

    def _setup_rules_tab(self) -> None:
        self.tab_rules.grid_columnconfigure(0, weight=1)
        self.tab_rules.grid_rowconfigure(1, weight=1)

        # Barre d'action : bouton ajouter une règle
        top_rules_frame = ctk.CTkFrame(self.tab_rules, fg_color="transparent")
        top_rules_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 8))
        top_rules_frame.grid_columnconfigure(0, weight=1)

        btn_add_rule = ctk.CTkButton(
            top_rules_frame,
            text="+ Nouvelle règle (SI... ALORS...)",
            height=32,
            fg_color="#1f6aa5",
            command=self._handle_open_add_rule_dialog,
        )
        btn_add_rule.grid(row=0, column=0, sticky="ew")

        # Liste défilante des règles
        self.scroll_rules = ctk.CTkScrollableFrame(self.tab_rules, fg_color="transparent")
        self.scroll_rules.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_rules.grid_columnconfigure(0, weight=1)

    # -----------------------------------------------------------------------
    # Colonne droite : Raisonnement, Traces et Résultats
    # -----------------------------------------------------------------------
    def _build_right_column(self, parent: ctk.CTkFrame) -> None:
        right_container = ctk.CTkFrame(parent, fg_color="transparent")
        right_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_container.grid_columnconfigure(0, weight=1)
        right_container.grid_rowconfigure(1, weight=1)

        # 1. Carte supérieure : Contrôle du raisonnement
        card_control = CardFrame(right_container)
        card_control.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card_control.grid_columnconfigure(1, weight=1)

        # Ligne 1 : Objectif (But)
        ctk.CTkLabel(
            card_control,
            text="Objectif (But) :",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=15, pady=(15, 6), sticky="w")

        goal_select_frame = ctk.CTkFrame(card_control, fg_color="transparent")
        goal_select_frame.grid(row=0, column=1, padx=15, pady=(15, 6), sticky="ew")
        goal_select_frame.grid_columnconfigure(0, weight=1)

        self.combo_goal = ctk.CTkComboBox(
            goal_select_frame,
            values=["C"],
            command=lambda val: self._check_goal_status(),
            height=32,
        )
        self.combo_goal.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.combo_goal.set("C")

        # Badge indicateur temps réel pour le but
        self.lbl_goal_status = ctk.CTkLabel(
            goal_select_frame,
            text="ℹ Objectif à démontrer",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#e1e4e8", "#21262d"),
            corner_radius=6,
            padx=10,
            pady=4,
        )
        self.lbl_goal_status.grid(row=0, column=1, sticky="e")

        # Ligne 2 : Méthode de chaînage
        ctk.CTkLabel(
            card_control,
            text="Méthode :",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=1, column=0, padx=15, pady=6, sticky="w")

        self.seg_method = ctk.CTkSegmentedButton(
            card_control,
            values=["Chaînage avant", "Chaînage arrière", "Chaînage mixte (Bonus)"],
            command=self._handle_method_change,
            height=32,
        )
        self.seg_method.grid(row=1, column=1, padx=15, pady=6, sticky="ew")
        self.seg_method.set("Chaînage avant")

        # Ligne 3 : Boutons d'action
        btn_action_frame = ctk.CTkFrame(card_control, fg_color="transparent")
        btn_action_frame.grid(row=2, column=0, columnspan=2, padx=15, pady=(10, 15), sticky="ew")
        btn_action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_step = ctk.CTkButton(
            btn_action_frame,
            text="▶ Étape suivante",
            height=36,
            fg_color=("#0284c7", "#0369a1"),
            hover_color=("#0369a1", "#075985"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_next_step,
        )
        self.btn_step.grid(row=0, column=0, padx=4, sticky="ew")

        self.btn_run_all = ctk.CTkButton(
            btn_action_frame,
            text="⚡ Exécuter tout",
            height=36,
            fg_color="#1f6aa5",
            hover_color="#144870",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_run_all,
        )
        self.btn_run_all.grid(row=0, column=1, padx=4, sticky="ew")

        self.btn_reset = ctk.CTkButton(
            btn_action_frame,
            text="🔄 Réinitialiser",
            height=36,
            fg_color=("gray75", "gray28"),
            text_color=("black", "white"),
            hover_color=("gray65", "gray38"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_reset,
        )
        self.btn_reset.grid(row=0, column=2, padx=4, sticky="ew")

        # 2. Carte inférieure : Trace, Arbre et Explications
        card_results = CardFrame(right_container)
        card_results.grid(row=1, column=0, sticky="nsew")
        card_results.grid_columnconfigure(0, weight=1)
        card_results.grid_rowconfigure(1, weight=1)

        # Bannière de statut de résultat
        self.banner_status = ctk.CTkLabel(
            card_results,
            text="Prêt. Sélectionnez un objectif et lancez l'inférence.",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#e1e4e8", "#21262d"),
            corner_radius=6,
            pady=8,
        )
        self.banner_status.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))

        # Onglets de visualisation des résultats
        self.tabview_results = ctk.CTkTabview(card_results, corner_radius=8)
        self.tabview_results.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        self.tab_trace = self.tabview_results.add("Tableau de Trace (Avant)")
        self.tab_tree = self.tabview_results.add("Arbre de Preuve (Arrière)")
        self.tab_expl = self.tabview_results.add("Explication & Chaîne")

        # Configuration de l'onglet Tableau
        self.tab_trace.grid_columnconfigure(0, weight=1)
        self.tab_trace.grid_rowconfigure(0, weight=1)
        self.trace_table = TraceTableView(self.tab_trace)
        self.trace_table.grid(row=0, column=0, sticky="nsew")

        # Configuration de l'onglet Arbre
        self.tab_tree.grid_columnconfigure(0, weight=1)
        self.tab_tree.grid_rowconfigure(0, weight=1)
        self.proof_tree = ProofTreeView(self.tab_tree)
        self.proof_tree.grid(row=0, column=0, sticky="nsew")

        # Configuration de l'onglet Explication
        self.tab_expl.grid_columnconfigure(0, weight=1)
        self.tab_expl.grid_rowconfigure(0, weight=1)
        self.txt_explanation = ctk.CTkTextbox(
            self.tab_expl,
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=8,
        )
        self.txt_explanation.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.txt_explanation.insert(
            "1.0",
            "Aucune exécution n'a encore eu lieu.\n"
            "Les explications détaillées et la chaîne minimale de règles apparaîtront ici."
        )
        self.txt_explanation.configure(state="disabled")

    # -----------------------------------------------------------------------
    # Gestion des interactions Base de Connaissances
    # -----------------------------------------------------------------------
    def _refresh_kb_view(self) -> None:
        """Met à jour l'affichage des faits et des règles."""
        self.lbl_kb_title.configure(text=f"Système Expert — {self.current_kb.name}")
        self.lbl_kb_desc.configure(text=self.current_kb.description or "Base de connaissances active")

        # 1. Rafraîchir les faits
        for w in self.scroll_facts.winfo_children():
            w.destroy()

        for fact in self.current_kb.facts:
            item_frame = ctk.CTkFrame(self.scroll_facts, fg_color=("#ffffff", "#161b22"), corner_radius=6)
            item_frame.pack(fill="x", pady=2, padx=2)
            item_frame.grid_columnconfigure(0, weight=1)

            lbl_f = ctk.CTkLabel(
                item_frame,
                text=f"• {fact}",
                font=ctk.CTkFont(size=13),
                anchor="w",
                padx=8,
                pady=4,
            )
            lbl_f.grid(row=0, column=0, sticky="w")

            btn_del = ctk.CTkButton(
                item_frame,
                text="✕",
                width=28,
                height=26,
                fg_color="transparent",
                hover_color=("#fee2e2", "#7f1d1d"),
                text_color=("#dc2626", "#ef4444"),
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda f=fact: self._handle_remove_fact(f),
            )
            btn_del.grid(row=0, column=1, padx=4)

        if not self.current_kb.facts:
            lbl_empty = ctk.CTkLabel(
                self.scroll_facts,
                text="Aucun fait initial dans la base.",
                text_color="gray",
                font=ctk.CTkFont(size=12, slant="italic"),
            )
            lbl_empty.pack(pady=15)

        # 2. Rafraîchir les règles
        for w in self.scroll_rules.winfo_children():
            w.destroy()

        for rule in self.current_kb.rules:
            item_frame = ctk.CTkFrame(self.scroll_rules, fg_color=("#ffffff", "#161b22"), corner_radius=6)
            item_frame.pack(fill="x", pady=3, padx=2)
            item_frame.grid_columnconfigure(0, weight=1)

            rule_text = rule.format_french()
            lbl_r = ctk.CTkLabel(
                item_frame,
                text=rule_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                padx=8,
                pady=6,
            )
            lbl_r.grid(row=0, column=0, sticky="w")

            btn_box = ctk.CTkFrame(item_frame, fg_color="transparent")
            btn_box.grid(row=0, column=1, padx=4)

            btn_edit = ctk.CTkButton(
                btn_box,
                text="✏",
                width=28,
                height=26,
                fg_color="transparent",
                hover_color=("gray85", "gray30"),
                text_color=("black", "white"),
                command=lambda r=rule: self._handle_open_edit_rule_dialog(r),
            )
            btn_edit.pack(side="left", padx=2)

            btn_del_r = ctk.CTkButton(
                btn_box,
                text="✕",
                width=28,
                height=26,
                fg_color="transparent",
                hover_color=("#fee2e2", "#7f1d1d"),
                text_color=("#dc2626", "#ef4444"),
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda rid=rule.id: self._handle_remove_rule(rid),
            )
            btn_del_r.pack(side="left", padx=2)

        if not self.current_kb.rules:
            lbl_empty_r = ctk.CTkLabel(
                self.scroll_rules,
                text="Aucune règle définie dans la base.",
                text_color="gray",
                font=ctk.CTkFont(size=12, slant="italic"),
            )
            lbl_empty_r.pack(pady=15)

    def _update_goal_combobox(self) -> None:
        """Met à jour les suggestions de but dans la liste déroulante."""
        symbols = self.current_kb.get_all_conclusions()
        if not symbols:
            symbols = self.current_kb.get_all_known_symbols()
        if not symbols:
            symbols = [""]

        current_val = self.combo_goal.get()
        self.combo_goal.configure(values=symbols)
        if current_val in symbols:
            self.combo_goal.set(current_val)
        elif symbols:
            self.combo_goal.set(symbols[0])

    def _check_goal_status(self) -> None:
        """Vérifie immédiatement si le but saisi est déjà présent dans la base de faits."""
        goal = normalize_fact(self.combo_goal.get())
        if not goal:
            self.lbl_goal_status.configure(
                text="⚡ Mode Saturation (toutes les règles)",
                fg_color=("#fef3c7", "#78350f"),
                text_color=("#b45309", "#fde68a"),
            )
        elif goal in self.initial_kb.facts:
            self.lbl_goal_status.configure(
                text="✔ Déjà présent dans les faits initiaux !",
                fg_color=("#dcfce7", "#14532d"),
                text_color=("#15803d", "#86efac"),
            )
        else:
            self.lbl_goal_status.configure(
                text="🎯 Objectif à démontrer",
                fg_color=("#e0f2fe", "#075985"),
                text_color=("#0369a1", "#7dd3fc"),
            )

    def _handle_add_fact(self) -> None:
        fact = self.entry_new_fact.get().strip()
        if not fact:
            MessageDialog(self, "Champ vide", "Veuillez saisir un libellé de fait non vide.", "warning")
            return
        if self.current_kb.add_fact(fact):
            self.initial_kb.add_fact(fact)
            self.entry_new_fact.delete(0, "end")
            self._refresh_kb_view()
            self._update_goal_combobox()
            self._check_goal_status()
        else:
            MessageDialog(
                self, "Fait existant", f"Le fait « {fact} » existe déjà dans la base.", "info"
            )

    def _handle_remove_fact(self, fact: str) -> None:
        self.current_kb.remove_fact(fact)
        self.initial_kb.remove_fact(fact)
        self._refresh_kb_view()
        self._update_goal_combobox()
        self._check_goal_status()

    def _handle_open_add_rule_dialog(self) -> None:
        def on_save(new_rule: Rule) -> bool:
            if self.current_kb.add_rule(new_rule):
                self.initial_kb.add_rule(new_rule)
                self._refresh_kb_view()
                self._update_goal_combobox()
                return True
            return False

        AddRuleDialog(self, on_save=on_save)

    def _handle_open_edit_rule_dialog(self, rule: Rule) -> None:
        def on_save(updated_rule: Rule) -> bool:
            if self.current_kb.update_rule(rule.id, updated_rule):
                self.initial_kb.update_rule(rule.id, updated_rule)
                self._refresh_kb_view()
                self._update_goal_combobox()
                return True
            return False

        AddRuleDialog(self, on_save=on_save, existing_rule=rule)

    def _handle_remove_rule(self, rule_id: str) -> None:
        self.current_kb.remove_rule(rule_id)
        self.initial_kb.remove_rule(rule_id)
        self._refresh_kb_view()
        self._update_goal_combobox()

    def _handle_preset_change(self, choice: str) -> None:
        preset_files = {
            "Exercice théorique (C)": "kb_exercice.json",
            "Pâtisserie (Les Tartes)": "kb_tarte.json",
            "Géométrie (Triangles)": "kb_triangle.json",
            "Zoologie (Autruche)": "kb_autruche.json",
        }
        filename = preset_files.get(choice)
        if not filename:
            return

        filepath = DATA_DIR / filename
        if filepath.exists():
            try:
                self.initial_kb = KnowledgeBase.load_from_json(filepath)
                self.current_kb = self.initial_kb.clone()
                self._handle_reset()
                self._refresh_kb_view()
                self._update_goal_combobox()
                self._check_goal_status()
            except Exception as e:
                MessageDialog(self, "Erreur de chargement", f"Échec du chargement : {e}", "error")

    def _handle_load_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Charger une base de connaissances JSON",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
            initialdir=str(DATA_DIR),
        )
        if not path:
            return
        try:
            loaded_kb = KnowledgeBase.load_from_json(path)
            self.initial_kb = loaded_kb
            self.current_kb = loaded_kb.clone()
            self._handle_reset()
            self._refresh_kb_view()
            self._update_goal_combobox()
            self._check_goal_status()
            MessageDialog(
                self,
                "Base chargée",
                f"La base « {loaded_kb.name} » a été chargée avec succès ({len(loaded_kb.facts)} faits, {len(loaded_kb.rules)} règles).",
                "success",
            )
        except Exception as e:
            MessageDialog(self, "Erreur de lecture JSON", f"Fichier JSON invalide : {e}", "error")

    def _handle_save_json(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Sauvegarder la base de connaissances en JSON",
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            initialdir=str(DATA_DIR),
            initialfile=f"{self.current_kb.name.lower().replace(' ', '_')}.json",
        )
        if not path:
            return
        try:
            self.current_kb.save_to_json(path)
            MessageDialog(self, "Sauvegarde réussie", f"Base sauvegardée dans :\n{path}", "success")
        except Exception as e:
            MessageDialog(self, "Erreur d'écriture", f"Impossible d'écrire le fichier : {e}", "error")

    # -----------------------------------------------------------------------
    # Exécution du Moteur d'Inférence
    # -----------------------------------------------------------------------
    def _handle_method_change(self, method: str) -> None:
        """Active/désactive le mode pas-à-pas selon la méthode."""
        if "arrière" in method.lower():
            self.btn_step.configure(state="disabled")
            self.tabview_results.set("Arbre de Preuve (Arrière)")
        else:
            self.btn_step.configure(state="normal")
            self.tabview_results.set("Tableau de Trace (Avant)")

    def _handle_reset(self) -> None:
        """Restaure la base de faits initiale et efface les traces."""
        self.current_kb = self.initial_kb.clone()
        self.stepper = None
        self.trace_table.clear()
        self.proof_tree.clear()
        self._set_explanation("Système réinitialisé. Base de faits restaurée à son état d'origine.")
        self.banner_status.configure(
            text="Prêt. Base réinitialisée.",
            fg_color=("#e1e4e8", "#21262d"),
            text_color=("black", "white"),
        )
        self._refresh_kb_view()
        self._check_goal_status()

    def _handle_next_step(self) -> None:
        """Exécute une seule étape du chaînage avant."""
        goal = normalize_fact(self.combo_goal.get())
        self.tabview_results.set("Tableau de Trace (Avant)")

        # Initialiser le stepper si besoin
        if self.stepper is None:
            self.stepper = ForwardStepper(self.current_kb, goal)
            self.trace_table.clear()

            # Vérifier si but déjà présent
            if goal and goal in self.current_kb.facts:
                self.banner_status.configure(
                    text=f"✔ Succès immédiat : « {goal} » est déjà un fait initial !",
                    fg_color=("#dcfce7", "#14532d"),
                    text_color=("#15803d", "#86efac"),
                )
                self._set_explanation(
                    f"Le but « {goal} » est déjà présent dans la base de faits initiale.\n"
                    "Aucune règle n'a besoin d'être déclenchée."
                )
                return

        step = self.stepper.next_step()
        if step is not None:
            is_goal_reached = bool(goal and step.deduction == goal)
            self.trace_table.add_step(step, is_goal_reached=is_goal_reached)

            if is_goal_reached:
                self.banner_status.configure(
                    text=f"✔ But « {goal} » atteint à l'étape #{step.step_num} !",
                    fg_color=("#dcfce7", "#14532d"),
                    text_color=("#15803d", "#86efac"),
                )
            else:
                self.banner_status.configure(
                    text=f"Étape #{step.step_num} : Règle {step.chosen_rule.id} appliquée ➔ + {step.deduction}",
                    fg_color=("#e0f2fe", "#075985"),
                    text_color=("#0369a1", "#7dd3fc"),
                )
            result = self.stepper.get_result()
            self._set_explanation(result.explanation)
        else:
            # Plus aucune règle déclenchable
            result = self.stepper.get_result()
            if goal:
                if result.success:
                    self.banner_status.configure(
                        text=f"✔ But « {goal} » démontré avec succès !",
                        fg_color=("#dcfce7", "#14532d"),
                        text_color=("#15803d", "#86efac"),
                    )
                else:
                    self.banner_status.configure(
                        text=f"✘ But « {goal} » non démontrable (plus de règles applicables).",
                        fg_color=("#fee2e2", "#7f1d1d"),
                        text_color=("#b91c1c", "#fca5a5"),
                    )
            else:
                self.banner_status.configure(
                    text=f"✔ Saturation terminée ({len(result.steps)} étapes au total).",
                    fg_color=("#dcfce7", "#14532d"),
                    text_color=("#15803d", "#86efac"),
                )
            self._set_explanation(result.explanation)

    def _handle_run_all(self) -> None:
        """Exécute l'algorithme choisi en une seule fois."""
        method = self.seg_method.get()
        goal = normalize_fact(self.combo_goal.get())

        if "avant" in method.lower():
            self._run_forward_all(goal)
        elif "arrière" in method.lower():
            self._run_backward_all(goal)
        else:
            self._run_mixed_all(goal)

    def _run_forward_all(self, goal: str) -> None:
        self.tabview_results.set("Tableau de Trace (Avant)")
        self.trace_table.clear()

        result: ForwardResult = forward_chaining(self.current_kb, goal)

        for step in result.steps:
            is_goal_reached = bool(goal and step.deduction == goal)
            self.trace_table.add_step(step, is_goal_reached=is_goal_reached)

        if goal:
            if result.success:
                status_text = (
                    f"✔ Succès : But « {goal} » présent dès l'origine !"
                    if result.goal_already_present
                    else f"✔ Succès : But « {goal} » démontré en {len(result.steps)} étape(s) !"
                )
                self.banner_status.configure(
                    text=status_text,
                    fg_color=("#dcfce7", "#14532d"),
                    text_color=("#15803d", "#86efac"),
                )
            else:
                self.banner_status.configure(
                    text=f"✘ Échec : But « {goal} » non démontrable.",
                    fg_color=("#fee2e2", "#7f1d1d"),
                    text_color=("#b91c1c", "#fca5a5"),
                )
        else:
            self.banner_status.configure(
                text=f"✔ Saturation de la base de faits achevée ({len(result.steps)} déductions).",
                fg_color=("#dcfce7", "#14532d"),
                text_color=("#15803d", "#86efac"),
            )

        self._set_explanation(result.explanation)

    def _run_backward_all(self, goal: str) -> None:
        if not goal:
            MessageDialog(
                self,
                "But requis",
                "Le chaînage arrière nécessite obligatoirement un objectif à démontrer.",
                "warning",
            )
            return

        self.tabview_results.set("Arbre de Preuve (Arrière)")
        result: BackwardResult = backward_chaining(self.current_kb, goal)

        # Affichage de l'arbre
        formatted_tree = result.root_node.to_formatted_tree()
        self.proof_tree.set_content(formatted_tree)

        if result.success:
            self.banner_status.configure(
                text=f"✔ Succès : But « {goal} » démontré par chaînage arrière !",
                fg_color=("#dcfce7", "#14532d"),
                text_color=("#15803d", "#86efac"),
            )
        else:
            self.banner_status.configure(
                text=f"✘ Échec : But « {goal} » non démontrable par chaînage arrière.",
                fg_color=("#fee2e2", "#7f1d1d"),
                text_color=("#b91c1c", "#fca5a5"),
            )

        self._set_explanation(result.explanation)

    def _run_mixed_all(self, goal: str) -> None:
        if not goal:
            MessageDialog(
                self,
                "But requis",
                "Le chaînage mixte nécessite obligatoirement un objectif à démontrer.",
                "warning",
            )
            return

        self.tabview_results.set("Tableau de Trace (Avant)")
        self.trace_table.clear()

        result: MixedResult = mixed_chaining(self.current_kb, goal)

        for step in result.forward_result.steps:
            is_goal = bool(step.deduction == goal)
            self.trace_table.add_step(step, is_goal_reached=is_goal)

        if result.success:
            self.banner_status.configure(
                text=f"✔ Succès (Mixte) : But « {goal} » démontré avec {len(result.relevant_rules)} règles sélectionnées !",
                fg_color=("#dcfce7", "#14532d"),
                text_color=("#15803d", "#86efac"),
            )
        else:
            self.banner_status.configure(
                text=f"✘ Échec (Mixte) : But « {goal} » non démontrable.",
                fg_color=("#fee2e2", "#7f1d1d"),
                text_color=("#b91c1c", "#fca5a5"),
            )

        self._set_explanation(result.explanation)

    def _set_explanation(self, text: str) -> None:
        self.txt_explanation.configure(state="normal")
        self.txt_explanation.delete("1.0", "end")
        self.txt_explanation.insert("1.0", text)
        self.txt_explanation.configure(state="disabled")
