"""Composants graphiques réutilisables pour l'interface CustomTkinter.

Inclut :
- CardFrame : conteneur de type carte avec bordure et coins arrondis.
- TraceTableView : tableau de trace du chaînage avant avec colonnes structurées.
- ProofTreeView : affichage visuel coloré de l'arbre de preuve en chaînage arrière.
- Dialogues modaux personnalisés (AddRuleDialog, MessageDialog).
"""

from __future__ import annotations
import tkinter as tk
from typing import Callable, List, Optional
import customtkinter as ctk

from core.expert_system import ForwardStep, Rule


class CardFrame(ctk.CTkFrame):
    """Conteneur stylisé avec coins arrondis et bordure élégante."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", ("#d0d7de", "#30363d"))
        kwargs.setdefault("fg_color", ("#f6f8fa", "#161b22"))
        super().__init__(master, **kwargs)


class MessageDialog(ctk.CTkToplevel):
    """Boîte de dialogue modale moderne et soignée (ne bloque jamais l'application)."""

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        icon_type: str = "info",  # 'info', 'error', 'success', 'warning'
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        colors = {
            "info": ("#1f6aa5", "ℹ"),
            "success": ("#2e7d32", "✔"),
            "warning": ("#d97706", "⚠"),
            "error": ("#c62828", "✖"),
        }
        color, icon = colors.get(icon_type, colors["info"])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # En-tête
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        icon_label = ctk.CTkLabel(
            header_frame,
            text=icon,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color,
            width=36,
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        title_label.pack(side="left", fill="x", expand=True)

        # Corps du message
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=390,
            justify="left",
            anchor="nw",
        )
        msg_label.grid(row=1, column=0, padx=25, pady=5, sticky="nsew")

        # Bouton Fermer
        btn_close = ctk.CTkButton(
            self,
            text="Compris",
            width=100,
            command=self.destroy,
            fg_color=color,
            hover_color=color,
        )
        btn_close.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="e")

        self.update_idletasks()
        # Centrage par rapport au parent
        try:
            x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
            y = parent.winfo_y() + (parent.winfo_height() - 220) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass


