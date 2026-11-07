"""Module des Algorithmes de recherche dans les espaces d'états (Module 2).

Fournit de manière totalement indépendante de l'interface graphique :
- La classe Graph (graphe orienté, pondéré, heuristiques, validation stricte).
- Les générateurs d'étapes (yield) pour l'exécution pas-à-pas de tous les algorithmes.
- Algorithmes non informés : BFS, UCS, DFS, DLS, IDS.
- Algorithmes informés : Best-First (Gloutonne), A*, SMA*, RBFS.
- Vérification formelle de l'admissibilité et de la consistance de l'heuristique.
- Table des propriétés théoriques du cours (temps, espace, complétude, optimalité).
"""

from __future__ import annotations
import heapq
import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Structures fondamentales du Graphe
# ---------------------------------------------------------------------------

@dataclass
class Edge:
    """Arc orienté et pondéré : from_node -> to_node avec un coût strictement positif."""
    from_node: str
    to_node: str
    cost: float

    def __post_init__(self) -> None:
        self.from_node = self.from_node.strip()
        self.to_node = self.to_node.strip()
        self.cost = float(self.cost)
        if self.cost <= 0:
            raise ValueError(f"Le coût d'un arc doit être strictement positif (> 0). Reçu : {self.cost}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "cost": self.cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Edge:
        return cls(
            from_node=str(data["from"]),
            to_node=str(data["to"]),
            cost=float(data["cost"]),
        )


@dataclass
class Graph:
    """Graphe orienté, pondéré, avec heuristiques et positions 2D."""
    name: str = "Graphe"
    description: str = ""
    nodes: List[str] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    heuristics: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    start_node: Optional[str] = None
    goal_node: Optional[str] = None

    def __post_init__(self) -> None:
        # Nettoyage et unicité des sommets en préservant l'ordre
        clean_nodes: List[str] = []
        for n in self.nodes:
            s = n.strip()
            if s and s not in clean_nodes:
                clean_nodes.append(s)
        self.nodes = clean_nodes

        if self.start_node:
            self.start_node = self.start_node.strip()
        if self.goal_node:
            self.goal_node = self.goal_node.strip()

    def add_node(
        self,
        node: str,
        pos: Optional[Tuple[float, float]] = None,
        h: float = 0.0,
    ) -> bool:
        """Ajoute un sommet. Retourne True si ajouté, False si existant ou vide."""
        s = node.strip()
        if not s or s in self.nodes:
            return False
        self.nodes.append(s)
        if pos is not None:
            self.positions[s] = (float(pos[0]), float(pos[1]))
        else:
            self.positions[s] = (0.0, 0.0)
        self.heuristics[s] = max(0.0, float(h))
        return True

    def remove_node(self, node: str) -> bool:
        """Supprime un sommet ainsi que tous les arcs incidents."""
        s = node.strip()
        if s not in self.nodes:
            return False
        self.nodes.remove(s)
        self.edges = [e for e in self.edges if e.from_node != s and e.to_node != s]
        self.heuristics.pop(s, None)
        self.positions.pop(s, None)
        if self.start_node == s:
            self.start_node = None
        if self.goal_node == s:
            self.goal_node = None
        return True

    def add_edge(self, from_node: str, to_node: str, cost: float) -> bool:
        """Ajoute ou met à jour un arc orienté avec un coût strictement positif."""
        u = from_node.strip()
        v = to_node.strip()
        if not u or not v:
            raise ValueError("Les sommets de départ et d'arrivée ne peuvent pas être vides.")
        if u not in self.nodes or v not in self.nodes:
            raise ValueError(f"Sommet inconnu dans l'arc {u} -> {v}.")
        if cost <= 0:
            raise ValueError(f"Le coût de l'arc doit être strictement positif (> 0). Reçu : {cost}")

        # Si un arc existe déjà entre u et v, on met à jour son coût
        for e in self.edges:
            if e.from_node == u and e.to_node == v:
                e.cost = float(cost)
                return True

        self.edges.append(Edge(from_node=u, to_node=v, cost=cost))
        return True

    def remove_edge(self, from_node: str, to_node: str) -> bool:
        """Supprime un arc orienté."""
        u = from_node.strip()
        v = to_node.strip()
        for i, e in enumerate(self.edges):
            if e.from_node == u and e.to_node == v:
                del self.edges[i]
                return True
        return False

    def get_neighbors(self, node: str) -> List[Tuple[str, float]]:
        """Retourne les voisins sortants triés par ordre alphabétique déterministe [(dest, coût)]."""
        s = node.strip()
        neighbors = [(e.to_node, e.cost) for e in self.edges if e.from_node == s]
        neighbors.sort(key=lambda item: item[0])
        return neighbors

    def set_heuristic(self, node: str, h: float) -> None:
        """Définit la valeur heuristique d'un sommet."""
        s = node.strip()
        if s in self.nodes:
            if h < 0:
                raise ValueError("Une valeur heuristique ne peut pas être négative.")
            self.heuristics[s] = float(h)

    def validate(self) -> Tuple[bool, List[str]]:
        """Valide la cohérence du graphe. Retourne (valide, liste_erreurs)."""
        errors = []
        if not self.nodes:
            errors.append("Le graphe ne contient aucun sommet.")
        if self.start_node and self.start_node not in self.nodes:
            errors.append(f"Le sommet initial '{self.start_node}' n'existe pas dans le graphe.")
        if self.goal_node and self.goal_node not in self.nodes:
            errors.append(f"Le sommet but '{self.goal_node}' n'existe pas dans le graphe.")
        for e in self.edges:
            if e.from_node not in self.nodes:
                errors.append(f"Arc avec départ invalide : {e.from_node}")
            if e.to_node not in self.nodes:
                errors.append(f"Arc avec arrivée invalide : {e.to_node}")
            if e.cost <= 0:
                errors.append(f"Arc {e.from_node}->{e.to_node} avec coût non positif : {e.cost}")
        return (len(errors) == 0, errors)

    def clone(self) -> Graph:
        """Copie en profondeur indépendante du graphe."""
        return Graph(
            name=self.name,
            description=self.description,
            nodes=list(self.nodes),
            edges=[Edge(e.from_node, e.to_node, e.cost) for e in self.edges],
            heuristics=dict(self.heuristics),
            positions={k: (v[0], v[1]) for k, v in self.positions.items()},
            start_node=self.start_node,
            goal_node=self.goal_node,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "start_node": self.start_node,
            "goal_node": self.goal_node,
            "nodes": self.nodes,
            "positions": {k: [v[0], v[1]] for k, v in self.positions.items()},
            "edges": [e.to_dict() for e in self.edges],
            "heuristics": self.heuristics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Graph:
        nodes = list(data.get("nodes", []))
        raw_edges = data.get("edges", [])
        edges = [Edge.from_dict(e) for e in raw_edges]
        raw_pos = data.get("positions", {})
        positions = {k: (float(v[0]), float(v[1])) for k, v in raw_pos.items()}
        heuristics = {k: float(v) for k, v in data.get("heuristics", {}).items()}
        return cls(
            name=str(data.get("name", "Graphe")),
            description=str(data.get("description", "")),
            nodes=nodes,
            edges=edges,
            heuristics=heuristics,
            positions=positions,
            start_node=data.get("start_node"),
            goal_node=data.get("goal_node"),
        )

    def save_to_json(self, file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> Graph:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Fichier introuvable : {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Structures de recherche (Nœuds, Étapes, Résultats)
# ---------------------------------------------------------------------------

@dataclass
class SearchNode:
    """Nœud dans l'arbre d'exploration de recherche."""
    state: str
    parent: Optional[SearchNode] = None
    action_cost: float = 0.0
    g: float = 0.0
    h: float = 0.0
    f: float = 0.0
    depth: int = 0

    def get_path(self) -> List[str]:
        """Reconstitue la chaîne des états depuis la racine jusqu'à ce nœud."""
        path = []
        curr: Optional[SearchNode] = self
        while curr is not None:
            path.append(curr.state)
            curr = curr.parent
        path.reverse()
        return path


@dataclass
class FrontierItem:
    """Représentation sérialisable d'un élément présent dans la frontière."""
    state: str
    g: float
    h: float
    f: float
    depth: int
    parent: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "g": round(self.g, 2),
            "h": round(self.h, 2),
            "f": round(self.f, 2),
            "depth": self.depth,
            "parent": self.parent,
        }


@dataclass
class SearchStep:
    """État instantané d'une étape de recherche pour la trace et la visualisation."""
    step_num: int
    current_node: Optional[str]
    visited: List[str]
    frontier: List[Dict[str, Any]]
    action_desc: str
    path: Optional[List[str]] = None
    total_cost: float = 0.0
    is_final: bool = False
    status: str = "EN_COURS"  # "EN_COURS", "TROUVE", "AUCUN_CHEMIN", "ECHEC_LIMITE"


@dataclass
class SearchResult:
    """Bilan complet d'une exécution de recherche."""
    algorithm: str
    status: str  # "TROUVE", "AUCUN_CHEMIN", "ECHEC_LIMITE"
    path: List[str]
    total_cost: float
    nodes_expanded: int
    max_depth: int
    steps: List[SearchStep]
    message: str


# ---------------------------------------------------------------------------
# Propriétés théoriques des algorithmes (Cours ENSI)
# ---------------------------------------------------------------------------

ALGORITHM_PROPERTIES: Dict[str, Dict[str, str]] = {
    "BFS": {
        "nom": "Parcours en largeur (BFS)",
        "temps": "O(b^d)",
        "espace": "O(b^d)",
        "completude": "Oui (si b est fini)",
        "optimalite": "Oui si les coûts des arcs sont tous identiques (1), sinon non optimal en coût.",
        "strategie": "Frontière FIFO. Développe les nœuds niveau par niveau.",
    },
    "UCS": {
        "nom": "Recherche à coût uniforme (UCS / Dijkstra)",
        "temps": "O(b^(1 + ⌊C*/ε⌋))",
        "espace": "O(b^(1 + ⌊C*/ε⌋))",
        "completude": "Oui (si les coûts des arcs sont ≥ ε > 0)",
        "optimalite": "Oui (optimal en coût total cumulé g(n)).",
        "strategie": "Frontière triée par g(n) croissant (coût depuis la racine).",
    },
    "DFS": {
        "nom": "Parcours en profondeur (DFS)",
        "temps": "O(b^m)",
        "espace": "O(b·m)",
        "completude": "Non dans les espaces infinis ou avec cycles non détectés ; Oui dans un espace fini avec liste des visités.",
        "optimalite": "Non (peut trouver un chemin très long avant un chemin optimal).",
        "strategie": "Frontière LIFO (pile). Explore la branche la plus profonde.",
    },
    "DLS": {
        "nom": "Profondeur limitée (DLS)",
        "temps": "O(b^l)",
        "espace": "O(b·l)",
        "completude": "Non si la solution est à une profondeur d > l ; Oui si d ≤ l.",
        "optimalite": "Non optimal en coût général.",
        "strategie": "DFS restreint à une profondeur maximale l.",
    },
    "IDS": {
        "nom": "Approfondissement itératif (IDS)",
        "temps": "O(b^d)",
        "espace": "O(b·d)",
        "completude": "Oui (si b est fini)",
        "optimalite": "Oui si les coûts des arcs sont uniformes, sinon non optimal en coût pondéré.",
        "strategie": "Applique DLS successivement avec limite = 0, 1, 2, ... jusqu'à trouver le but.",
    },
    "Best-First": {
        "nom": "Recherche Gloutonne / Best-First",
        "temps": "O(b^m) dans le pire cas",
        "espace": "O(b^m) dans le pire cas",
        "completude": "Non dans un arbre infini ; Oui dans un graphe fini avec liste fermée.",
        "optimalite": "Non (ne tient pas compte du coût g déjà payé).",
        "strategie": "Frontière ordonnée par h(n) croissant (distance estimée au but).",
    },
    "A*": {
        "nom": "Algorithme A*",
        "temps": "Exponentiel O(b^d) dans le pire cas, dépend de la précision de h",
        "espace": "O(b^d) (garde tous les nœuds en mémoire)",
        "completude": "Oui (si coûts ≥ ε > 0 et b fini)",
        "optimalite": "Oui si l'heuristique est admissible (recherche arbre) et consistante/monotone (recherche graphe).",
        "strategie": "Frontière ordonnée par f(n) = g(n) + h(n) croissant.",
    },
    "SMA*": {
        "nom": "A* à mémoire bornée (SMA*)",
        "temps": "Dépend de la mémoire disponible",
        "espace": "O(M) borné par la taille mémoire maximale M fixée",
        "completude": "Oui si la mémoire M suffit pour stocker le chemin le plus court.",
        "optimalite": "Optimal si la mémoire disponible est suffisante pour contenir le chemin de coût minimal.",
        "strategie": "A* avec seuil mémoire. Si la frontière dépasse M, élague le nœud de pire f.",
    },
    "RBFS": {
        "nom": "Recursive Best-First Search (RBFS)",
        "temps": "O(b^d) dans le meilleur cas, peut recalculer des nœuds",
        "espace": "O(b·d) linéaire en profondeur",
        "completude": "Oui (si b fini et coûts ≥ ε > 0)",
        "optimalite": "Oui si l'heuristique h est admissible.",
        "strategie": "Best-First récursif en espace linéaire avec variable f_limit et mémorisation de l'alternative.",
    },
}


# ---------------------------------------------------------------------------
# Vérification de l'heuristique (Admissibilité & Consistance)
# ---------------------------------------------------------------------------

def compute_true_optimal_costs(graph: Graph, goal: str) -> Dict[str, float]:
    """Calcule le coût réel optimal h*(n) depuis chaque sommet vers le but via Dijkstra inversé."""
    norm_goal = goal.strip()
    if norm_goal not in graph.nodes:
        return {}

    # Construction du graphe inversé : u <- v avec coût(u, v)
    reversed_adj: Dict[str, List[Tuple[str, float]]] = {n: [] for n in graph.nodes}
    for e in graph.edges:
        reversed_adj[e.to_node].append((e.from_node, e.cost))

    # Dijkstra depuis le but
    distances: Dict[str, float] = {norm_goal: 0.0}
    pq: List[Tuple[float, str]] = [(0.0, norm_goal)]

    while pq:
        dist_u, u = heapq.heappop(pq)
        if dist_u > distances[u]:
            continue

        for pred, cost in reversed_adj[u]:
            new_dist = dist_u + cost
            if pred not in distances or new_dist < distances[pred]:
                distances[pred] = new_dist
                heapq.heappush(pq, (new_dist, pred))

    return distances


def verify_admissibility(graph: Graph, goal: Optional[str] = None) -> Dict[str, Any]:
    """Vérifie si h(n) <= h*(n) pour chaque sommet pouvant atteindre le but."""
    target_goal = (goal or graph.goal_node or "").strip()
    if not target_goal or target_goal not in graph.nodes:
        return {
            "is_admissible": False,
            "goal": target_goal,
            "message": "Sommet but non défini ou inexistant dans le graphe.",
            "violations": [],
            "details": {},
        }

    h_star = compute_true_optimal_costs(graph, target_goal)
    violations = []
    details = {}
    is_admissible = True

    # Vérification h(but) = 0
    h_goal = graph.heuristics.get(target_goal, 0.0)
    if h_goal != 0.0:
        is_admissible = False
        violations.append(f"h({target_goal}) = {h_goal} ≠ 0 (le but doit avoir une heuristique nulle).")

    for node in graph.nodes:
        h_val = graph.heuristics.get(node, 0.0)
        h_opt = h_star.get(node, float("inf"))

        is_node_valid = True
        if h_opt < float("inf"):
            if h_val > h_opt:
                is_node_valid = False
                is_admissible = False
                violations.append(
                    f"Sommet « {node} » : h={h_val} > h*={h_opt} (surestimation de {round(h_val - h_opt, 2)})."
                )
        details[node] = {
            "h": h_val,
            "h_star": h_opt if h_opt < float("inf") else "Inaccessible",
            "is_admissible": is_node_valid,
        }

    return {
        "is_admissible": is_admissible,
        "goal": target_goal,
        "message": (
            "✔ L'heuristique est ADMISSIBLE (ne surestime jamais le coût réel vers le but)."
            if is_admissible
            else "⚠ L'heuristique N'EST PAS ADMISSIBLE (au moins une surestimation détectée)."
        ),
        "violations": violations,
        "details": details,
    }


def verify_consistency(graph: Graph, goal: Optional[str] = None) -> Dict[str, Any]:
    """Vérifie si h(n) <= c(n, n') + h(n') pour chaque arc orienté (Consistance / Monotonie)."""
    target_goal = (goal or graph.goal_node or "").strip()
    violations = []
    is_consistent = True

    if target_goal and target_goal in graph.nodes:
        h_goal = graph.heuristics.get(target_goal, 0.0)
        if h_goal != 0.0:
            is_consistent = False
            violations.append(f"h({target_goal}) = {h_goal} ≠ 0 pour l'état but.")

    for edge in graph.edges:
        h_u = graph.heuristics.get(edge.from_node, 0.0)
        h_v = graph.heuristics.get(edge.to_node, 0.0)
        cost = edge.cost

        if h_u > cost + h_v:
            is_consistent = False
            diff = round(h_u - (cost + h_v), 2)
            violations.append(
                f"Arc {edge.from_node} ➔ {edge.to_node} : h({edge.from_node})={h_u} > c({cost}) + h({edge.to_node})={h_v} (déficit de {diff})."
            )

    return {
        "is_consistent": is_consistent,
        "message": (
            "✔ L'heuristique est CONSISTANTE (satisfait l'inégalité triangulaire sur tous les arcs)."
            if is_consistent
            else "⚠ L'heuristique N'EST PAS CONSISTANTE (inégalité violée sur certains arcs)."
        ),
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# Algorithmes de recherche non informés
# ---------------------------------------------------------------------------

def bfs_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
) -> Iterator[SearchStep]:
    """Parcours en largeur d'abord (Breadth-First Search).

    - Frontière FIFO (deque).
    - Mémorisation des visités.
    - Expansion déterministe par ordre alphabétique.
    - Retourne le chemin minimisant le nombre d'arcs.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes:
        yield SearchStep(1, None, [], [], "Erreur : Sommet initial non défini ou invalide.", status="AUCUN_CHEMIN", is_final=True)
        return
    if not g_node or g_node not in graph.nodes:
        yield SearchStep(1, None, [], [], "Erreur : Sommet but non défini ou invalide.", status="AUCUN_CHEMIN", is_final=True)
        return

    # Cas particulier : départ == but
    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Le sommet initial '{s_node}' est déjà l'état but !",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    root = SearchNode(state=s_node, parent=None, g=0.0, depth=0)
    queue: deque[SearchNode] = deque([root])
    visited: Set[str] = {s_node}
    visited_list: List[str] = [s_node]

    step_num = 1

    def format_frontier() -> List[Dict[str, Any]]:
        return [
            FrontierItem(
                n.state,
                n.g,
                graph.heuristics.get(n.state, 0.0),
                n.g,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for n in queue
        ]

    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=list(visited_list),
        frontier=format_frontier(),
        action_desc=f"Initialisation BFS avec racine '{s_node}'.",
    )

    while queue:
        step_num += 1
        current = queue.popleft()

        # Expansion
        neighbors = graph.get_neighbors(current.state)
        newly_added = []

        for dest, cost in neighbors:
            if dest not in visited:
                visited.add(dest)
                visited_list.append(dest)
                child = SearchNode(
                    state=dest,
                    parent=current,
                    action_cost=cost,
                    g=current.g + cost,
                    depth=current.depth + 1,
                )
                queue.append(child)
                newly_added.append(dest)

                # Test du but à la génération (standard BFS)
                if dest == g_node:
                    path = child.get_path()
                    yield SearchStep(
                        step_num=step_num,
                        current_node=current.state,
                        visited=list(visited_list),
                        frontier=format_frontier(),
                        action_desc=f"But '{g_node}' atteint depuis '{current.state}' !",
                        path=path,
                        total_cost=child.g,
                        status="TROUVE",
                        is_final=True,
                    )
                    return

        yield SearchStep(
            step_num=step_num,
            current_node=current.state,
            visited=list(visited_list),
            frontier=format_frontier(),
            action_desc=(
                f"Développement de '{current.state}'. "
                f"Nouveaux successeurs ajoutés : [{', '.join(newly_added) if newly_added else 'aucun'}]."
            ),
        )

    # Fin sans chemin
    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(visited_list),
        frontier=[],
        action_desc=f"Frontière vide : aucun chemin vers le but '{g_node}'.",
        status="AUCUN_CHEMIN",
        is_final=True,
    )


def ucs_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
) -> Iterator[SearchStep]:
    """Recherche à coût uniforme (UCS / Dijkstra).

    - Frontière ordonnée par coût cumulé g(n) croissant.
    - Test du but au moment de l'extraction de la frontière.
    - Garantie de trouver le chemin de coût minimal.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommet initial ou but invalide.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    root = SearchNode(state=s_node, g=0.0, depth=0)
    counter = 0
    # Tas : (g, counter, state, node)
    heap: List[Tuple[float, int, str, SearchNode]] = [(0.0, counter, s_node, root)]
    best_g: Dict[str, float] = {s_node: 0.0}
    visited: Set[str] = set()
    visited_list: List[str] = []

    def format_frontier() -> List[Dict[str, Any]]:
        sorted_items = sorted(heap, key=lambda item: (item[0], item[2]))
        return [
            FrontierItem(
                n.state,
                n.g,
                graph.heuristics.get(n.state, 0.0),
                n.g,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for _, _, _, n in sorted_items
        ]

    step_num = 1
    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=[],
        frontier=format_frontier(),
        action_desc=f"Initialisation UCS avec racine '{s_node}' (g=0).",
    )

    while heap:
        step_num += 1
        g_val, _, state, current = heapq.heappop(heap)

        if state in visited:
            continue

        visited.add(state)
        visited_list.append(state)

        # Test du but à l'extraction
        if state == g_node:
            path = current.get_path()
            yield SearchStep(
                step_num=step_num,
                current_node=state,
                visited=list(visited_list),
                frontier=format_frontier(),
                action_desc=f"But '{g_node}' extrait de la frontière avec le coût optimal g={g_val} !",
                path=path,
                total_cost=current.g,
                status="TROUVE",
                is_final=True,
            )
            return

        # Expansion
        neighbors = graph.get_neighbors(state)
        for dest, cost in neighbors:
            new_g = current.g + cost
            if dest not in visited:
                if dest not in best_g or new_g < best_g[dest]:
                    best_g[dest] = new_g
                    counter += 1
                    child = SearchNode(
                        state=dest,
                        parent=current,
                        action_cost=cost,
                        g=new_g,
                        depth=current.depth + 1,
                    )
                    heapq.heappush(heap, (new_g, counter, dest, child))

        yield SearchStep(
            step_num=step_num,
            current_node=state,
            visited=list(visited_list),
            frontier=format_frontier(),
            action_desc=f"Développement de '{state}' (g={round(g_val, 2)}).",
        )

    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(visited_list),
        frontier=[],
        action_desc=f"Frontière vide : aucun chemin vers '{g_node}'.",
        status="AUCUN_CHEMIN",
        is_final=True,
    )


def dfs_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
) -> Iterator[SearchStep]:
    """Parcours en profondeur itératif (Depth-First Search).

    - Frontière LIFO (pile).
    - Détection des cycles par ensemble des visités.
    - Successeurs empilés en ordre inverse pour dépiler alphabétiquement.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    root = SearchNode(state=s_node, g=0.0, depth=0)
    stack: List[SearchNode] = [root]
    visited: Set[str] = set()
    visited_list: List[str] = []

    def format_frontier() -> List[Dict[str, Any]]:
        return [
            FrontierItem(
                n.state,
                n.g,
                graph.heuristics.get(n.state, 0.0),
                n.g,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for n in reversed(stack)
        ]

    step_num = 1
    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=[],
        frontier=format_frontier(),
        action_desc=f"Initialisation DFS avec racine '{s_node}'.",
    )

    while stack:
        step_num += 1
        current = stack.pop()

        if current.state in visited:
            continue

        visited.add(current.state)
        visited_list.append(current.state)

        if current.state == g_node:
            path = current.get_path()
            yield SearchStep(
                step_num=step_num,
                current_node=current.state,
                visited=list(visited_list),
                frontier=format_frontier(),
                action_desc=f"But '{g_node}' atteint !",
                path=path,
                total_cost=current.g,
                status="TROUVE",
                is_final=True,
            )
            return

        neighbors = graph.get_neighbors(current.state)
        # Empiler en ordre inverse pour dépiler alphabétiquement
        for dest, cost in reversed(neighbors):
            if dest not in visited:
                child = SearchNode(
                    state=dest,
                    parent=current,
                    action_cost=cost,
                    g=current.g + cost,
                    depth=current.depth + 1,
                )
                stack.append(child)

        yield SearchStep(
            step_num=step_num,
            current_node=current.state,
            visited=list(visited_list),
            frontier=format_frontier(),
            action_desc=f"Développement DFS de '{current.state}' (profondeur {current.depth}).",
        )

    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(visited_list),
        frontier=[],
        action_desc=f"Pile vide : aucun chemin vers '{g_node}'.",
        status="AUCUN_CHEMIN",
        is_final=True,
    )


def dls_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
    depth_limit: int = 3,
) -> Iterator[SearchStep]:
    """Parcours en profondeur limitée (Depth-Limited Search).

    Distingue clairement :
    - 'TROUVE' : solution trouvée à profondeur <= depth_limit.
    - 'ECHEC_LIMITE' : exploration arrêtée en raison de la limite de profondeur (cutoff).
    - 'AUCUN_CHEMIN' : tout l'espace accessible a été exploré sans jamais atteindre la limite.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    root = SearchNode(state=s_node, g=0.0, depth=0)
    stack: List[SearchNode] = [root]
    visited_depth: Dict[str, int] = {}
    visited_list: List[str] = []
    cutoff_occurred = False

    def format_frontier() -> List[Dict[str, Any]]:
        return [
            FrontierItem(
                n.state,
                n.g,
                graph.heuristics.get(n.state, 0.0),
                n.g,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for n in reversed(stack)
        ]

    step_num = 1
    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=[],
        frontier=format_frontier(),
        action_desc=f"Initialisation DLS (limite L={depth_limit}) avec '{s_node}'.",
    )

    while stack:
        step_num += 1
        current = stack.pop()

        if current.state in visited_depth and visited_depth[current.state] <= current.depth:
            continue

        visited_depth[current.state] = current.depth
        if current.state not in visited_list:
            visited_list.append(current.state)

        if current.state == g_node:
            path = current.get_path()
            yield SearchStep(
                step_num=step_num,
                current_node=current.state,
                visited=list(visited_list),
                frontier=format_frontier(),
                action_desc=f"But '{g_node}' atteint à la profondeur {current.depth} ≤ {depth_limit} !",
                path=path,
                total_cost=current.g,
                status="TROUVE",
                is_final=True,
            )
            return

        if current.depth >= depth_limit:
            cutoff_occurred = True
            yield SearchStep(
                step_num=step_num,
                current_node=current.state,
                visited=list(visited_list),
                frontier=format_frontier(),
                action_desc=f"Nœud '{current.state}' atteint la limite de profondeur L={depth_limit} (non développé).",
            )
            continue

        neighbors = graph.get_neighbors(current.state)
        for dest, cost in reversed(neighbors):
            child_depth = current.depth + 1
            if dest not in visited_depth or visited_depth[dest] > child_depth:
                child = SearchNode(
                    state=dest,
                    parent=current,
                    action_cost=cost,
                    g=current.g + cost,
                    depth=child_depth,
                )
                stack.append(child)

        yield SearchStep(
            step_num=step_num,
            current_node=current.state,
            visited=list(visited_list),
            frontier=format_frontier(),
            action_desc=f"Développement DLS de '{current.state}' (profondeur {current.depth}/{depth_limit}).",
        )

    final_status = "ECHEC_LIMITE" if cutoff_occurred else "AUCUN_CHEMIN"
    desc = (
        f"Échec dû à la limite de profondeur L={depth_limit} (branches élaguées non explorées)."
        if cutoff_occurred
        else f"Aucun chemin possible vers '{g_node}' (arbre totalement épuisé)."
    )
    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(visited_list),
        frontier=[],
        action_desc=desc,
        status=final_status,
        is_final=True,
    )


