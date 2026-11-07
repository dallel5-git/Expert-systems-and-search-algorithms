"""Fenêtre principale et contrôleur de navigation de l'application desktop.

Gère :
- L'écran d'accueil / Menu principal élégant conforme aux exigences ENSI.
- La navigation fluide entre le Menu Principal, le Module 1 et le Module 2.
- Le basculement de thème Clair / Sombre.
"""

from __future__ import annotations
import sys
from typing import Optional
import customtkinter as ctk

from gui.expert_view import ExpertView
from gui.search_view import SearchView
from gui.widgets import CardFrame


class MenuView(ctk.CTkFrame):
    """Écran d'accueil et Menu Principal de l'application."""

    def __init__(
        self,
        master,
        on_open_expert: callable,
        on_open_search: callable,
        on_quit: callable,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_open_expert = on_open_expert
        self.on_open_search = on_open_search
        self.on_quit = on_quit

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_menu()

    def _build_menu(self) -> None:
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=30)
        center_frame.grid_columnconfigure(0, weight=1)

        # En-tête académique
        header_card = CardFrame(center_frame)
        header_card.grid(row=0, column=0, sticky="ew", pady=(10, 30))
        header_card.grid_columnconfigure(0, weight=1)

        badge_ensi = ctk.CTkLabel(
            header_card,
            text="  ÉCOLE NATIONALE DES SCIENCES DE L'INFORMATIQUE (ENSI) — II2  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#e0f2fe", "#075985"),
            text_color=("#0369a1", "#bae6fd"),
            corner_radius=12,
        )
        badge_ensi.pack(anchor="center", pady=(25, 12))

        title_lbl = ctk.CTkLabel(
            header_card,
            text="Intelligence Artificielle & Machine Learning",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title_lbl.pack(anchor="center", pady=(0, 6))

        sub_lbl = ctk.CTkLabel(
            header_card,
            text="Systèmes experts et algorithmes de recherche",
            font=ctk.CTkFont(size=18, slant="italic"),
            text_color=("#1f6aa5", "#58a6ff"),
        )
        sub_lbl.pack(anchor="center", pady=(0, 25))

        # Conteneur des 3 gros boutons du menu principal
        menu_cards_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        menu_cards_frame.grid(row=1, column=0, sticky="ew", pady=10)
        menu_cards_frame.grid_columnconfigure(0, weight=1)

        options = [
            (
                "1. Systèmes experts",
                "Moteur d'inférence d'ordre 0+ : chaînage avant, chaînage arrière, trace pas-à-pas et gestion de base.",
                "#1f6aa5",
                "#144870",
                self.on_open_expert,
                "Opérationnel (Module 1)",
            ),
            (
                "2. Algorithmes de recherche",
                "Exploration d'espaces d'états dans des graphes orientés et pondérés (recherche aveugle et informée A*).",
                "#1f6aa5",
                "#144870",
                self.on_open_search,
                "Opérationnel (Module 2)",
            ),
            (
                "3. Quitter",
                "Fermer l'application.",
                ("#ef4444", "#991b1b"),
                ("#dc2626", "#7f1d1d"),
                self.on_quit,
                None,
            ),
        ]

        for i, (title, desc, color, hover, cmd, badge_text) in enumerate(options):
            card = CardFrame(menu_cards_frame)
            card.grid(row=i, column=0, sticky="ew", pady=8)
            card.grid_columnconfigure(0, weight=1)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=20, pady=16)
            inner.grid_columnconfigure(0, weight=1)

            t_frame = ctk.CTkFrame(inner, fg_color="transparent")
            t_frame.grid(row=0, column=0, sticky="w")

            t_label = ctk.CTkLabel(
                t_frame,
                text=title,
                font=ctk.CTkFont(size=17, weight="bold"),
                anchor="w",
            )
            t_label.pack(side="left")

            if badge_text:
                is_ready = "Opérationnel" in badge_text
                b_badge = ctk.CTkLabel(
                    t_frame,
                    text=f"  {badge_text}  ",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=("#dcfce7", "#14532d") if is_ready else ("#fef3c7", "#78350f"),
                    text_color=("#15803d", "#86efac") if is_ready else ("#b45309", "#fde68a"),
                    corner_radius=10,
                )
                b_badge.pack(side="left", padx=12)

            d_label = ctk.CTkLabel(
                inner,
                text=desc,
                font=ctk.CTkFont(size=13),
                text_color="gray",
                anchor="w",
            )
            d_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

            btn = ctk.CTkButton(
                inner,
                text="Ouvrir ➜" if "Quitter" not in title else "Quitter ✕",
                width=130,
                height=38,
                fg_color=color,
                hover_color=hover,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=cmd,
            )
            btn.grid(row=0, column=1, rowspan=2, padx=(15, 0), sticky="e")

        # Pied de page
        footer_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        footer_frame.grid(row=2, column=0, sticky="ew", pady=(25, 0))
        footer_frame.grid_columnconfigure(0, weight=1)

        lbl_footer = ctk.CTkLabel(
            footer_frame,
            text="Projet académique — Devoir 1 : Systèmes experts & Algorithmes de recherche",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        lbl_footer.pack(anchor="center")


class App(ctk.CTk):
    """Fenêtre principale de l'application avec contrôleur de vues."""

    def __init__(self):
        super().__init__()

        # Configuration de la fenêtre
        self.title("Systèmes Experts & Algorithmes de Recherche — ENSI IA & ML")
        self.geometry("1280x840")
        self.minsize(1050, 700)

        # Thème par défaut (sombre moderne)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Grille principale
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_app_bar()

        # Conteneur des vues
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Initialisation des vues
        self.view_menu: Optional[MenuView] = None
        self.view_expert: Optional[ExpertView] = None
        self.view_search: Optional[SearchView] = None

        # Affichage initial du menu principal
        self.show_menu()

    def _build_app_bar(self) -> None:
        """Barre d'application discrète avec commutateur de thème."""
        bar = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color=("gray92", "#0d1117"))
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        lbl_app_title = ctk.CTkLabel(
            bar,
            text=" ENSI • IA et Machine Learning",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray",
        )
        lbl_app_title.grid(row=0, column=0, padx=15, sticky="w")

        theme_frame = ctk.CTkFrame(bar, fg_color="transparent")
        theme_frame.grid(row=0, column=1, padx=15, sticky="e")

        ctk.CTkLabel(theme_frame, text="Thème :", font=ctk.CTkFont(size=11), text_color="gray").pack(
            side="left", padx=(0, 6)
        )
        self.switch_theme = ctk.CTkSwitch(
            theme_frame,
            text="Sombre",
            font=ctk.CTkFont(size=11),
            command=self._toggle_theme,
            onvalue="Dark",
            offvalue="Light",
        )
        self.switch_theme.pack(side="left")
        self.switch_theme.select()  # Dark par défaut

    def _toggle_theme(self) -> None:
        mode = "Dark" if self.switch_theme.get() == "Dark" else "Light"
        ctk.set_appearance_mode(mode)
        self.switch_theme.configure(text="Sombre" if mode == "Dark" else "Clair")

    def _clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.grid_forget()

    def show_menu(self) -> None:
        self._clear_container()
        if self.view_menu is None:
            self.view_menu = MenuView(
                self.container,
                on_open_expert=self.show_expert,
                on_open_search=self.show_search,
                on_quit=self.quit_app,
            )
        self.view_menu.grid(row=0, column=0, sticky="nsew")

    def show_expert(self) -> None:
        self._clear_container()
        if self.view_expert is None:
            self.view_expert = ExpertView(
                self.container,
                on_back_to_menu=self.show_menu,
            )
        self.view_expert.grid(row=0, column=0, sticky="nsew")

    def show_search(self) -> None:
        self._clear_container()
        if self.view_search is None:
            self.view_search = SearchView(
                self.container,
                on_back_to_menu=self.show_menu,
            )
        self.view_search.grid(row=0, column=0, sticky="nsew")

    def quit_app(self) -> None:
        self.destroy()
        sys.exit(0)
