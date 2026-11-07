"""Module du Système Expert (Moteur d'inférence, Base de faits, Base de règles).

Ce module implémente de manière totalement indépendante de l'interface graphique :
- La représentation des règles et de la base de connaissances.
- Le chaînage avant déterministe avec et sans but (saturation) et trace pas-à-pas.
- Le chaînage arrière récursif dirigé par le but avec sous-buts, backtracking,
  détection de boucles et arbre de preuve visuel.
- Le chaînage mixte (stratégie bidirectionnelle / réduction de recherche).
- La gestion des cas limites (faits vides, règles sans prémisse, boucles, etc.).
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


def normalize_fact(fact: str) -> str:
    """Normalise une chaîne de fait (supprime espaces superflus)."""
    return fact.strip() if fact else ""


@dataclass
class Rule:
    """Représentation d'une règle : SI prémisses (conjonction ET) ALORS conclusion."""
    id: str
    premises: List[str]
    conclusion: str

    def __post_init__(self) -> None:
        self.id = self.id.strip()
        self.premises = [normalize_fact(p) for p in self.premises if normalize_fact(p)]
        self.conclusion = normalize_fact(self.conclusion)

    def is_axiom(self) -> bool:
        """Retourne True si la règle n'a aucune prémisse (fait inconditionnel)."""
        return len(self.premises) == 0

    def is_triggerable(self, facts: Set[str]) -> bool:
        """Vérifie si toutes les prémisses de la règle sont satisfaites par l'ensemble des faits."""
        if not self.premises:
            return True
        return all(p in facts for p in self.premises)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la règle en dictionnaire sérialisable."""
        return {
            "id": self.id,
            "premises": self.premises,
            "conclusion": self.conclusion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Rule:
        """Crée une règle depuis un dictionnaire."""
        return cls(
            id=str(data.get("id", "")).strip(),
            premises=list(data.get("premises", [])),
            conclusion=str(data.get("conclusion", "")).strip(),
        )

    def format_french(self) -> str:
        """Affichage standardisé : 'R1 : SI c1 ET c2 ALORS conclusion'."""
        if not self.premises:
            return f"{self.id} : SI <vrai> ALORS {self.conclusion}"
        prems = " ET ".join(self.premises)
        return f"{self.id} : SI {prems} ALORS {self.conclusion}"

    def __str__(self) -> str:
        return self.format_french()


@dataclass
class KnowledgeBase:
    """Base de connaissances regroupant la base de faits et la base de règles."""
    name: str = "Base de connaissances"
    description: str = ""
    facts: List[str] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Nettoyage et unicité en conservant l'ordre
        clean_facts: List[str] = []
        for f in self.facts:
            norm = normalize_fact(f)
            if norm and norm not in clean_facts:
                clean_facts.append(norm)
        self.facts = clean_facts

    def add_fact(self, fact: str) -> bool:
        """Ajoute un fait. Retourne True si le fait a été ajouté, False s'il existait déjà ou était vide."""
        norm = normalize_fact(fact)
        if not norm or norm in self.facts:
            return False
        self.facts.append(norm)
        return True

    def remove_fact(self, fact: str) -> bool:
        """Supprime un fait de la base."""
        norm = normalize_fact(fact)
        if norm in self.facts:
            self.facts.remove(norm)
            return True
        return False

    def add_rule(self, rule: Rule) -> bool:
        """Ajoute une règle. Retourne True si ajoutée, False si l'ID ou la règle exacte existe déjà."""
        if not rule.id or not rule.conclusion:
            return False
        if any(r.id == rule.id for r in self.rules):
            return False
        self.rules.append(rule)
        return True

    def update_rule(self, rule_id: str, new_rule: Rule) -> bool:
        """Met à jour une règle existante."""
        for i, r in enumerate(self.rules):
            if r.id == rule_id:
                # Vérifier si le nouvel ID existe déjà chez une autre règle
                if new_rule.id != rule_id and any(other.id == new_rule.id for other in self.rules):
                    return False
                self.rules[i] = new_rule
                return True
        return False

    def remove_rule(self, rule_id: str) -> bool:
        """Supprime une règle par son identifiant."""
        for i, r in enumerate(self.rules):
            if r.id == rule_id:
                del self.rules[i]
                return True
        return False

    def clone(self) -> KnowledgeBase:
        """Crée une copie indépendante en profondeur de la base de connaissances."""
        cloned_rules = [
            Rule(id=r.id, premises=list(r.premises), conclusion=r.conclusion)
            for r in self.rules
        ]
        return KnowledgeBase(
            name=self.name,
            description=self.description,
            facts=list(self.facts),
            rules=cloned_rules,
        )

    def get_all_conclusions(self) -> List[str]:
        """Retourne toutes les conclusions possibles définies dans les règles (uniques)."""
        seen = set()
        res = []
        for r in self.rules:
            if r.conclusion not in seen:
                seen.add(r.conclusion)
                res.append(r.conclusion)
        return res

    def get_all_known_symbols(self) -> List[str]:
        """Retourne l'ensemble de tous les symboles (faits, prémisses et conclusions)."""
        seen = set(self.facts)
        res = list(self.facts)
        for r in self.rules:
            for p in r.premises:
                if p not in seen:
                    seen.add(p)
                    res.append(p)
            if r.conclusion not in seen:
                seen.add(r.conclusion)
                res.append(r.conclusion)
        return res

    def to_dict(self) -> Dict[str, Any]:
        """Exporte la base sous forme de dictionnaire JSON-compatible."""
        return {
            "name": self.name,
            "description": self.description,
            "facts": self.facts,
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KnowledgeBase:
        """Instancie une base depuis un dictionnaire."""
        name = str(data.get("name", "Base sans titre"))
        description = str(data.get("description", ""))
        raw_facts = data.get("facts", [])
        raw_rules = data.get("rules", [])
        rules = [Rule.from_dict(r) for r in raw_rules if isinstance(r, dict)]
        return cls(name=name, description=description, facts=list(raw_facts), rules=rules)

    def save_to_json(self, file_path: str | Path) -> None:
        """Sauvegarde la base dans un fichier JSON."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> KnowledgeBase:
        """Charge une base depuis un fichier JSON."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Fichier introuvable : {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Structures de traces et résultats
# ---------------------------------------------------------------------------

@dataclass
class ForwardStep:
    """Représente une étape élémentaire de déduction en chaînage avant."""
    step_num: int
    triggerable_rules: List[Rule]
    chosen_rule: Rule
    deduction: str
    facts_snapshot: List[str]


@dataclass
class ForwardResult:
    """Résultat complet d'une exécution de chaînage avant."""
    success: bool
    goal: Optional[str]
    goal_already_present: bool
    steps: List[ForwardStep]
    initial_facts: List[str]
    final_facts: List[str]
    applied_rules: List[Rule]
    contributing_rules: List[Rule]
    explanation: str


@dataclass
class BackwardNode:
    """Nœud hiérarchique de l'arbre de preuve en chaînage arrière."""
    goal: str
    status: bool  # True si prouvé, False sinon
    reason: str  # Description (ex: 'Fait initial', 'Prouvé via R1', 'Cycle détecté', etc.)
    rule: Optional[Rule] = None
    children: List[BackwardNode] = field(default_factory=list)
    depth: int = 0

    def to_formatted_tree(self, prefix: str = "", is_tail: bool = True) -> str:
        """Génère une vue textuelle indentée et élégante avec les symboles ✔ / ✘."""
        mark = "✔" if self.status else "✘"
        rule_desc = f" [{self.rule.id}]" if self.rule else ""
        lines = []

        node_repr = f"🎯 But : « {self.goal} » [{mark}] {rule_desc} ({self.reason})"
        lines.append(f"{prefix}{'└── ' if is_tail else '├── '}{node_repr}")

        child_prefix = prefix + ("    " if is_tail else "│   ")
        for i, child in enumerate(self.children):
            is_last = (i == len(self.children) - 1)
            lines.append(child.to_formatted_tree(child_prefix, is_last))

        return "\n".join(lines)


@dataclass
class BackwardResult:
    """Résultat complet d'une exécution de chaînage arrière."""
    success: bool
    goal: str
    root_node: BackwardNode
    applied_rules: List[Rule]
    explanation: str


@dataclass
class MixedResult:
    """Résultat du chaînage mixte (stratégie bidirectionnelle / heuristique de recherche)."""
    success: bool
    goal: str
    relevant_rules: List[Rule]
    forward_result: ForwardResult
    explanation: str


# ---------------------------------------------------------------------------
# Algorithme 1 : Chaînage avant (Forward Chaining)
# ---------------------------------------------------------------------------

def forward_chaining(
    kb: KnowledgeBase,
    goal: Optional[str] = None,
) -> ForwardResult:
    """Exécute l'algorithme de chaînage avant déterministe.

    Algorithme du cours :
    - Si le but est dans la base de faits initiale : succès immédiat.
    - Tant qu'il existe des règles déclenchables parmi les règles non encore appliquées :
      - Trouver toutes les règles déclenchables (prémisses ⊆ faits courants).
      - Sélectionner la première règle dans l'ordre de la base (priorité R1, R2, ...).
      - L'appliquer : ajouter sa conclusion aux faits, marquer la règle comme appliquée.
      - Si la conclusion est égale au but cherché : succès immédiat !
    - Si aucune règle n'est déclenchable :
      - Si but spécifié : échec (but non atteint).
      - Si pas de but (saturation) : arrêt normal.
    """
    initial_facts = list(kb.facts)
    norm_goal = normalize_fact(goal) if goal else None

    # Cas 1 : Le but est déjà dans la base de faits
    if norm_goal and norm_goal in initial_facts:
        return ForwardResult(
            success=True,
            goal=norm_goal,
            goal_already_present=True,
            steps=[],
            initial_facts=initial_facts,
            final_facts=initial_facts,
            applied_rules=[],
            contributing_rules=[],
            explanation=(
                f"Le but « {norm_goal} » est déjà présent dans la base de faits initiale.\n"
                "Aucune inférence supplémentaire n'a été nécessaire."
            ),
        )

    facts = list(initial_facts)
    facts_set = set(facts)
    unapplied_rules = list(kb.rules)

    steps: List[ForwardStep] = []
    applied_rules: List[Rule] = []
    goal_found = False

    while True:
        # Trouver toutes les règles déclenchables
        triggerable: List[Rule] = []
        for r in unapplied_rules:
            if r.is_triggerable(facts_set):
                triggerable.append(r)

        if not triggerable:
            break

        # Sélection déterministe : première règle déclenchable
        chosen = triggerable[0]
        unapplied_rules.remove(chosen)
        applied_rules.append(chosen)

        deduction = chosen.conclusion
        if deduction not in facts_set:
            facts.append(deduction)
            facts_set.add(deduction)

        step = ForwardStep(
            step_num=len(steps) + 1,
            triggerable_rules=list(triggerable),
            chosen_rule=chosen,
            deduction=deduction,
            facts_snapshot=list(facts),
        )
        steps.append(step)

        if norm_goal and deduction == norm_goal:
            goal_found = True
            break

    # Déterminer la réussite
    if norm_goal:
        success = goal_found
    else:
        success = True  # En saturation, l'algorithme atteint toujours son terme avec succès

    # Extraction des règles ayant directement ou indirectement contribué au but
    contributing_rules: List[Rule] = []
    if norm_goal and success:
        contributing_rules = _extract_contributing_rules(norm_goal, applied_rules, set(initial_facts))
    elif not norm_goal:
        contributing_rules = list(applied_rules)

    # Rédaction de l'explication
    if norm_goal:
        if success:
            chain_str = " ➔ ".join([r.id for r in contributing_rules]) if contributing_rules else "Aucune"
            expl = (
                f"✔ But « {norm_goal} » démontré avec succès en {len(steps)} étape(s) !\n"
                f"Chaîne de règles contributives : {chain_str}\n"
                f"Faits finaux obtenus ({len(facts)}) : {', '.join(facts)}"
            )
        else:
            expl = (
                f"✘ But « {norm_goal} » non démontrable.\n"
                f"L'inférence s'est arrêtée après {len(steps)} étape(s) sans pouvoir déduire le but.\n"
                f"Faits saturés ({len(facts)}) : {', '.join(facts)}"
            )
    else:
        expl = (
            f"✔ Saturation de la base de faits terminée avec succès en {len(steps)} étape(s).\n"
            f"{len(applied_rules)} règle(s) appliquée(s).\n"
            f"Base de faits saturée ({len(facts)}) : {', '.join(facts)}"
        )

    return ForwardResult(
        success=success,
        goal=norm_goal,
        goal_already_present=False,
        steps=steps,
        initial_facts=initial_facts,
        final_facts=facts,
        applied_rules=applied_rules,
        contributing_rules=contributing_rules,
        explanation=expl,
    )


def _extract_contributing_rules(
    goal: str, applied_rules: List[Rule], initial_facts: Set[str]
) -> List[Rule]:
    """Extrait la sous-chaîne minimale de règles ayant contribué à démontrer le but."""
    needed_facts: Set[str] = {goal}
    contributing: List[Rule] = []

    # Parcours inverse des règles appliquées
    for rule in reversed(applied_rules):
        if rule.conclusion in needed_facts:
            contributing.append(rule)
            needed_facts.remove(rule.conclusion)
            for p in rule.premises:
                if p not in initial_facts:
                    needed_facts.add(p)

    contributing.reverse()
    return contributing


class ForwardStepper:
    """Générateur d'étapes pour l'exécution interactive pas-à-pas du chaînage avant."""

    def __init__(self, kb: KnowledgeBase, goal: Optional[str] = None):
        self.kb = kb
        self.goal = normalize_fact(goal) if goal else None
        self.initial_facts = list(kb.facts)
        self.facts = list(self.initial_facts)
        self.facts_set = set(self.facts)
        self.unapplied_rules = list(kb.rules)
        self.steps: List[ForwardStep] = []
        self.applied_rules: List[Rule] = []
        self._done = False
        self._success = False

        if self.goal and self.goal in self.facts_set:
            self._done = True
            self._success = True

    def is_done(self) -> bool:
        return self._done

    def next_step(self) -> Optional[ForwardStep]:
        """Exécute une seule étape d'inférence et retourne l'objet ForwardStep correspondant."""
        if self._done:
            return None

        triggerable: List[Rule] = []
        for r in self.unapplied_rules:
            if r.is_triggerable(self.facts_set):
                triggerable.append(r)

        if not triggerable:
            self._done = True
            self._success = (self.goal in self.facts_set) if self.goal else True
            return None

        chosen = triggerable[0]
        self.unapplied_rules.remove(chosen)
        self.applied_rules.append(chosen)

        deduction = chosen.conclusion
        if deduction not in self.facts_set:
            self.facts.append(deduction)
            self.facts_set.add(deduction)

        step = ForwardStep(
            step_num=len(self.steps) + 1,
            triggerable_rules=list(triggerable),
            chosen_rule=chosen,
            deduction=deduction,
            facts_snapshot=list(self.facts),
        )
        self.steps.append(step)

        if self.goal and deduction == self.goal:
            self._done = True
            self._success = True

        return step

    def get_result(self) -> ForwardResult:
        """Retourne l'état complet actuel sous forme de ForwardResult."""
        goal_already = (self.goal is not None) and (self.goal in self.initial_facts)
        contributing: List[Rule] = []
        if self.goal and self._success:
            contributing = _extract_contributing_rules(self.goal, self.applied_rules, set(self.initial_facts))
        elif not self.goal:
            contributing = list(self.applied_rules)

        if self.goal:
            if self._success:
                chain = " ➔ ".join([r.id for r in contributing]) if contributing else "Fait initial"
                expl = (
                    f"✔ But « {self.goal} » atteint avec succès en {len(self.steps)} étape(s) !\n"
                    f"Règles contributives : {chain}\n"
                    f"Faits actuels ({len(self.facts)}) : {', '.join(self.facts)}"
                )
            elif self._done:
                expl = (
                    f"✘ But « {self.goal} » non démontrable.\n"
                    f"Faits saturés ({len(self.facts)}) : {', '.join(self.facts)}"
                )
            else:
                expl = f"En cours d'exécution pas-à-pas (Étape {len(self.steps)})..."
        else:
            expl = (
                f"Saturation ({'Terminée' if self._done else 'En cours'}) : {len(self.steps)} étape(s).\n"
                f"Faits actuels ({len(self.facts)}) : {', '.join(self.facts)}"
            )

        return ForwardResult(
            success=self._success,
            goal=self.goal,
            goal_already_present=goal_already,
            steps=list(self.steps),
            initial_facts=self.initial_facts,
            final_facts=list(self.facts),
            applied_rules=list(self.applied_rules),
            contributing_rules=contributing,
            explanation=expl,
        )


# ---------------------------------------------------------------------------
# Algorithme 2 : Chaînage arrière (Backward Chaining)
# ---------------------------------------------------------------------------

def backward_chaining(kb: KnowledgeBase, goal: str) -> BackwardResult:
    """Exécute l'algorithme de chaînage arrière récursif dirigé par le but.

    Caractéristiques :
    - Recherche guidée par le but à démontrer.
    - Décomposition en sous-buts (prémisses des règles candidates).
    - Backtracking : si une règle échoue à prouver toutes ses prémisses, tester une autre règle.
    - Détection de boucles : ensemble des buts en cours de preuve sur la branche courante.
    - Production d'un arbre de preuve explicatif complet avec statuts ✔ / ✘.
    """
    norm_goal = normalize_fact(goal)
    if not norm_goal:
        root = BackwardNode(goal="<vide>", status=False, reason="Objectif vide non spécifié", depth=0)
        return BackwardResult(
            success=False,
            goal="",
            root_node=root,
            applied_rules=[],
            explanation="Erreur : Aucun objectif spécifié pour le chaînage arrière.",
        )

    facts_set = set(kb.facts)
    known_proven_facts = set(facts_set)
    rules_applied_in_order: List[Rule] = []

    def prove_goal(current_goal: str, call_stack: Set[str], depth: int) -> BackwardNode:
        # Cas A : Le but est un fait initial ou déjà prouvé antérieurement
        if current_goal in known_proven_facts:
            reason = "Fait initial" if current_goal in facts_set else "Fait déjà déduit"
            return BackwardNode(
                goal=current_goal,
                status=True,
                reason=reason,
                rule=None,
                depth=depth,
            )

        # Cas B : Protection contre les boucles infinies (cycle sur la branche courante)
        if current_goal in call_stack:
            return BackwardNode(
                goal=current_goal,
                status=False,
                reason="Boucle cyclique détectée (but déjà en cours de preuve)",
                rule=None,
                depth=depth,
            )

        # Cas C : Chercher les règles candidates ayant current_goal comme conclusion
        candidate_rules = [r for r in kb.rules if r.conclusion == current_goal]

        if not candidate_rules:
            return BackwardNode(
                goal=current_goal,
                status=False,
                reason="Aucune règle ne conclut sur ce but",
                rule=None,
                depth=depth,
            )

        next_stack = call_stack | {current_goal}
        node = BackwardNode(
            goal=current_goal,
            status=False,
            reason="Échec de toutes les règles candidates",
            depth=depth,
        )

        # Exploration avec Backtracking des règles candidates
        for rule in candidate_rules:
            rule_success = True
            child_nodes: List[BackwardNode] = []

            # Si règle sans prémisse (axiome)
            if rule.is_axiom():
                rule_node = BackwardNode(
                    goal=current_goal,
                    status=True,
                    reason=f"Prouvé par axiome {rule.id}",
                    rule=rule,
                    children=[],
                    depth=depth + 1,
                )
                node.children.append(rule_node)
                node.status = True
                node.rule = rule
                node.reason = f"Démontré via {rule.id}"
                known_proven_facts.add(current_goal)
                if rule not in rules_applied_in_order:
                    rules_applied_in_order.append(rule)
                return node

            for premise in rule.premises:
                child = prove_goal(premise, next_stack, depth + 1)
                child_nodes.append(child)
                if not child.status:
                    rule_success = False
                    # Échec de cette prémisse -> on arrête d'évaluer les suivantes pour cette règle
                    break

            # Conserver la tentative de règle pour la trace
            rule_node = BackwardNode(
                goal=current_goal,
                status=rule_success,
                reason=f"Application de {rule.id} : {'Succès' if rule_success else 'Prémisses non démontrées'}",
                rule=rule,
                children=child_nodes,
                depth=depth + 1,
            )
            node.children.append(rule_node)

            if rule_success:
                node.status = True
                node.rule = rule
                node.reason = f"Démontré via {rule.id}"
                known_proven_facts.add(current_goal)
                if rule not in rules_applied_in_order:
                    rules_applied_in_order.append(rule)
                return node  # Succès trouvé, fin de la recherche pour ce but

        # Toutes les règles candidates ont échoué
        node.status = False
        return node

    root_tree = prove_goal(norm_goal, set(), 0)

    # Formulation de l'explication finale
    if root_tree.status:
        chain_str = " ➔ ".join([r.id for r in rules_applied_in_order]) if rules_applied_in_order else "Fait initial"
        expl = (
            f"✔ But « {norm_goal} » démontré avec succès par chaînage arrière !\n"
            f"Chaîne de règles validées : {chain_str}\n"
            f"Consultez l'arbre des sous-buts ci-dessous pour le détail du raisonnement."
        )
    else:
        expl = (
            f"✘ But non démontrable : impossible d'établir « {norm_goal} ».\n"
            f"Toutes les voies de décomposition en sous-buts ont échoué."
        )

    return BackwardResult(
        success=root_tree.status,
        goal=norm_goal,
        root_node=root_tree,
        applied_rules=rules_applied_in_order,
        explanation=expl,
    )


# ---------------------------------------------------------------------------
# Algorithme 3 : Chaînage mixte (Bonus)
# ---------------------------------------------------------------------------

def mixed_chaining(kb: KnowledgeBase, goal: str) -> MixedResult:
    """Exécute un chaînage mixte bidirectionnel :

    1. Phase arrière : élagage ciblé. On identifie uniquement les règles qui sont
       connectées au but (dépendances ascendantes du graphe de règles).
    2. Phase avant restreinte : on applique le chaînage avant uniquement sur ce
       sous-ensemble pertinent pour éviter toute déduction inutile.
    """
    norm_goal = normalize_fact(goal)
    if not norm_goal:
        return MixedResult(
            success=False,
            goal="",
            relevant_rules=[],
            forward_result=forward_chaining(kb, ""),
            explanation="Erreur : Aucun but spécifié.",
        )

    # 1. Sélection arrière des règles pertinentes
    relevant_rules: List[Rule] = []
    needed_symbols = {norm_goal}
    visited_symbols = set()

    while needed_symbols:
        sym = needed_symbols.pop()
        visited_symbols.add(sym)
        for r in kb.rules:
            if r.conclusion == sym:
                if r not in relevant_rules:
                    relevant_rules.append(r)
                for p in r.premises:
                    if p not in visited_symbols:
                        needed_symbols.add(p)

    # Conserver l'ordre original de la base pour le déterminisme
    filtered_rules = [r for r in kb.rules if r in relevant_rules]

    # Créer une sous-base avec uniquement les règles pertinentes
    sub_kb = KnowledgeBase(
        name=f"Sous-base ciblée pour '{norm_goal}'",
        description="Règles sélectionnées par analyse de dépendance descendante",
        facts=list(kb.facts),
        rules=filtered_rules,
    )

    # 2. Exécution du chaînage avant sur le sous-espace réduit
    fwd_res = forward_chaining(sub_kb, norm_goal)

    total_rules = len(kb.rules)
    retained_rules = len(filtered_rules)
    economy = total_rules - retained_rules

    if fwd_res.success:
        expl = (
            f"✔ Chaînage mixte réussi pour « {norm_goal} » !\n"
            f"Optimisation : {retained_rules}/{total_rules} règle(s) retenue(s) ({economy} règle(s) élaguée(s)).\n"
            f"{fwd_res.explanation}"
        )
    else:
        expl = (
            f"✘ Chaînage mixte : But « {norm_goal} » non démontrable.\n"
            f"Sous-ensemble analysé : {retained_rules} règle(s).\n"
            f"{fwd_res.explanation}"
        )

    return MixedResult(
        success=fwd_res.success,
        goal=norm_goal,
        relevant_rules=filtered_rules,
        forward_result=fwd_res,
        explanation=expl,
    )
