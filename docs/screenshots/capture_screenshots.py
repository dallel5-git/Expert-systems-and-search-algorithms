#!/usr/bin/env python3
"""Script utilitaire pour générer et actualiser les captures et figures du projet.

Génère les visualisations du graphe du cours, de l'arbre de preuve du système expert,
de la recherche A* et du diagramme comparatif des algorithmes dans docs/screenshots/.
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from core.expert_system import KnowledgeBase, backward_chaining
from gui.app import App

SCREENSHOTS_DIR = Path(__file__).parent


def generate_all_screenshots() -> None:
    print("[1/3] Génération des figures Module 2 (Graphe, A*, Comparatif)...")
    app = App()
    app.withdraw()
    app.show_search()
    sv = app.view_search

    # Graphe du cours par défaut
    sv._refresh_graph_canvas()
    sv.fig.savefig(SCREENSHOTS_DIR / "graphe_visualisation.png", dpi=150, bbox_inches="tight")
    print("  -> docs/screenshots/graphe_visualisation.png")

    # Recherche A* avec chemin solution en surbrillance
    sv.combo_algo.set("A*")
    sv._run_all()
    sv.fig.savefig(SCREENSHOTS_DIR / "recherche_astar_solution.png", dpi=150, bbox_inches="tight")
    print("  -> docs/screenshots/recherche_astar_solution.png")

    # Comparaison de tous les algorithmes
    sv._handle_run_comparison()
    sv.fig_chart.savefig(SCREENSHOTS_DIR / "comparaison_algorithmes.png", dpi=150, bbox_inches="tight")
    print("  -> docs/screenshots/comparaison_algorithmes.png")
    app.destroy()

    print("[2/3] Génération de l'arbre de preuve Module 1 (Chaînage arrière)...")
    kb_path = Path(__file__).parent.parent / "data" / "kb_triangle.json"
    kb = KnowledgeBase.load_from_json(kb_path)
    res = backward_chaining(kb, "triangle rectangle")

    G = nx.DiGraph()
    labels = {}

    def add_nodes(node, parent_id=None):
        nid = f"{node.goal}_{id(node)}"
        mark = "✔" if node.status else "✘"
        labels[nid] = f"{node.goal}\n[{mark} {node.reason}]"
        G.add_node(nid)
        if parent_id is not None:
            G.add_edge(parent_id, nid)
        for ch in node.children:
            add_nodes(ch, nid)

    add_nodes(res.root_node)

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#161b22")
    ax.set_facecolor("#161b22")
    pos = nx.spring_layout(G, seed=42)
    node_colors = ["#10b981" if "✔" in labels[n] else "#ef4444" for n in G.nodes()]

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=3200, alpha=0.9)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#60a5fa", arrows=True, arrowsize=18, width=2)
    nx.draw_networkx_labels(
        G, pos, labels, ax=ax, font_size=8, font_color="white", font_family="sans-serif", font_weight="bold"
    )
    ax.set_title(
        "Système Expert — Arbre de preuve (Chaînage arrière : triangle rectangle)",
        color="white",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(SCREENSHOTS_DIR / "expert_arbre_preuve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  -> docs/screenshots/expert_arbre_preuve.png")

    print("[3/3] Toutes les figures ont été générées avec succès !")


if __name__ == "__main__":
    generate_all_screenshots()
