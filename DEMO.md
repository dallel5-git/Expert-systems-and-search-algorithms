# Guide et Scénario de Démonstration (Soutenance 2-3 minutes)

**Projet :** Systèmes Experts et Algorithmes de Recherche dans les Espaces d'États  
**Cadre :** ENSI — Module « Intelligence Artificielle & Machine Learning » (II2)  
**Durée conseillée :** 2 minutes 30 secondes à 3 minutes.

---

## Chronogramme de Présentation

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ 0:00 - 0:25     │ 0:25 - 1:15     │ 1:15 - 2:15     │ 2:15 - 2:45     │
│ Introduction    │ Module 1        │ Module 2        │ Comparatif &    │
│ & Menu Général  │ Système Expert  │ Algorithmes     │ Qualité / Tests │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## ⏱ 0:00 - 0:25 | Introduction & Ergonomie de l'Application

### Action :
1. Lancer l'application avec `./run.sh` (ou `run.bat` sous Windows).
2. Montrer l'écran d'accueil avec l'en-tête académique ENSI.
3. Basculer le switch de thème (en haut à droite) : **Sombre ⇄ Clair** pour illustrer l'adaptabilité visuelle.
4. Cliquer sur le bouton **« 1. Systèmes experts »**.

### Discours :
> *« Bonjour Monsieur. Nous vous présentons notre application desktop développée pour le module d'IA et Machine Learning de l'ENSI. L'application est articulée autour d'un menu d'accueil sobre et moderne avec thème clair/sombre automatique. Elle intègre deux modules majeurs totalement découplés de l'interface graphique : le moteur d'inférence de systèmes experts et les algorithmes de recherche dans les espaces d'états. Débutons par le Module 1. »*

---

## ⏱ 0:25 - 1:15 | Module 1 — Systèmes Experts (Ordre 0+)

### Action :
1. Dans le sélecteur d'exemples, charger **« Base Géométrie - Triangles »** (ou « Base Tarte aux pommes »).
2. **Chaînage avant :**
   - Cliquer sur le bouton **« Étape suivante ▶ »** 2 fois pour montrer l'exécution interactive pas-à-pas (règles déclenchées, faits ajoutés, journal horodaté).
   - Cliquer sur **« Tout exécuter ⚡ »** : observer la saturation de la base de faits et l'explication finale.
3. **Chaînage arrière :**
   - Dans le champ « But à prouver », choisir `triangle rectangle`.
   - Cliquer sur **« Lancer Chaînage Arrière »**.
   - Observer l'arbre de preuve hiérarchique avec ses coches vertes `[✔]` et les justifications de chaque sous-but (application de `R2`, sous-but `triangle` démontré via `R1`, faits initiaux).
4. **Cas limites et robustesse :**
   - Taper un but inexistant `triangle mystere` : l'application répond instantanément par un échec explicite sans aucun plantage.
5. Cliquer sur **« ◀ Retour au menu »**, puis sur **« 2. Algorithmes de recherche »**.

### Discours :
> *« Dans ce premier module, notre moteur d'inférence implémente le chaînage avant déterministe avec saturation et traçabilité complète de chaque déduction, ainsi que le chaînage arrière récursif dirigé par le but avec détection de cycles et retour sur trace. L'arbre de preuve détaille visuellement la cascade de déductions, et l'utilisateur peut tester n'importe quelle hypothèse en toute sécurité grâce à une gestion rigoureuse des erreurs. »*

---

## ⏱ 1:15 - 2:15 | Module 2 — Algorithmes de Recherche

### Action :
1. Montrer le graphe orienté et pondéré affiché au centre (graphe du cours, sommets A à G avec heuristiques \(h(n)\) et coûts sur chaque arc).
2. **Recherche non informée :**
   - Sélectionner l'algorithme **BFS** puis cliquer sur **« Tout exécuter ⚡ »** : chemin trouvé `A ➜ B ➜ D ➜ G` (3 arcs, coût 14).
   - Sélectionner **UCS** puis cliquer sur **« Tout exécuter ⚡ »** : chemin trouvé `A ➜ B ➜ D ➜ G` (coût minimal = 13).
   - Mettre en valeur l'onglet **« Frontière (Open) »** qui expose la structure de données réelle (FIFO pour BFS, file de priorité triée par \(g\) pour UCS).
3. **Recherche informée (A*) :**
   - Sélectionner **A\***.
   - Cliquer sur **« Propriétés Théoriques »** : montrer l'analyse automatique certifiant que l'heuristique du cours est **admissible** et **consistante**.
   - Cliquer sur **« Tout exécuter ⚡ »** : le chemin optimal s'illumine en vert vif (`A ➜ B ➜ D ➜ G`, coût 13) avec seulement 5 nœuds développés.

### Discours :
> *« Passons au Module 2. Le graphe orienté et pondéré est modélisé et rendu de façon interactive avec Matplotlib et NetworkX. Tous les algorithmes du cours y sont implémentés fidèlement : BFS avec file FIFO, DFS en pile LIFO, UCS trié par coût cumulé g, Recherche Gloutonne triée par h, A* avec f = g + h, ainsi que SMA* à mémoire bornée et RBFS récursif. L'interface affiche en temps réel le nœud développé, l'état exact de la frontière et valide formellement l'admissibilité de l'heuristique. »*

---

## ⏱ 2:15 - 2:45 | Bonus Comparatif & Qualité du Code

### Action :
1. Dans le panneau de droite, basculer sur l'onglet **« Comparaison (Bonus) »**.
2. Cliquer sur le bouton **« 🚀 Lancer le comparatif complet »**.
   - Montrer le tableau récapitulatif instantané (algorithme, statut, coût, nœuds explorés, temps d'exécution en millisecondes, optimalité).
   - Montrer le diagramme à barres comparant les nœuds développés avec surbrillance verte de la meilleure solution (A*).
3. Ouvrir un terminal rapide et taper :
   ```bash
   pytest -v tests/
   ```
   (Montrer les **80 tests unitaires** qui passent en ~0.2 seconde avec 100% de succès).

### Discours :
> *« En bonus, nous avons intégré un banc d'essai comparatif automatisé. En un clic, tous les algorithmes sont confrontés sur le même graphe : le tableau met en relief le compromis entre coût de solution et effort d'exploration, complété par un diagramme à barres dynamique. Côté ingénierie logicielle, le projet est 100% typé, documenté en français, ne dépend d'aucun chemin absolu et dispose d'une suite de 80 tests unitaires automatisés validant l'ensemble des cas nominaux et extrêmes. »*

---

## ⏱ 2:45 - 3:00 | Conclusion & Questions

### Discours :
> *« En conclusion, le devoir respecte l'intégralité des spécifications demandées pour l'ENSI, avec une architecture évolutive et zéro dépendance circulaire. Nous sommes à votre disposition pour toute question ou manipulation spécifique. Merci pour votre attention. »*
