"""Suite de tests unitaires et d'intégration pour le moteur de systèmes experts.

Vérifie :
1. Les bases de référence du cours :
   - kb_tarte : abricots = Vrai, cerises = Faux
   - kb_triangle : triangle rectangle = Vrai, triangle isocèle = Vrai
   - kb_autruche : autruche = Vrai
   - kb_exercice : C = Vrai (avant et arrière) avec vérification précise de l'ordre R5, R2, R3, R1
2. Tous les cas particuliers :
   - Base de faits vide
   - Règle sans prémisse (axiome)
   - Règles en doublon
   - But inexistant
   - Boucles cycliques (A -> B, B -> A)
   - But déjà présent dans les faits initiaux
   - Chaînage mixte (bonus)
   - Exécution pas-à-pas (ForwardStepper)
   - Sérialisation / Désérialisation JSON
"""

import json
from pathlib import Path
import pytest

from core.expert_system import (
    Rule,
    KnowledgeBase,
    forward_chaining,
    backward_chaining,
    mixed_chaining,
    ForwardStepper,
    normalize_fact,
)

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Fixtures des bases de connaissances
# ---------------------------------------------------------------------------

@pytest.fixture
def kb_tarte() -> KnowledgeBase:
    return KnowledgeBase.load_from_json(DATA_DIR / "kb_tarte.json")


@pytest.fixture
def kb_triangle() -> KnowledgeBase:
    return KnowledgeBase.load_from_json(DATA_DIR / "kb_triangle.json")


@pytest.fixture
def kb_autruche() -> KnowledgeBase:
    return KnowledgeBase.load_from_json(DATA_DIR / "kb_autruche.json")


@pytest.fixture
def kb_exercice() -> KnowledgeBase:
    return KnowledgeBase.load_from_json(DATA_DIR / "kb_exercice.json")


# ---------------------------------------------------------------------------
# 1. Tests des bases de référence du cours
# ---------------------------------------------------------------------------

class TestBasesDuCours:
    """Validation des exemples officiels du cours d'IA & ML."""

    def test_tarte_abricots_vrai(self, kb_tarte: KnowledgeBase):
        """Tarte aux abricots = Vrai (abricots + farine/beurre/œufs/sel -> pâte -> tarte aux abricots)."""
        # Chaînage avant
        res_fwd = forward_chaining(kb_tarte, "tarte aux abricots")
        assert res_fwd.success is True
        assert "tarte aux abricots" in res_fwd.final_facts
        rule_ids = [r.id for r in res_fwd.applied_rules]
        assert "R1" in rule_ids  # Produit la pâte
        assert "R4" in rule_ids  # Produit la tarte aux abricots

        # Chaînage arrière
        res_bwd = backward_chaining(kb_tarte, "tarte aux abricots")
        assert res_bwd.success is True
        bwd_rule_ids = [r.id for r in res_bwd.applied_rules]
        assert "R4" in bwd_rule_ids
        assert "R1" in bwd_rule_ids

    def test_tarte_cerises_faux(self, kb_tarte: KnowledgeBase):
        """Tarte aux cerises = Faux car 'cerises' n'est pas dans la base de faits."""
        # Chaînage avant
        res_fwd = forward_chaining(kb_tarte, "tarte aux cerises")
        assert res_fwd.success is False
        assert "tarte aux cerises" not in res_fwd.final_facts

        # Chaînage arrière
        res_bwd = backward_chaining(kb_tarte, "tarte aux cerises")
        assert res_bwd.success is False

    def test_triangle_rectangle_vrai(self, kb_triangle: KnowledgeBase):
        """Triangle rectangle = Vrai (ordre vaut 3 -> triangle -> triangle rectangle)."""
        # Chaînage avant
        res_fwd = forward_chaining(kb_triangle, "triangle rectangle")
        assert res_fwd.success is True
        assert "triangle rectangle" in res_fwd.final_facts

        # Chaînage arrière
        res_bwd = backward_chaining(kb_triangle, "triangle rectangle")
        assert res_bwd.success is True

    def test_triangle_isocele_vrai(self, kb_triangle: KnowledgeBase):
        """Triangle isocèle = Vrai."""
        res_fwd = forward_chaining(kb_triangle, "triangle isocèle")
        assert res_fwd.success is True
        res_bwd = backward_chaining(kb_triangle, "triangle isocèle")
        assert res_bwd.success is True

    def test_autruche_vrai(self, kb_autruche: KnowledgeBase):
        """Autruche = Vrai (a des plumes -> oiseau -> autruche)."""
        # Chaînage avant
        res_fwd = forward_chaining(kb_autruche, "autruche")
        assert res_fwd.success is True
        assert "autruche" in res_fwd.final_facts

        # Chaînage arrière
        res_bwd = backward_chaining(kb_autruche, "autruche")
        assert res_bwd.success is True

    def test_exercice_c_vrai_et_ordre_regles(self, kb_exercice: KnowledgeBase):
        """Exercice du cours : Dérivation de C avec faits E, F.

        Vérification exacte de l'ordre d'application en chaînage avant :
        Étape 1 : R5 (E ET F -> D)
        Étape 2 : R2 (F ET D -> A)
        Étape 3 : R3 (D ET E -> B)
        Étape 4 : R1 (A ET B -> C) -> BUT ATTEINT
        """
        # Chaînage avant
        res_fwd = forward_chaining(kb_exercice, "C")
        assert res_fwd.success is True
        assert len(res_fwd.steps) == 4

        # Vérification précise des étapes
        # Étape 1
        assert res_fwd.steps[0].chosen_rule.id == "R5"
        assert res_fwd.steps[0].deduction == "D"
        # Étape 2 (R2 et R3 sont déclenchables, première déclenchable = R2)
        triggerable_step2 = [r.id for r in res_fwd.steps[1].triggerable_rules]
        assert "R2" in triggerable_step2 and "R3" in triggerable_step2
        assert res_fwd.steps[1].chosen_rule.id == "R2"
        assert res_fwd.steps[1].deduction == "A"
        # Étape 3
        assert res_fwd.steps[2].chosen_rule.id == "R3"
        assert res_fwd.steps[2].deduction == "B"
        # Étape 4 (R1 et R4 sont déclenchables, première déclenchable = R1)
        triggerable_step4 = [r.id for r in res_fwd.steps[3].triggerable_rules]
        assert "R1" in triggerable_step4 and "R4" in triggerable_step4
        assert res_fwd.steps[3].chosen_rule.id == "R1"
        assert res_fwd.steps[3].deduction == "C"

        # Chaînage arrière
        res_bwd = backward_chaining(kb_exercice, "C")
        assert res_bwd.success is True
        assert res_bwd.root_node.status is True


