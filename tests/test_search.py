"""Suite de tests unitaires et d'intégration pour le Module 2 (Algorithmes de recherche).

Vérifie :
1. Graphe de référence du cours :
   - BFS : chemin avec le moins d'arcs (G -> C -> K, 2 arcs, coût 25)
   - UCS : chemin de coût minimal (G -> D -> E -> F -> K, coût 14)
   - A* : chemin de coût minimal (G -> D -> E -> F -> K, coût 14)
   - Greedy Best-First : trouve le but
   - RBFS : trouve le but de coût optimal
   - SMA* : respecte la mémoire bornée
   - IDS : complétude
   - DLS : échec dû à la limite quand la limite est trop faible (L=1)
   - Vérification de l'admissibilité et de la consistance de l'heuristique
2. Tous les cas particuliers sur l'ensemble des algorithmes :
   - Graphe vide
   - Initial == But (coût 0, chemin = [initial])
   - But inaccessible
   - Sommet isolé
   - Cycles (A -> B -> A)
   - Arcs avec mise à jour / parallèles
   - Coûts négatifs ou nuls (refus avec exception / message clair)
   - Sérialisation et désérialisation JSON
"""

import pytest
from pathlib import Path

from core.search_algorithms import (
    Edge,
    Graph,
    run_search_algorithm,
    verify_admissibility,
    verify_consistency,
    compute_true_optimal_costs,
    compare_all_algorithms,
    bfs_search,
    ucs_search,
    dfs_search,
    dls_search,
    ids_search,
    greedy_best_first_search,
    a_star_search,
    sma_star_search,
    rbfs_search,
)

DATA_DIR = Path(__file__).parent.parent / "data"

ALL_ALGORITHMS = ["BFS", "UCS", "DFS", "DLS", "IDS", "Best-First", "A*", "SMA*", "RBFS"]


@pytest.fixture
def graphe_cours() -> Graph:
    """Charge le graphe officiel du cours depuis le JSON."""
    return Graph.load_from_json(DATA_DIR / "graphe_cours.json")


# ---------------------------------------------------------------------------
# 1. Tests sur le Graphe de référence du cours
# ---------------------------------------------------------------------------