class AddRuleDialog(ctk.CTkToplevel):
    """Dialogue modal pour ajouter ou modifier une règle."""

    def __init__(
        self,
        parent,
        on_save: Callable[[Rule], bool],
        existing_rule: Optional[Rule] = None,
    ):
        super().__init__(parent)
        self.on_save = on_save
        self.existing_rule = existing_rule

        is_edit = existing_rule is not None
        self.title("Modifier la règle" if is_edit else "Ajouter une règle")
        self.geometry("500x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        # Titre
        title_lbl = ctk.CTkLabel(
            self,
            text="Modification de règle" if is_edit else "Nouvelle règle SI... ALORS...",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        desc_lbl = ctk.CTkLabel(
            self,
            text="Séparez plusieurs prémisses par des virgules ou le mot 'ET'.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        desc_lbl.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # Formulaire
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.grid(row=2, column=0, padx=20, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        # Identifiant
        ctk.CTkLabel(form_frame, text="Identifiant :", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=5, pady=8, sticky="w"
        )
        self.entry_id = ctk.CTkEntry(form_frame, placeholder_text="ex: R1, R2...")
        self.entry_id.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        # Prémisses
        ctk.CTkLabel(form_frame, text="Prémisses (SI) :", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=1, column=0, padx=5, pady=8, sticky="w"
        )
        self.entry_premises = ctk.CTkEntry(
            form_frame, placeholder_text="ex: farine, beurre, œufs (ou laisser vide pour un axiome)"
        )
        self.entry_premises.grid(row=1, column=1, padx=5, pady=8, sticky="ew")

        # Conclusion
        ctk.CTkLabel(form_frame, text="Conclusion (ALORS) :", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, padx=5, pady=8, sticky="w"
        )
        self.entry_conclusion = ctk.CTkEntry(form_frame, placeholder_text="ex: pâte")
        self.entry_conclusion.grid(row=2, column=1, padx=5, pady=8, sticky="ew")

        # Message d'erreur dynamique
        self.lbl_error = ctk.CTkLabel(self, text="", text_color="#ef5350", font=ctk.CTkFont(size=12))
        self.lbl_error.grid(row=3, column=0, padx=20, pady=5, sticky="w")

        # Préremplissage si modification
        if existing_rule:
            self.entry_id.insert(0, existing_rule.id)
            self.entry_premises.insert(0, ", ".join(existing_rule.premises))
            self.entry_conclusion.insert(0, existing_rule.conclusion)

        # Boutons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=20, pady=(15, 20), sticky="e")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Annuler",
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray65", "gray40"),
            command=self.destroy,
            width=100,
        )
        btn_cancel.pack(side="left", padx=5)

        btn_submit = ctk.CTkButton(
            btn_frame,
            text="Enregistrer",
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=self._handle_submit,
            width=110,
        )
        btn_submit.pack(side="left", padx=5)

    def _handle_submit(self) -> None:
        rid = self.entry_id.get().strip()
        raw_prems = self.entry_premises.get().strip()
        conclusion = self.entry_conclusion.get().strip()

        if not rid:
            self.lbl_error.configure(text="L'identifiant de la règle est obligatoire.")
            return
        if not conclusion:
            self.lbl_error.configure(text="La conclusion de la règle est obligatoire.")
            return

        # Parsing des prémisses (supporte virgules ou 'ET')
        premises = []
        if raw_prems:
            # Remplace ' ET ' insensible à la casse par des virgules
            normalized = raw_prems.replace(" et ", ",").replace(" ET ", ",").replace(" Et ", ",")
            for part in normalized.split(","):
                cleaned = part.strip()
                if cleaned:
                    premises.append(cleaned)

        rule = Rule(id=rid, premises=premises, conclusion=conclusion)
        success = self.on_save(rule)
        if success:
            self.destroy()
        else:
            self.lbl_error.configure(
                text=f"Impossible d'enregistrer : l'identifiant '{rid}' est peut-être déjà utilisé."
            )


class TraceTableView(ctk.CTkScrollableFrame):
    """Tableau de bord de trace du chaînage avant affichant les étapes sous forme de table."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=0, minsize=50)   # N°
        self.grid_columnconfigure(1, weight=1, minsize=140)  # Règles déclenchables
        self.grid_columnconfigure(2, weight=1, minsize=170)  # Règle choisie
        self.grid_columnconfigure(3, weight=1, minsize=110)  # Déduction
        self.grid_columnconfigure(4, weight=2, minsize=200)  # Faits mis à jour

        self._row_count = 0
        self._build_header()

    def _build_header(self) -> None:
        headers = [
            ("N°", 0),
            ("Règles déclenchables", 1),
            ("Règle choisie", 2),
            ("Déduction", 3),
            ("Base de faits mise à jour", 4),
        ]
        header_frame = ctk.CTkFrame(self, fg_color=("#e1e4e8", "#21262d"), corner_radius=6)
        header_frame.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 6), padx=2)
        header_frame.grid_columnconfigure(0, weight=0, minsize=50)
        header_frame.grid_columnconfigure(1, weight=1, minsize=140)
        header_frame.grid_columnconfigure(2, weight=1, minsize=170)
        header_frame.grid_columnconfigure(3, weight=1, minsize=110)
        header_frame.grid_columnconfigure(4, weight=2, minsize=200)

        for text, col in headers:
            lbl = ctk.CTkLabel(
                header_frame,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="center" if col == 0 else "w",
                padx=6,
                pady=6,
            )
            lbl.grid(row=0, column=col, sticky="ew")

        self._row_count = 1

    def clear(self) -> None:
        """Efface toutes les lignes du tableau."""
        for widget in self.winfo_children():
            widget.destroy()
        self._build_header()

    def add_step(self, step: ForwardStep, is_goal_reached: bool = False) -> None:
        """Ajoute une étape dans la table."""
        bg_color = ("#e8f5e9", "#1b3320") if is_goal_reached else (
            ("#f6f8fa", "#161b22") if self._row_count % 2 == 1 else ("#ffffff", "#0d1117")
        )

        row_frame = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=4)
        row_frame.grid(row=self._row_count, column=0, columnspan=5, sticky="ew", pady=2, padx=2)
        row_frame.grid_columnconfigure(0, weight=0, minsize=50)
        row_frame.grid_columnconfigure(1, weight=1, minsize=140)
        row_frame.grid_columnconfigure(2, weight=1, minsize=170)
        row_frame.grid_columnconfigure(3, weight=1, minsize=110)
        row_frame.grid_columnconfigure(4, weight=2, minsize=200)

        # 0. N°
        lbl_num = ctk.CTkLabel(
            row_frame,
            text=f"#{step.step_num}",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="center",
            padx=4,
        )
        lbl_num.grid(row=0, column=0, sticky="ew")

        # 1. Règles déclenchables
        triggerable_str = ", ".join([r.id for r in step.triggerable_rules])
        lbl_trig = ctk.CTkLabel(
            row_frame,
            text=f"[{triggerable_str}]",
            font=ctk.CTkFont(size=12),
            text_color=("#0969da", "#58a6ff"),
            anchor="w",
            padx=6,
        )
        lbl_trig.grid(row=0, column=1, sticky="ew")

        # 2. Règle choisie
        chosen_str = f"{step.chosen_rule.id} : SI {' ET '.join(step.chosen_rule.premises) if step.chosen_rule.premises else '<vrai>'} ALORS {step.chosen_rule.conclusion}"
        lbl_chosen = ctk.CTkLabel(
            row_frame,
            text=chosen_str,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
            padx=6,
        )
        lbl_chosen.grid(row=0, column=2, sticky="ew")

        # 3. Déduction
        deduct_text = f"+ {step.deduction}"
        if is_goal_reached:
            deduct_text += " 🎯 (BUT)"
        lbl_deduct = ctk.CTkLabel(
            row_frame,
            text=deduct_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1a7f37", "#3fb950") if is_goal_reached else ("#24292f", "#c9d1d9"),
            anchor="w",
            padx=6,
        )
        lbl_deduct.grid(row=0, column=3, sticky="ew")

        # 4. Faits mis à jour
        facts_preview = "{" + ", ".join(step.facts_snapshot) + "}"
        lbl_facts = ctk.CTkLabel(
            row_frame,
            text=facts_preview,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
            padx=6,
        )
        lbl_facts.grid(row=0, column=4, sticky="ew")

        self._row_count += 1


class ProofTreeView(ctk.CTkFrame):
    """Afficheur visuel pour l'arbre de preuve en chaînage arrière."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.text_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="monospace", size=13),
            wrap="none",
            corner_radius=8,
            border_width=1,
            border_color=("gray80", "gray30"),
        )
        self.text_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def set_content(self, text: str) -> None:
        """Remplit le visualiseur avec l'arbre textuel."""
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", text if text else "Aucun arbre de preuve à afficher.")
        self.text_box.configure(state="disabled")

    def clear(self) -> None:
        self.set_content("Prêt. Choisissez un but et lancez le chaînage arrière pour afficher l'arbre.")