# ---------------------------------------------------------------------------
# 2. Tests des cas particuliers et limites
# ---------------------------------------------------------------------------

class TestCasParticuliers:
    """Gestion des cas limites pour garantir une robustesse absolue."""

    def test_base_faits_vide(self):
        """Base de faits vide sans règles applicables."""
        kb = KnowledgeBase(
            name="Base vide",
            facts=[],
            rules=[Rule("R1", ["A"], "B")],
        )
        res_fwd = forward_chaining(kb, "B")
        assert res_fwd.success is False
        assert len(res_fwd.steps) == 0

        res_bwd = backward_chaining(kb, "B")
        assert res_bwd.success is False

    def test_regle_sans_premisse_axiome(self):
        """Règle sans prémisse (SI vrai ALORS conclusion)."""
        kb = KnowledgeBase(
            name="Axiome",
            facts=[],
            rules=[Rule("R1", [], "Soleil")],
        )
        # Chaînage avant
        res_fwd = forward_chaining(kb, "Soleil")
        assert res_fwd.success is True
        assert "Soleil" in res_fwd.final_facts
        assert len(res_fwd.steps) == 1
        assert res_fwd.steps[0].chosen_rule.id == "R1"

        # Chaînage arrière
        res_bwd = backward_chaining(kb, "Soleil")
        assert res_bwd.success is True
        assert "Soleil" in [r.conclusion for r in res_bwd.applied_rules]

    def test_regles_en_doublon_ou_conflits(self):
        """Vérifie la détection et la gestion propre des règles en doublon."""
        kb = KnowledgeBase(name="Test doublons")
        r1 = Rule("R1", ["A"], "B")
        r1_bis = Rule("R1", ["A"], "B")  # Même ID

        assert kb.add_rule(r1) is True
        assert kb.add_rule(r1_bis) is False  # Refusé car ID existant
        assert len(kb.rules) == 1

    def test_but_inexistant(self, kb_exercice: KnowledgeBase):
        """Recherche d'un symbole totalement absent de la base."""
        res_fwd = forward_chaining(kb_exercice, "INEXISTANT_XYZ")
        assert res_fwd.success is False

        res_bwd = backward_chaining(kb_exercice, "INEXISTANT_XYZ")
        assert res_bwd.success is False
        assert "INEXISTANT_XYZ" in res_bwd.explanation

    def test_boucle_regles_detection_cycle(self):
        """Protection contre les boucles récursives en chaînage arrière (A -> B et B -> A)."""
        kb = KnowledgeBase(
            name="Base cyclique",
            facts=["A"],
            rules=[
                Rule("R1", ["A"], "B"),
                Rule("R2", ["B"], "A"),
                Rule("R3", ["B"], "C"),
            ],
        )
        # Chaînage avant termine sans boucle
        res_fwd = forward_chaining(kb, "C")
        assert res_fwd.success is True
        assert "C" in res_fwd.final_facts

        # Chaînage arrière : sans faits initiaux pour forcer le cycle A -> B -> A
        kb_sans_faits = KnowledgeBase(
            name="Base cyclique sans faits",
            facts=[],
            rules=[
                Rule("R1", ["A"], "B"),
                Rule("R2", ["B"], "A"),
            ],
        )
        # Ne doit pas lever de RecursionError et doit détecter le cycle
        res_bwd = backward_chaining(kb_sans_faits, "A")
        assert res_bwd.success is False
        tree_text = res_bwd.root_node.to_formatted_tree()
        assert "Boucle cyclique détectée" in tree_text

    def test_but_deja_dans_faits_initiaux(self, kb_tarte: KnowledgeBase):
        """Si le but est déjà présent dans la base de faits initiale."""
        res_fwd = forward_chaining(kb_tarte, "pommes")
        assert res_fwd.success is True
        assert res_fwd.goal_already_present is True
        assert len(res_fwd.steps) == 0
        assert "déjà présent" in res_fwd.explanation

        res_bwd = backward_chaining(kb_tarte, "pommes")
        assert res_bwd.success is True
        assert res_bwd.root_node.reason == "Fait initial"

    def test_champs_vides_et_normalisation(self):
        """Vérifie la robustesse face aux espaces et entrées vides."""
        assert normalize_fact("   pommes   ") == "pommes"
        assert normalize_fact("") == ""
        assert normalize_fact("   ") == ""

        kb = KnowledgeBase(name="Test Espaces", facts=["  A  ", "B  "])
        assert "A" in kb.facts
        assert "B" in kb.facts

        # Ajout de fait vide ignoré
        assert kb.add_fact("   ") is False