class TestGrapheDuCours:
    """Validation des propriétés d'optimalité et de complétude sur le graphe du cours."""

    def test_bfs_chemin_moins_d_arcs(self, graphe_cours: Graph):
        """BFS doit trouver le chemin avec le minimum d'arcs : G -> C -> K (2 arcs)."""
        res = run_search_algorithm(graphe_cours, "BFS", start="G", goal="K")
        assert res.status == "TROUVE"
        assert res.path == ["G", "C", "K"]
        assert len(res.path) - 1 == 2
        assert res.total_cost == 25.0

    def test_ucs_chemin_cout_minimal(self, graphe_cours: Graph):
        """UCS doit trouver le chemin de coût minimal : G -> D -> E -> F -> K (coût 14.0)."""
        res = run_search_algorithm(graphe_cours, "UCS", start="G", goal="K")
        assert res.status == "TROUVE"
        assert res.path == ["G", "D", "E", "F", "K"]
        assert res.total_cost == 14.0

    def test_astar_chemin_cout_minimal(self, graphe_cours: Graph):
        """A* avec heuristique admissible doit trouver le coût minimal (14.0)."""
        res = run_search_algorithm(graphe_cours, "A*", start="G", goal="K")
        assert res.status == "TROUVE"
        assert res.path == ["G", "D", "E", "F", "K"]
        assert res.total_cost == 14.0

    def test_best_first_trouve_but(self, graphe_cours: Graph):
        """Recherche gloutonne / Best-First doit trouver le but."""
        res = run_search_algorithm(graphe_cours, "Best-First", start="G", goal="K")
        assert res.status == "TROUVE"
        assert res.path[0] == "G"
        assert res.path[-1] == "K"

    def test_rbfs_chemin_optimal(self, graphe_cours: Graph):
        """RBFS doit trouver le chemin optimal (coût 14.0)."""
        res = run_search_algorithm(graphe_cours, "RBFS", start="G", goal="K")
        assert res.status == "TROUVE"
        assert res.path == ["G", "D", "E", "F", "K"]
        assert res.total_cost == 14.0

    def test_sma_star_avec_memoire_suffisante(self, graphe_cours: Graph):
        """SMA* avec capacité suffisante doit trouver le chemin optimal."""
        res = run_search_algorithm(graphe_cours, "SMA*", start="G", goal="K", max_memory=10)
        assert res.status == "TROUVE"
        assert res.path == ["G", "D", "E", "F", "K"]
        assert res.total_cost == 14.0

    def test_ids_complet(self, graphe_cours: Graph):
        """IDS doit trouver le but avec une profondeur maximale suffisante."""
        res = run_search_algorithm(graphe_cours, "IDS", start="G", goal="K", max_depth_limit=6)
        assert res.status == "TROUVE"
        assert res.path[0] == "G"
        assert res.path[-1] == "K"

    def test_dls_echec_limite_trop_faible(self, graphe_cours: Graph):
        """DLS avec limite=1 doit échouer avec 'ECHEC_LIMITE' car K est à profondeur >= 2."""
        res = run_search_algorithm(graphe_cours, "DLS", start="G", goal="K", depth_limit=1)
        assert res.status == "ECHEC_LIMITE"
        assert "limite de profondeur" in res.message.lower()

    def test_dls_succes_avec_limite_suffisante(self, graphe_cours: Graph):
        """DLS avec limite=2 peut atteindre K via G -> C -> K."""
        res = run_search_algorithm(graphe_cours, "DLS", start="G", goal="K", depth_limit=2)
        assert res.status == "TROUVE"
        assert res.path == ["G", "C", "K"]

    def test_verification_heuristique_graphe_cours(self, graphe_cours: Graph):
        """Vérifie que l'heuristique de graphe_cours est admissible et consistante."""
        admiss = verify_admissibility(graphe_cours, "K")
        assert admiss["is_admissible"] is True
        assert len(admiss["violations"]) == 0

        consist = verify_consistency(graphe_cours, "K")
        assert consist["is_consistent"] is True
        assert len(consist["violations"]) == 0


# ---------------------------------------------------------------------------
# 2. Tests de l'Analyseur d'Heuristique (Cas de non-respect)
# ---------------------------------------------------------------------------

class TestAnalyseHeuristique:
    """Vérification de la détection de violations d'admissibilité et de consistance."""

    def test_detection_non_admissible(self, graphe_cours: Graph):
        """Si h(D) = 25 alors que le coût réel optimal est 9 -> non admissible !"""
        g_clone = graphe_cours.clone()
        g_clone.set_heuristic("D", 25.0)

        res = verify_admissibility(g_clone, "K")
        assert res["is_admissible"] is False
        assert any("D" in v for v in res["violations"])

    def test_detection_non_consistante(self, graphe_cours: Graph):
        """Si h(E) = 15 et arc E->F de coût 2 avec h(F)=4 : h(E) > c + h(F) (15 > 2 + 4 = 6) -> non consistant !"""
        g_clone = graphe_cours.clone()
        g_clone.set_heuristic("E", 15.0)

        res = verify_consistency(g_clone, "K")
        assert res["is_consistent"] is False
        assert any("E ➔ F" in v for v in res["violations"])


# ---------------------------------------------------------------------------
# 3. Tests des Cas Particuliers sur TOUS les algorithmes
# ---------------------------------------------------------------------------