def ids_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
    max_depth_limit: int = 10,
) -> Iterator[SearchStep]:
    """Recherche par approfondissement itératif (Iterative Deepening Search).

    Exécute successivement DLS avec des limites 0, 1, 2, ..., max_depth_limit.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    step_global = 1
    cutoff_any = False

    for limit in range(max_depth_limit + 1):
        yield SearchStep(
            step_num=step_global,
            current_node=None,
            visited=[],
            frontier=[],
            action_desc=f"═══ Lancement de l'itération IDS avec limite de profondeur L={limit} ═══",
        )
        step_global += 1

        dls_gen = dls_search(graph, s_node, g_node, depth_limit=limit)
        last_step = None
        for step in dls_gen:
            step.step_num = step_global
            step_global += 1
            last_step = step
            if step.is_final and step.status == "TROUVE":
                yield step
                return
            if not step.is_final:
                yield step

        if last_step and last_step.status == "ECHEC_LIMITE":
            cutoff_any = True
        elif last_step and last_step.status == "AUCUN_CHEMIN":
            # Aucun nœud n'a été coupé par la limite -> le graphe entier est épuisé !
            yield SearchStep(
                step_num=step_global,
                current_node=None,
                visited=last_step.visited,
                frontier=[],
                action_desc=f"Recherche terminée : aucun chemin existant vers '{g_node}'.",
                status="AUCUN_CHEMIN",
                is_final=True,
            )
            return

    yield SearchStep(
        step_num=step_global,
        current_node=None,
        visited=[],
        frontier=[],
        action_desc=f"Échec IDS : limite maximale ({max_depth_limit}) atteinte sans trouver de solution.",
        status="ECHEC_LIMITE" if cutoff_any else "AUCUN_CHEMIN",
        is_final=True,
    )


# ---------------------------------------------------------------------------
# Algorithmes de recherche informés
# ---------------------------------------------------------------------------

def greedy_best_first_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
) -> Iterator[SearchStep]:
    """Recherche Gloutonne / Best-First Search.

    - Frontière ordonnée par h(n) croissant.
    - Test du but au moment de l'expansion.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    h_root = graph.heuristics.get(s_node, 0.0)
    root = SearchNode(state=s_node, g=0.0, h=h_root, f=h_root, depth=0)
    counter = 0
    heap: List[Tuple[float, int, str, SearchNode]] = [(h_root, counter, s_node, root)]
    visited: Set[str] = set()
    visited_list: List[str] = []

    def format_frontier() -> List[Dict[str, Any]]:
        sorted_items = sorted(heap, key=lambda item: (item[0], item[2]))
        return [
            FrontierItem(
                n.state,
                n.g,
                n.h,
                n.f,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for _, _, _, n in sorted_items
        ]

    step_num = 1
    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=[],
        frontier=format_frontier(),
        action_desc=f"Initialisation Best-First avec '{s_node}' (h={h_root}).",
    )

    while heap:
        step_num += 1
        h_val, _, state, current = heapq.heappop(heap)

        if state in visited:
            continue

        visited.add(state)
        visited_list.append(state)

        if state == g_node:
            path = current.get_path()
            yield SearchStep(
                step_num=step_num,
                current_node=state,
                visited=list(visited_list),
                frontier=format_frontier(),
                action_desc=f"But '{g_node}' atteint par recherche gloutonne !",
                path=path,
                total_cost=current.g,
                status="TROUVE",
                is_final=True,
            )
            return

        neighbors = graph.get_neighbors(state)
        for dest, cost in neighbors:
            if dest not in visited:
                child_h = graph.heuristics.get(dest, 0.0)
                counter += 1
                child = SearchNode(
                    state=dest,
                    parent=current,
                    action_cost=cost,
                    g=current.g + cost,
                    h=child_h,
                    f=child_h,
                    depth=current.depth + 1,
                )
                heapq.heappush(heap, (child_h, counter, dest, child))

        yield SearchStep(
            step_num=step_num,
            current_node=state,
            visited=list(visited_list),
            frontier=format_frontier(),
            action_desc=f"Développement Best-First de '{state}' (h={h_val}).",
        )

    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(visited_list),
        frontier=[],
        action_desc=f"Frontière vide : aucun chemin vers '{g_node}'.",
        status="AUCUN_CHEMIN",
        is_final=True,
    )