# ---------------------------------------------------------------------------
# 3. Tests des fonctionnalités interactives et avancées
# ---------------------------------------------------------------------------

class TestFonctionnalitesAvancees:
    """Tests du chaînage pas-à-pas (ForwardStepper), mixte et sérialisation."""

    def test_forward_stepper_interactif(self, kb_exercice: KnowledgeBase):
        """Simule les clics sur 'Étape suivante'."""
        stepper = ForwardStepper(kb_exercice, "C")
        assert not stepper.is_done()

        # Étape 1
        s1 = stepper.next_step()
        assert s1 is not None
        assert s1.chosen_rule.id == "R5"
        assert not stepper.is_done()

        # Étape 2
        s2 = stepper.next_step()
        assert s2 is not None
        assert s2.chosen_rule.id == "R2"

        # Étape 3
        s3 = stepper.next_step()
        assert s3 is not None
        assert s3.chosen_rule.id == "R3"

        # Étape 4 (But C atteint)
        s4 = stepper.next_step()
        assert s4 is not None
        assert s4.chosen_rule.id == "R1"
        assert stepper.is_done()

        # Étape supplémentaire : retourne None
        assert stepper.next_step() is None

        # Résultat final cohérent
        result = stepper.get_result()
        assert result.success is True
        assert result.goal == "C"
        assert len(result.steps) == 4

    def test_chainage_mixte_bonus(self, kb_exercice: KnowledgeBase):
        """Test de la méthode de chaînage mixte avec élagage."""
        res_mix = mixed_chaining(kb_exercice, "C")
        assert res_mix.success is True
        assert res_mix.goal == "C"
        # R4 (B ET D -> F) n'est pas nécessaire pour déduire C
        relevant_ids = [r.id for r in res_mix.relevant_rules]
        assert "R1" in relevant_ids
        assert "R2" in relevant_ids
        assert "R3" in relevant_ids
        assert "R5" in relevant_ids

    def test_sauvegarde_et_chargement_json(self, tmp_path: Path):
        """Vérifie l'export et import JSON fidèle."""
        kb = KnowledgeBase(
            name="Base Test",
            description="Description test",
            facts=["f1", "f2"],
            rules=[
                Rule("R1", ["f1"], "c1"),
                Rule("R2", ["f2", "c1"], "c2"),
            ],
        )
        file_path = tmp_path / "test_kb.json"
        kb.save_to_json(file_path)

        loaded = KnowledgeBase.load_from_json(file_path)
        assert loaded.name == kb.name
        assert loaded.description == kb.description
        assert loaded.facts == kb.facts
        assert len(loaded.rules) == 2
        assert loaded.rules[0].id == "R1"
        assert loaded.rules[0].premises == ["f1"]
        assert loaded.rules[0].conclusion == "c1"