class TestCasParticuliers:
    """Validation de la robustesse absolue de chaque algorithme face aux cas limites."""

    @pytest.mark.parametrize("algo", ALL_ALGORITHMS)
    def test_graphe_vide(self, algo: str):
        """Graphe sans sommets : doit retourner AUCUN_CHEMIN sans exception."""
        empty_graph = Graph(name="Graphe vide")
        res = run_search_algorithm(empty_graph, algo, start="A", goal="B")
        assert res.status == "AUCUN_CHEMIN"
        assert res.path == []

    @pytest.mark.parametrize("algo", ALL_ALGORITHMS)
    def test_depart_egal_but(self, algo: str):
        """Si start == goal : coût 0, chemin = [start], statut TROUVE."""
        graph = Graph(name="Un seul sommet", nodes=["A"], start_node="A", goal_node="A")
        res = run_search_algorithm(graph, algo, start="A", goal="A")
        assert res.status == "TROUVE"
        assert res.path == ["A"]
        assert res.total_cost == 0.0

    @pytest.mark.parametrize("algo", ALL_ALGORITHMS)
    def test_but_inaccessible(self, algo: str):
        """Graphe avec but complètement déconnecté du départ."""
        graph = Graph(
            name="Déconnecté",
            nodes=["A", "B", "C"],
            edges=[Edge("A", "B", 1.0)],  # C est isolé
            heuristics={"A": 0.0, "B": 0.0, "C": 0.0},
            start_node="A",
            goal_node="C",
        )
        res = run_search_algorithm(graph, algo, start="A", goal="C", max_depth_limit=3, depth_limit=3)
        assert res.status == "AUCUN_CHEMIN"
        assert res.path == []

    @pytest.mark.parametrize("algo", ALL_ALGORITHMS)
    def test_sommet_isole(self, algo: str):
        """Départ isolé sans aucun arc sortant."""
        graph = Graph(
            name="Isolé",
            nodes=["Isole", "Autre"],
            edges=[],
            heuristics={"Isole": 5.0, "Autre": 0.0},
            start_node="Isole",
            goal_node="Autre",
        )
        res = run_search_algorithm(graph, algo, start="Isole", goal="Autre", max_depth_limit=2, depth_limit=2)
        assert res.status == "AUCUN_CHEMIN"
        assert res.path == []

    @pytest.mark.parametrize("algo", ALL_ALGORITHMS)
    def test_graphe_avec_cycles(self, algo: str):
        """Cycle A -> B -> A et chemin vers le but C."""
        graph = Graph(
            name="Cycle",
            nodes=["A", "B", "C"],
            edges=[
                Edge("A", "B", 2.0),
                Edge("B", "A", 2.0),
                Edge("B", "C", 3.0),
            ],
            heuristics={"A": 4.0, "B": 3.0, "C": 0.0},
            start_node="A",
            goal_node="C",
        )
        res = run_search_algorithm(graph, algo, start="A", goal="C", max_depth_limit=5, depth_limit=5)
        assert res.status == "TROUVE"
        assert res.path == ["A", "B", "C"]
        assert res.total_cost == 5.0

    def test_couts_negatifs_ou_nuls_rejetes(self):
        """Validation stricte : les coûts <= 0 doivent être formellement rejetés."""
        graph = Graph(name="Test Coûts", nodes=["A", "B"])

        # Coût nul (0)
        with pytest.raises(ValueError) as exc1:
            Edge("A", "B", 0.0)
        assert "strictement positif" in str(exc1.value)

        with pytest.raises(ValueError) as exc2:
            graph.add_edge("A", "B", 0.0)
        assert "strictement positif" in str(exc2.value)

        # Coût négatif (< 0)
        with pytest.raises(ValueError) as exc3:
            Edge("A", "B", -5.0)
        assert "strictement positif" in str(exc3.value)

        with pytest.raises(ValueError) as exc4:
            graph.add_edge("A", "B", -3.5)
        assert "strictement positif" in str(exc4.value)

    def test_arcs_paralleles_mise_a_jour(self):
        """L'ajout d'un arc déjà existant entre deux nœuds met à jour son coût proprement."""
        graph = Graph(name="Mise à jour arc", nodes=["A", "B"])
        graph.add_edge("A", "B", 10.0)
        assert len(graph.edges) == 1
        assert graph.edges[0].cost == 10.0

        # Remplacement avec un nouveau coût
        graph.add_edge("A", "B", 4.0)
        assert len(graph.edges) == 1
        assert graph.edges[0].cost == 4.0

    def test_heuristique_par_defaut_si_manquante(self):
        """Si un sommet n'a pas de valeur h explicite, 0.0 est utilisé par défaut."""
        graph = Graph(
            name="Heuristique manquante",
            nodes=["A", "B"],
            edges=[Edge("A", "B", 5.0)],
            heuristics={},  # Vide
            start_node="A",
            goal_node="B",
        )
        res = run_search_algorithm(graph, "A*", start="A", goal="B")
        assert res.status == "TROUVE"
        assert res.path == ["A", "B"]
        assert res.total_cost == 5.0

    def test_serialisation_json(self, tmp_path: Path, graphe_cours: Graph):
        """Vérifie la sauvegarde et le rechargement JSON sans perte."""
        file_path = tmp_path / "saved_graph.json"
        graphe_cours.save_to_json(file_path)

        loaded = Graph.load_from_json(file_path)
        assert loaded.name == graphe_cours.name
        assert loaded.nodes == graphe_cours.nodes
        assert len(loaded.edges) == len(graphe_cours.edges)
        assert loaded.heuristics == graphe_cours.heuristics
        assert loaded.start_node == graphe_cours.start_node
        assert loaded.goal_node == graphe_cours.goal_node