def a_star_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
) -> Iterator[SearchStep]:
    """Algorithme A*.

    - Open-List triée par f(n) = g(n) + h(n) croissant.
    - Closed-List (visités).
    - Mise à jour du meilleur chemin si un état déjà connu est réatteint avec un g inférieur.
    - Test du but au moment de l'extraction de l'Open-List.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    h_root = graph.heuristics.get(s_node, 0.0)
    root = SearchNode(state=s_node, g=0.0, h=h_root, f=h_root, depth=0)
    counter = 0
    # Tas Open : (f, counter, state, node)
    open_heap: List[Tuple[float, int, str, SearchNode]] = [(h_root, counter, s_node, root)]
    best_g: Dict[str, float] = {s_node: 0.0}
    closed: Set[str] = set()
    closed_list: List[str] = []

    def format_frontier() -> List[Dict[str, Any]]:
        sorted_items = sorted(open_heap, key=lambda item: (item[0], item[2]))
        # Dédupliquer visuellement les états non encore clos en gardant le meilleur
        seen = set()
        res = []
        for f_val, _, st, n in sorted_items:
            if st not in closed and st not in seen:
                seen.add(st)
                res.append(
                    FrontierItem(
                        n.state,
                        n.g,
                        n.h,
                        n.f,
                        n.depth,
                        n.parent.state if n.parent else None,
                    ).to_dict()
                )
        return res

    step_num = 1
    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=[],
        frontier=format_frontier(),
        action_desc=f"Initialisation A* avec '{s_node}' (g=0, h={h_root}, f={h_root}).",
    )

    while open_heap:
        step_num += 1
        f_val, _, state, current = heapq.heappop(open_heap)

        if state in closed:
            continue

        closed.add(state)
        closed_list.append(state)

        # Test de l'objectif à la sortie de l'Open-List
        if state == g_node:
            path = current.get_path()
            yield SearchStep(
                step_num=step_num,
                current_node=state,
                visited=list(closed_list),
                frontier=format_frontier(),
                action_desc=f"But '{g_node}' extrait de l'Open-List avec f={round(f_val, 2)} (optimal) !",
                path=path,
                total_cost=current.g,
                status="TROUVE",
                is_final=True,
            )
            return

        neighbors = graph.get_neighbors(state)
        for dest, cost in neighbors:
            new_g = current.g + cost
            if dest in closed and new_g >= best_g.get(dest, float("inf")):
                continue

            if dest not in best_g or new_g < best_g[dest]:
                best_g[dest] = new_g
                if dest in closed:
                    closed.remove(dest)
                    if dest in closed_list:
                        closed_list.remove(dest)

                dest_h = graph.heuristics.get(dest, 0.0)
                new_f = new_g + dest_h
                counter += 1
                child = SearchNode(
                    state=dest,
                    parent=current,
                    action_cost=cost,
                    g=new_g,
                    h=dest_h,
                    f=new_f,
                    depth=current.depth + 1,
                )
                heapq.heappush(open_heap, (new_f, counter, dest, child))

        yield SearchStep(
            step_num=step_num,
            current_node=state,
            visited=list(closed_list),
            frontier=format_frontier(),
            action_desc=f"Développement A* de '{state}' (g={round(current.g, 2)}, h={current.h}, f={round(f_val, 2)}).",
        )

    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(closed_list),
        frontier=[],
        action_desc=f"Open-List vide : aucun chemin vers '{g_node}'.",
        status="AUCUN_CHEMIN",
        is_final=True,
    )


def sma_star_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
    max_memory: int = 5,
) -> Iterator[SearchStep]:
    """Simplified Memory-Bounded A* (SMA*).

    - L'Open-List est bornée à au plus max_memory nœuds.
    - Lorsque la capacité est dépassée, le nœud de pire f (le plus grand f) est élagué.
    - Développe toujours en priorité le nœud de meilleur f.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    if max_memory < 1:
        yield SearchStep(1, None, [], [], "Taille mémoire SMA* doit être ≥ 1.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    h_root = graph.heuristics.get(s_node, 0.0)
    root = SearchNode(state=s_node, g=0.0, h=h_root, f=h_root, depth=0)
    # open_list : liste de SearchNode
    open_list: List[SearchNode] = [root]
    visited_list: List[str] = []

    def format_frontier() -> List[Dict[str, Any]]:
        sorted_nodes = sorted(open_list, key=lambda n: (n.f, n.state))
        return [
            FrontierItem(
                n.state,
                n.g,
                n.h,
                n.f,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for n in sorted_nodes
        ]

    step_num = 1
    yield SearchStep(
        step_num=step_num,
        current_node=None,
        visited=[],
        frontier=format_frontier(),
        action_desc=f"Initialisation SMA* (mémoire max={max_memory}) avec '{s_node}'.",
    )

    while open_list:
        step_num += 1
        # Trier par f croissant (meilleur en premier)
        open_list.sort(key=lambda n: (n.f, n.state))
        best_node = open_list.pop(0)

        if best_node.state not in visited_list:
            visited_list.append(best_node.state)

        if best_node.state == g_node:
            path = best_node.get_path()
            yield SearchStep(
                step_num=step_num,
                current_node=best_node.state,
                visited=list(visited_list),
                frontier=format_frontier(),
                action_desc=f"But '{g_node}' atteint par SMA* avec f={round(best_node.f, 2)} !",
                path=path,
                total_cost=best_node.g,
                status="TROUVE",
                is_final=True,
            )
            return

        neighbors = graph.get_neighbors(best_node.state)
        pruned_info = []

        for dest, cost in neighbors:
            # Éviter cycle sur la branche
            curr_anc = best_node
            is_cycle = False
            while curr_anc is not None:
                if curr_anc.state == dest:
                    is_cycle = True
                    break
                curr_anc = curr_anc.parent
            if is_cycle:
                continue

            dest_h = graph.heuristics.get(dest, 0.0)
            new_g = best_node.g + cost
            new_f = max(new_g + dest_h, best_node.f)  # Héritage monotonique

            child = SearchNode(
                state=dest,
                parent=best_node,
                action_cost=cost,
                g=new_g,
                h=dest_h,
                f=new_f,
                depth=best_node.depth + 1,
            )
            open_list.append(child)

            # Élagage si mémoire dépassée
            if len(open_list) > max_memory:
                # Élaguer le nœud ayant le pire f (le plus grand f)
                open_list.sort(key=lambda n: (n.f, n.state))
                worst = open_list.pop(-1)
                pruned_info.append(f"{worst.state} (f={round(worst.f, 1)})")

        pruned_msg = f" [Élagage mémoire : {', '.join(pruned_info)}]" if pruned_info else ""
        yield SearchStep(
            step_num=step_num,
            current_node=best_node.state,
            visited=list(visited_list),
            frontier=format_frontier(),
            action_desc=f"Développement SMA* de '{best_node.state}' (f={round(best_node.f, 2)}).{pruned_msg}",
        )

    yield SearchStep(
        step_num=step_num + 1,
        current_node=None,
        visited=list(visited_list),
        frontier=[],
        action_desc=f"Mémoire épuisée ou frontière vide sans trouver '{g_node}'.",
        status="ECHEC_LIMITE" if max_memory < len(graph.nodes) else "AUCUN_CHEMIN",
        is_final=True,
    )


def rbfs_search(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
) -> Iterator[SearchStep]:
    """Recursive Best-First Search (RBFS).

    - Recherche Best-First en profondeur avec espace mémoire linéaire O(b·d).
    - Maintient la variable f_limit héritée du parent.
    - Met à jour dynamiquement la valeur f d'un sous-arbre lors du repli (backtracking).
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        yield SearchStep(1, None, [], [], "Sommets invalides.", status="AUCUN_CHEMIN", is_final=True)
        return

    if s_node == g_node:
        yield SearchStep(
            1,
            s_node,
            [s_node],
            [],
            f"Départ '{s_node}' est le but.",
            path=[s_node],
            total_cost=0.0,
            status="TROUVE",
            is_final=True,
        )
        return

    h_root = graph.heuristics.get(s_node, 0.0)
    root = SearchNode(state=s_node, g=0.0, h=h_root, f=h_root, depth=0)
    visited_list: List[str] = []
    step_counter = [1]

    def format_frontier(nodes: List[SearchNode]) -> List[Dict[str, Any]]:
        return [
            FrontierItem(
                n.state,
                n.g,
                n.h,
                n.f,
                n.depth,
                n.parent.state if n.parent else None,
            ).to_dict()
            for n in sorted(nodes, key=lambda x: (x.f, x.state))
        ]

    yield SearchStep(
        step_num=step_counter[0],
        current_node=None,
        visited=[],
        frontier=format_frontier([root]),
        action_desc=f"Initialisation RBFS avec racine '{s_node}' (f={h_root}).",
    )

    # Structure récursive retournant (résultat_node, nouveau_f)
    def rbfs_recursive(node: SearchNode, f_limit: float) -> Tuple[Optional[SearchNode], float]:
        step_counter[0] += 1
        if node.state not in visited_list:
            visited_list.append(node.state)

        if node.state == g_node:
            return node, node.f

        neighbors = graph.get_neighbors(node.state)
        successors: List[SearchNode] = []

        for dest, cost in neighbors:
            # Éviter cycle sur la branche courante
            curr_anc = node
            is_cycle = False
            while curr_anc is not None:
                if curr_anc.state == dest:
                    is_cycle = True
                    break
                curr_anc = curr_anc.parent
            if is_cycle:
                continue

            child_h = graph.heuristics.get(dest, 0.0)
            child_g = node.g + cost
            child_f = max(child_g + child_h, node.f)  # Propriété RBFS
            child = SearchNode(
                state=dest,
                parent=node,
                action_cost=cost,
                g=child_g,
                h=child_h,
                f=child_f,
                depth=node.depth + 1,
            )
            successors.append(child)

        if not successors:
            return None, float("inf")

        while True:
            # Trier les successeurs par f croissant
            successors.sort(key=lambda s: (s.f, s.state))
            best = successors[0]

            if best.f > f_limit or best.f == float("inf"):
                return None, best.f

            # Déterminer la valeur alternative (second meilleur f)
            alternative = successors[1].f if len(successors) > 1 else float("inf")

            # Appel récursif avec min(f_limit, alternative)
            sub_limit = min(f_limit, alternative)
            result, best.f = rbfs_recursive(best, sub_limit)

            if result is not None:
                return result, best.f

    # Exécution
    solution_node, _ = rbfs_recursive(root, float("inf"))

    if solution_node:
        path = solution_node.get_path()
        yield SearchStep(
            step_num=step_counter[0],
            current_node=solution_node.state,
            visited=list(visited_list),
            frontier=[],
            action_desc=f"But '{g_node}' atteint par RBFS avec coût={round(solution_node.g, 2)} !",
            path=path,
            total_cost=solution_node.g,
            status="TROUVE",
            is_final=True,
        )
    else:
        yield SearchStep(
            step_num=step_counter[0],
            current_node=None,
            visited=list(visited_list),
            frontier=[],
            action_desc=f"RBFS terminé : aucun chemin vers '{g_node}'.",
            status="AUCUN_CHEMIN",
            is_final=True,
        )


# ---------------------------------------------------------------------------
# Fonction d'exécution globale et utilitaire
# ---------------------------------------------------------------------------

def run_search_algorithm(
    graph: Graph,
    algorithm: str,
    start: Optional[str] = None,
    goal: Optional[str] = None,
    depth_limit: int = 3,
    max_depth_limit: int = 10,
    max_memory: int = 5,
) -> SearchResult:
    """Exécute un algorithme et compile le SearchResult complet avec toutes les étapes."""
    algo_key = algorithm.strip()

    generator: Iterator[SearchStep]
    if algo_key == "BFS":
        generator = bfs_search(graph, start, goal)
    elif algo_key == "UCS":
        generator = ucs_search(graph, start, goal)
    elif algo_key == "DFS":
        generator = dfs_search(graph, start, goal)
    elif algo_key == "DLS":
        generator = dls_search(graph, start, goal, depth_limit=depth_limit)
    elif algo_key == "IDS":
        generator = ids_search(graph, start, goal, max_depth_limit=max_depth_limit)
    elif algo_key == "Best-First":
        generator = greedy_best_first_search(graph, start, goal)
    elif algo_key == "A*":
        generator = a_star_search(graph, start, goal)
    elif algo_key == "SMA*":
        generator = sma_star_search(graph, start, goal, max_memory=max_memory)
    elif algo_key == "RBFS":
        generator = rbfs_search(graph, start, goal)
    else:
        raise ValueError(f"Algorithme inconnu : {algo_key}")

    steps: List[SearchStep] = []
    final_step: Optional[SearchStep] = None

    for step in generator:
        steps.append(step)
        if step.is_final:
            final_step = step

    if final_step is None and steps:
        final_step = steps[-1]

    status = final_step.status if final_step else "AUCUN_CHEMIN"
    path = final_step.path if (final_step and final_step.path) else []
    cost = final_step.total_cost if final_step else 0.0

    # Compter les développements (étapes avec current_node non None)
    expanded = sum(1 for s in steps if s.current_node is not None)
    max_depth = max((len(s.path) - 1 for s in steps if s.path), default=0)

    msg = final_step.action_desc if final_step else "Recherche achevée."

    return SearchResult(
        algorithm=algo_key,
        status=status,
        path=path,
        total_cost=cost,
        nodes_expanded=expanded,
        max_depth=max_depth,
        steps=steps,
        message=msg,
    )


def compare_all_algorithms(
    graph: Graph,
    start: Optional[str] = None,
    goal: Optional[str] = None,
    depth_limit: int = 3,
    max_depth_limit: int = 10,
    max_memory: int = 5,
) -> Dict[str, Any]:
    """Exécute tous les algorithmes applicables sur le graphe et compile un comparatif complet.

    - Les algorithmes informés ne sont lancés que si l'heuristique est complète pour tous les sommets.
    - Mesure précise du temps d'exécution en ms, du coût, des nœuds développés et de la profondeur.
    - Identification automatique de l'optimalité et du meilleur algorithme.
    """
    s_node = (start or graph.start_node or "").strip()
    g_node = (goal or graph.goal_node or "").strip()

    if not s_node or s_node not in graph.nodes or not g_node or not g_node in graph.nodes:
        return {
            "success": False,
            "error": "Sommet initial ou but invalide.",
            "results": [],
            "best_algo": None,
            "min_cost": None,
        }

    has_full_heuristics = all(n in graph.heuristics for n in graph.nodes)

    uninformed_algos = ["BFS", "UCS", "DFS", "DLS", "IDS"]
    informed_algos = ["Best-First", "A*", "SMA*", "RBFS"]

    algos_to_run = list(uninformed_algos)
    if has_full_heuristics:
        algos_to_run.extend(informed_algos)

    results_data: List[Dict[str, Any]] = []
    min_cost = float("inf")

    for algo in algos_to_run:
        t0 = time.perf_counter()
        res = run_search_algorithm(
            graph,
            algo,
            start=s_node,
            goal=g_node,
            depth_limit=depth_limit,
            max_depth_limit=max_depth_limit,
            max_memory=max_memory,
        )
        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        found = (res.status == "TROUVE")
        cost = res.total_cost if found else float("inf")
        if found and cost < min_cost:
            min_cost = cost

        results_data.append({
            "algorithm": algo,
            "category": "Non informée" if algo in uninformed_algos else "Informée",
            "status": res.status,
            "found": found,
            "path": res.path,
            "path_length": max(0, len(res.path) - 1) if found else 0,
            "cost": res.total_cost if found else None,
            "nodes_expanded": res.nodes_expanded,
            "time_ms": round(t_elapsed_ms, 3),
            "max_depth": res.max_depth,
            "is_optimal": False,
        })

    # Déterminer l'optimalité
    best_algo = None
    fewest_expanded = float("inf")

    if min_cost < float("inf"):
        for row in results_data:
            if row["found"] and row["cost"] == min_cost:
                row["is_optimal"] = True
                if row["nodes_expanded"] < fewest_expanded:
                    fewest_expanded = row["nodes_expanded"]
                    best_algo = row["algorithm"]

    return {
        "success": True,
        "start": s_node,
        "goal": g_node,
        "has_full_heuristics": has_full_heuristics,
        "min_cost": min_cost if min_cost < float("inf") else None,
        "best_algo": best_algo,
        "results": results_data,
    }
