# Coach IA GTB — Plan d'Action Détaillé

> **Projet** : PFEE EPITA × AER — Coach IA pour Gestion Technique du Bâtiment
> **Période** : Mai 2026 → 31 janvier 2027
> **Méthodologie** : Scrum-Ban (livraison continue) — 1 jour/semaine
> **Version du plan** : 1.0 — basée sur la Roadmap V2 + Architecture Technique V1

---

## Table des matières

1. [Vue d'ensemble & jalons critiques](#1-vue-densemble--jalons-critiques)
2. [Phase 1 — Analyse & Fondations (S1-S7)](#phase-1--analyse--fondations-s1-s7)
3. [Phase 2 — Pipeline & Intelligence IA (S8-S20)](#phase-2--pipeline--intelligence-ia-s8-s20)
4. [Phase 3 — Interface, Énergie & Tests (S21-S30)](#phase-3--interface-énergie--tests-s21-s30)
5. [Risques et plan de mitigation](#5-risques-et-plan-de-mitigation)
6. [Dépendances bloquantes côté AER](#6-dépendances-bloquantes-côté-aer)
7. [Critères de succès du MVP](#7-critères-de-succès-du-mvp)
8. [Gouvernance & rituels](#8-gouvernance--rituels)

---

## 1. Vue d'ensemble & jalons critiques

| Jalon | Date cible | Livrable | Statut |
|---|---|---|---|
| J1 — Architecture validée | Fin S2 (mai 2026) | Doc Architecture V1 signé AER | 🔄 En cours |
| J2 — Cartographie GTB + référentiel alarmes | Fin S7 (juin 2026) | Référentiel + base de cas | ⏳ |
| J3 — Pipeline GTB → Backend opérationnel | Fin S12 (août 2026) | Backend + TimescaleDB ingérant des données réelles | ⏳ |
| J4 — Démo physique intermédiaire | Mi-juillet 2026 | POC connecteur + base RAG amorcée | ⏳ |
| J5 — Agent IA V1 (diagnostic) | Fin S17 (septembre 2026) | Agent répondant sur alarme contextualisée | ⏳ |
| J6 — Moteur priorisation + règles métier | Fin S20 (octobre 2026) | Plan d'action automatique quotidien | ⏳ |
| J7 — Dashboard + Chatbot V1 | Fin S24 (novembre 2026) | UI React opérationnelle | ⏳ |
| J8 — Module énergie | Fin S27 (décembre 2026) | Analyse conso + scénarios optimisation | ⏳ |
| J9 — Tests terrain validés | Mi-S30 (janvier 2027) | Rapport tests sur GTB AER | ⏳ |
| **J10 — MVP livré + démo finale** | **31 janvier 2027** | **Rapport PFEE + démo jury** | ⏳ |

---

## Phase 1 — Analyse & Fondations (S1-S7)

### 1.1 Sprint S1-S2 — Kick-off & cadrage architecture (mai 2026)

#### Tâches techniques
- [x] **T1.1** Rédaction de l'architecture technique V1 (ce document)
- [ ] **T1.2** Validation formelle de l'architecture par AER (réunion dédiée)
- [ ] **T1.3** Création du repository GitHub `coach-ia-gtb` avec :
  - Branches `main`, `develop`, convention `feature/*`, `fix/*`
  - Protection de `main` (PR review obligatoire)
  - Template d'issue + template de PR
  - `.gitignore` Python + Node + IDE
- [ ] **T1.4** Mise en place de l'environnement de dev local :
  - Docker Compose (Postgres+TimescaleDB, ChromaDB, backend, frontend)
  - Pré-commit hooks (Black, Ruff, ESLint, Prettier)
  - `Makefile` avec commandes `make up`, `make test`, `make lint`
- [ ] **T1.5** Création du backlog projet (GitHub Projects) avec import de toutes les tâches du présent plan
- [ ] **T1.6** Création des comptes nécessaires :
  - Compte Mistral AI (clé API dédiée projet)
  - Compte OVH (à provisionner en S8)
  - Compte Figma équipe

**Livrables S1-S2** : architecture validée, repo opérationnel, environnement Docker local fonctionnel.

#### Risques
- **R1** : Retard de validation architecture → mitigation : faire valider par e-mail si réunion impossible avant S3.

---

### 1.2 Sprint S1-S4 — Analyse données GTB (mai-juin 2026)

#### Tâches techniques
- [ ] **T2.1** **Cartographie des points GTB AER** — bloquant si CSV non transmis
  - Recevoir le CSV de supervision Niagara du site AER
  - Identifier les types de points : capteurs température, consignes, états (TOR), index énergie, alarmes
  - Documenter fréquences d'échantillonnage et profondeur historique
  - **Livrable** : `docs/cartographie_points_gtb.md` + script Python d'analyse
- [ ] **T2.2** **Benchmark stratégie d'intégration Niagara**
  - Analyser la doc Niagara fournie par AER
  - Comparer 3 approches :
    1. **iFrame** (POC — déjà décidé)
    2. **API REST Niagara** (`/obix/` ou `/bajaux/`)
    3. **Module Niagara natif** (Java, industrialisation)
  - **Livrable** : `docs/integration_niagara_benchmark.md` — décision documentée pour Phase 2
- [ ] **T2.3** **Spécification du schéma de données canonique**
  - Modèle interne indépendant de Niagara (futur multi-supervisions : Schneider, Siemens, Distech)
  - Tables : `sites`, `points`, `measurements` (hypertable Timescale), `alarms`, `equipments`
  - **Livrable** : `infra/sql/01_schema.sql` (cf. fichier dans le repo)

---

### 1.3 Sprint S5-S7 — Connaissance métier CVC (juin 2026)

#### Tâches techniques
- [ ] **T3.1** **Modélisation des alarmes CVC enrichies**
  - Construire un référentiel JSON/YAML : code alarme → libellé → équipement → criticité (1-5) → actions standards → conditions de déclenchement
  - Source : comptes rendus de dépannage AER + notices automates
  - **Livrable** : `backend/app/data/alarms_reference.json` (200+ entrées cible)
- [ ] **T3.2** **Base de cas de dépannage structurés**
  - Extraire ~50 cas types des comptes rendus AER
  - Format : { symptôme, contexte (équipement, conditions), diagnostic, action corrective, durée résolution }
  - **Livrable** : `backend/app/data/troubleshooting_cases.jsonl`
  - Ces cas alimenteront le RAG pour la pertinence du coach
- [ ] **T3.3** **Sessions de travail métier avec techniciens AER**
  - 2 sessions min. de 2h, dont 1 sur site
  - Objectif : valider sémantique des codes alarmes + comprendre raisonnement de diagnostic
  - **Livrable** : compte rendu + audio anonymisé pour ré-écoute équipe

#### Risques
- **R2** : Comptes rendus AER non structurés / partiels → mitigation : prévoir une étape OCR + extraction LLM si docs scannés.

**🎯 Fin de Phase 1 (S7) : démo intermédiaire prévue mi-juillet — montrer cartographie + premiers cas + démarrage backend.**

---

## Phase 2 — Pipeline & Intelligence IA (S8-S20)

### 2.1 Sprint S8-S10 — Prototype connecteur GTB → Backend (juillet 2026)

#### Tâches techniques
- [ ] **T4.1** **Activation VPN AER** — bloquant
  - Échange clés SSH + config VPN
  - Test connectivité Niagara depuis poste dev
- [ ] **T4.2** **Connecteur Niagara — module Python**
  - Implémenter `backend/app/connectors/niagara_client.py` :
    - Auth (token, fallback basic auth)
    - Lecture points temps réel via API Obix REST
    - Lecture historiques (Histories) avec pagination
    - Souscription alarmes (polling 30s en V1, WebSocket en V2)
  - **Livrable** : connecteur testé sur site AER + tests unitaires
- [ ] **T4.3** **Schéma de mapping Niagara → modèle canonique**
  - Fichier de mapping `point_id_niagara → point_id_canonique`
  - Service de normalisation des unités (Pa, kPa, °C, °F, kWh, m³)

---

### 2.2 Sprint S10-S12 — Base de données temporelles (août 2026)

#### Tâches techniques
- [ ] **T5.1** **Provisionnement OVH**
  - Serveur dédié (recommandation : Advance-2 avec 32GB RAM min.)
  - Installation Ubuntu 24.04 + Docker
  - Configuration firewall + fail2ban + accès SSH par clé
- [ ] **T5.2** **Déploiement TimescaleDB**
  - PostgreSQL 16 + extension TimescaleDB
  - Création des hypertables : `measurements`, `alarms_events`
  - Politique de rétention : raw 90j, agrégats 1h sur 2 ans
  - Continuous aggregates pour les vues temps réel
- [ ] **T5.3** **Import historiques CSV AER**
  - Script d'ingestion `backend/scripts/import_csv_history.py`
  - Validation qualité données (doublons, gaps, outliers)
  - Rapport de qualité d'import généré automatiquement
- [ ] **T5.4** **API Backend FastAPI V1**
  - Endpoints : `/api/v1/sites`, `/points`, `/measurements`, `/alarms`
  - Auth JWT
  - Documentation OpenAPI automatique
  - Tests d'intégration

---

### 2.3 Sprint S13-S17 — Intégration météo + RAG + Agent V1 (septembre 2026)

#### Tâches techniques
- [ ] **T6.1** **Intégration API Open-Meteo**
  - Service `backend/app/services/weather_service.py`
  - Récupération horaire + prévisions 48h
  - Cache Redis 1h
  - Jointure spatiale (lat/lon site → météo locale)
- [ ] **T6.2** **Base RAG opérationnelle (ChromaDB + LlamaIndex)**
  - Pipeline d'ingestion : PDF → chunking sémantique → embeddings → ChromaDB
  - Modèle d'embedding : `BAAI/bge-m3` (multilingue FR/EN, performant)
  - Indexer : notices automates, comptes rendus dépannage, bonnes pratiques CVC
  - Endpoint `/api/v1/rag/search` avec score de similarité
  - **Livrable** : ≥ 500 chunks indexés, F1-score qualitatif ≥ 0.7 sur 20 questions test
- [ ] **T6.3** **Agent IA V1 — Diagnostic alarme**
  - Architecture : LLM Mistral Large + RAG + contexte GTB (mesures dernières 24h)
  - Prompt système structuré (rôle technicien expert, format réponse)
  - Endpoint `/api/v1/agent/diagnose` (POST alarm_id → diagnostic + actions)
  - Mémoire de session (Redis, TTL 24h)
  - Fallback Gemini si Mistral indisponible
  - **Livrable** : agent testé sur 30 alarmes simulées + 10 alarmes réelles

#### Risques
- **R3** : Qualité RAG dépend des documents AER → mitigation : prévoir enrichissement avec docs publics CVC (guides RAGE, etc.)
- **R4** : Coût Mistral API si volumétrie élevée → mitigation : caching + Mistral Small pour les requêtes simples.

---

### 2.4 Sprint S18-S20 — Recommandation intelligente (octobre 2026)

#### Tâches techniques
- [ ] **T7.1** **Moteur de priorisation des alarmes**
  - Score = `criticité × impact_énergétique × fréquence × persistance × occupation_zone`
  - Service `backend/app/services/prioritization.py`
  - Cron job quotidien → génération du "plan d'action du jour"
  - Endpoint `/api/v1/action-plan/daily`
- [ ] **T7.2** **Moteur de règles métier CVC**
  - Encodage des règles expertes en YAML (lisible par les techniciens)
  - Exemples de règles :
    - Dérive consigne > 2°C pendant > 1h → alerte
    - Équipement actif hors plage horaire → alerte
    - ΔT entrée/sortie échangeur < 2K → encrassement suspecté
  - Moteur : `python-rule-engine` ou implémentation custom légère
  - **Livrable** : ≥ 30 règles métier validées par AER
- [ ] **T7.3** **Validation par techniciens AER**
  - Session 1/2 journée avec techniciens
  - Revue des recommandations sur 1 semaine de données réelles
  - Taux de pertinence cible : ≥ 80%

---

## Phase 3 — Interface, Énergie & Tests (S21-S30)

### 3.1 Sprint S21-S24 — Interface utilisateur (novembre 2026)

#### Tâches techniques
- [ ] **T8.1** **Maquettes Figma**
  - 3 écrans clés : Dashboard, Chatbot, Plan d'action
  - 3 profils utilisateurs : technicien, exploitant, responsable énergie
  - Session de validation AER (incluant techniciens terrain)
- [ ] **T8.2** **Frontend React — Dashboard**
  - Stack : React 18 + Vite + TypeScript + TailwindCSS + Recharts
  - Composants :
    - Vue temps réel (températures, consignes, états équipements)
    - Liste alarmes priorisées
    - Graphiques consommation énergie + croisement météo
    - Indicateurs (KPI) confort + énergie
  - WebSocket pour les mises à jour temps réel
- [ ] **T8.3** **Frontend React — Chatbot**
  - Interface conversationnelle structurée par rubriques :
    - 🔧 Dépannage
    - 📊 Analyse
    - ⚡ Énergie
    - 📋 Plan d'action
  - Streaming des réponses LLM (Server-Sent Events)
  - Affichage des sources RAG (transparence)
  - Boutons d'action contextuels ("Marquer comme traité", "Voir l'historique")
- [ ] **T8.4** **Intégration iFrame Niagara (POC)**
  - Tester l'embedding dans Niagara (header X-Frame-Options ALLOW-FROM)
  - Communication parent-iFrame via postMessage (sélection alarme depuis Niagara)

---

### 3.2 Sprint S25-S27 — Suivi énergétique (décembre 2026)

#### Tâches techniques
- [ ] **T9.1** **Module analyse de consommation**
  - Calcul des index énergie (kWh) par poste : chauffage, ECS, éclairage si dispo
  - Modèle de référence (baseline) par DJU (Degré Jour Unifié)
  - Détection de dérives : conso_observée vs conso_attendue (>15% sur 7j glissants)
  - Endpoint `/api/v1/energy/analysis`
- [ ] **T9.2** **Scénarios d'optimisation énergétique**
  - Identification automatique d'opportunités :
    - Plages horaires inutilisées
    - Consignes surdimensionnées
    - Délestage possible
  - Estimation des économies en kWh et € (prix moyen tarif tertiaire)
  - **Garde-fou** : recommandation = suggestion, jamais action automatique sur le terrain
  - Validation humaine obligatoire (workflow d'approbation)
- [ ] **T9.3** **Rapports énergétiques**
  - Export PDF mensuel automatique
  - Comparaison N vs N-1 + écart vs baseline météo-corrigée

#### Risques
- **R5** : Faux positifs dans détection de dérives → mitigation : seuils adaptatifs + validation humaine systématique avant toute suggestion d'action.

---

### 3.3 Sprint S28-S30 — Tests terrain & Démo finale (janvier 2027)

#### Tâches techniques
- [ ] **T10.1** **Plan de tests terrain**
  - Site : bâtiment AER (périmètre chauffage)
  - Durée : 2 semaines minimum
  - Scénarios :
    1. Détection d'alarmes réelles → vérification diagnostic IA
    2. Suggestion d'optimisation → validation par technicien
    3. Test de robustesse (panne réseau, redémarrage)
    4. Sécurité : tentative d'accès non autorisé
  - Outils : grille d'évaluation, journal incidents, métriques de précision
- [ ] **T10.2** **Itérations correctives**
  - Bugfix prioritaires
  - Ajustement des seuils et règles selon retours terrain
  - Mise à jour de la base RAG avec cas réels rencontrés
- [ ] **T10.3** **Rapport PFEE**
  - Document final : contexte, architecture, choix techniques, résultats, perspectives
  - 30-50 pages + annexes
  - Relecture AER + tuteur EPITA
- [ ] **T10.4** **Démo finale + soutenance**
  - Démo live sur GTB AER
  - Présentation devant AER + jury EPITA
  - **Deadline absolue : 31 janvier 2027**

---

## 5. Risques et plan de mitigation

| ID | Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Retard validation architecture | Faible | Moyen | Validation par e-mail si réunion impossible |
| R2 | Comptes rendus AER non structurés | Moyen | Haut | OCR + extraction LLM, prévoir 2 sem buffer |
| R3 | Qualité RAG insuffisante | Moyen | Haut | Enrichissement docs publics + itérations |
| R4 | Surcoût API Mistral | Faible | Moyen | Caching agressif + Mistral Small fallback |
| R5 | Faux positifs détection énergie | Haut | Moyen | Validation humaine systématique |
| R6 | Accès VPN AER retardé | Moyen | Haut | Travailler sur CSV en attendant + escalade |
| R7 | Intégration iFrame bloquée (CSP) | Moyen | Moyen | Plan B : ouverture popup au lieu d'iFrame |
| R8 | Indisponibilité technicien AER pour validation | Moyen | Haut | Planifier les sessions 3 sem à l'avance |
| R9 | Dépassement délai 31/01/2027 | Faible | Critique | Buffer S29-S30, MVP minimal défini en amont |
| R10 | Données GTB de mauvaise qualité (gaps, outliers) | Haut | Moyen | Pipeline de nettoyage automatique + alertes qualité |

---

## 6. Dépendances bloquantes côté AER

| Élément | Échéance souhaitée | Statut | Impact si retard |
|---|---|---|---|
| Documentation Niagara (API REST, modules) | S1-S2 | ⏳ | Bloque T2.2, T4.2 |
| Modules e-learning GTB | S2 | ⏳ | Bloque montée en compétences équipe |
| Jeux de données CSV (historiques) | S2 | ⏳ | Bloque T2.1, T5.3 |
| Comptes rendus de dépannage + notices | S4 | ⏳ | Bloque T3.1, T3.2, T6.2 |
| Clé API Mistral | S2 | ⏳ | Bloque T6.3 |
| Accès VPN site AER | S8 (juin) | ⏳ | **CRITIQUE** — bloque T4.1 |
| Disponibilité techniciens pour interviews | S5-S7 | ⏳ | Bloque T3.3, T7.3 |
| Validation maquettes Figma | S22 | ⏳ | Bloque T8.2 |
| Site AER disponible pour tests terrain | S28-S30 | ⏳ | Bloque T10.1 |

---

## 7. Critères de succès du MVP

Le MVP livré le **31 janvier 2027** devra remplir l'ensemble des critères suivants :

### Critères fonctionnels
- ✅ Connecteur Niagara opérationnel sur GTB AER (lecture temps réel + historique)
- ✅ Backend ingère et stocke ≥ 30 jours de données réelles continues
- ✅ Agent IA répond pertinemment (≥ 80% sur grille AER) à des questions de diagnostic d'alarme
- ✅ Plan d'action quotidien généré automatiquement
- ✅ Dashboard React affiche données temps réel + chatbot fonctionnel
- ✅ Module énergie détecte ≥ 1 dérive réelle constatée pendant les tests
- ✅ Au moins 2 scénarios d'optimisation suggérés et validés par techniciens

### Critères non-fonctionnels
- ✅ Hébergement OVH conforme RGPD
- ✅ Temps de réponse chatbot < 5s (P95)
- ✅ Latence ingestion données < 30s (point GTB → backend)
- ✅ Disponibilité ≥ 99% sur la période de tests
- ✅ Pas d'incident de sécurité (audit basique : OWASP Top 10)
- ✅ Documentation complète (architecture, déploiement, API, user guide)

### Critères de démonstration
- ✅ Démo physique réussie chez AER ou en visio avec écran partagé
- ✅ Rapport PFEE livré
- ✅ Soutenance jury validée

---

## 8. Gouvernance & rituels

### Rituels d'équipe
- **Hebdomadaire** : stand-up court (15 min) — chaque membre, blocages
- **Bihebdomadaire** : point AER (1h) — démo incrémentale, décisions
- **Mensuel** : retro Scrum-Ban (1h) — amélioration continue
- **Fin de phase** : démo physique + revue d'avancement avec AER

### Outils
- **Code** : GitHub (`coach-ia-gtb`)
- **Project Management** : GitHub Projects
- **Communication** : Slack/Teams (à définir avec AER)
- **Design** : Figma
- **Documentation** : Markdown dans le repo + Notion pour les notes vivantes

### Définition de "Done"
Une tâche est "Done" quand :
1. Code écrit et commité sur branche feature
2. Tests unitaires écrits (couverture ≥ 70%)
3. PR review validée par au moins 1 pair
4. Documentation à jour (README + docstrings)
5. CI verte (lint + tests)
6. Merge sur `develop`
7. Démontrable au point AER suivant

---

**Dernière mise à jour** : 13 juin 2026
**Responsable du plan** : Équipe IA EPITA × AER