# ---------------------------------------------------------------------------
# 4. Tests du Comparateur d'Algorithmes (Bonus Étape 3)
# ---------------------------------------------------------------------------

class TestComparaison:
    """Validation de la fonction de benchmark global compare_all_algorithms."""

    def test_comparaison_graphe_cours(self, graphe_cours: Graph):
        """Vérifie l'exécution groupée de tous les algorithmes sur graphe_cours."""
        comp = compare_all_algorithms(graphe_cours, start="G", goal="K")
        assert comp["success"] is True
        assert comp["start"] == "G"
        assert comp["goal"] == "K"
        assert comp["min_cost"] == 14.0
        assert comp["best_algo"] in ["UCS", "A*", "SMA*", "RBFS"]
        assert len(comp["results"]) == 9  # 5 non informés + 4 informés

        # Vérification des propriétés des lignes du tableau comparatif
        results_map = {r["algorithm"]: r for r in comp["results"]}

        # BFS : trouvé mais non optimal en coût (25 vs 14)
        assert results_map["BFS"]["found"] is True
        assert results_map["BFS"]["cost"] == 25.0
        assert results_map["BFS"]["is_optimal"] is False

        # UCS : optimal en coût (14.0)
        assert results_map["UCS"]["found"] is True
        assert results_map["UCS"]["cost"] == 14.0
        assert results_map["UCS"]["is_optimal"] is True

        # A* : optimal en coût (14.0)
        assert results_map["A*"]["found"] is True
        assert results_map["A*"]["cost"] == 14.0
        assert results_map["A*"]["is_optimal"] is True

        # Temps mesuré strictement positif
        for row in comp["results"]:
            assert row["time_ms"] >= 0.0

    def test_comparaison_sans_heuristique(self, graphe_cours: Graph):
        """Sans heuristiques complètes, seuls les algorithmes non informés sont lancés."""
        g_no_h = graphe_cours.clone()
        g_no_h.heuristics = {}  # Aucune heuristique
        comp = compare_all_algorithms(g_no_h, start="G", goal="K")
        assert comp["success"] is True
        assert comp["has_full_heuristics"] is False
        assert len(comp["results"]) == 5  # Uniquement BFS, UCS, DFS, DLS, IDS

    def test_comparaison_sommets_invalides(self, graphe_cours: Graph):
        """Sommet initial ou but inexistant -> échec propre sans crash."""
        comp = compare_all_algorithms(graphe_cours, start="INEXISTANT", goal="K")
        assert comp["success"] is False
        assert "invalide" in comp["error"]
