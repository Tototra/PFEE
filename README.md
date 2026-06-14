# Coach IA GTB

> **Assistant intelligent pour la Gestion Technique du Bâtiment**
> PFEE EPITA × AER — Promotion 2026/2027 · Échéance MVP : **31 janvier 2027**

Coach IA GTB est un copilote conversationnel destiné aux exploitants GTB. Il
s'intègre à une supervision **Niagara** (Tridium) pour aider à diagnostiquer
les dérives, prioriser les alarmes, optimiser la consommation énergétique et
guider la maintenance corrective sur la base du contexte temps réel du
bâtiment et d'une base de connaissance métier (RAG).

---

## 🎯 Objectifs

| # | Cas d'usage | Description |
|---|-------------|-------------|
| 1 | **Dépannage assisté** | Analyse d'une alarme → causes probables, ordre d'investigation, références aux cas similaires. |
| 2 | **Analyse de mesure** | Lecture contextualisée d'une dérive (température, débit…) avec corrélation météo / occupation. |
| 3 | **Optimisation énergie** | Détection de gisements d'économies (loi d'eau, intermittence, surconsommation). |
| 4 | **Plan d'action du jour** | Top N alarmes priorisées par un score multi-critères (criticité × énergie × occupation × persistance). |

---

## 🏗️ Architecture

```
┌──────────────────┐   ┌──────────────────────────────┐   ┌────────────────────┐
│  C1 Niagara      │   │  C2 Backend (FastAPI)        │   │  C4 Frontend       │
│  ──────────      │◄─►│  • API REST + SSE            │◄─►│  React + Vite + TS │
│  Connecteur Obix │   │  • TimescaleDB (séries temp.)│   │  Dashboard         │
│  Polling 60 s    │   │  • Postgres (métier)         │   │  Chatbot streaming │
└──────────────────┘   │  • Redis (cache)             │   └────────────────────┘
                       │                              │
                       │     C3 Agents IA + RAG       │
                       │  • Claude (Mistral/Gemini fb)│
                       │  • ChromaDB + bge-m3         │
                       │  • Règles métier YAML        │
                       │  • Open-Meteo (DJU)          │
                       └──────────────────────────────┘
```

Détails dans **[`docs/architecture.md`](docs/architecture.md)**.

---

## 🚀 Démarrage rapide

### Prérequis

- Docker & Docker Compose (recommandé)
- *ou* Python 3.11+ et Node 20+ pour un setup local

### En 4 commandes

```bash
git clone <repo>
cd coach-ia-gtb
cp .env.example .env          # puis renseigner MISTRAL_API_KEY au minimum
make up                       # démarre postgres, redis, backend, frontend
make migrate && make seed     # crée le schéma TimescaleDB + données démo
```

Vérification :

- Backend Swagger : http://localhost:8000/docs
- Frontend : http://localhost:5173
- Health check : `curl http://localhost:8000/api/v1/health`

### Commandes utiles

```bash
make help        # liste toutes les cibles
make logs        # tail logs de la stack
make test        # tests backend + frontend
make lint        # lint complet
make shell-db    # psql sur la base
make down        # stoppe la stack
```

---

## 📁 Structure du projet

```
coach-ia-gtb/
├── PLAN_ACTION.md             # Plan d'action complet (10 milestones, S1→S30)
├── backend/                   # FastAPI + SQLAlchemy + RAG
│   ├── app/
│   │   ├── api/v1/            # Routers REST (sites, points, alarms, agent, energy)
│   │   ├── agents/            # Agent diagnostic + provider LLM (Mistral/Gemini)
│   │   ├── connectors/        # Client Niagara (Obix)
│   │   ├── core/              # Config, DB async, logging
│   │   ├── data/              # business_rules.yaml
│   │   ├── models/            # Schéma canonique GTB
│   │   ├── rag/               # Pipeline ChromaDB + embeddings
│   │   └── services/          # Priorisation, météo, moteur de règles
│   ├── scripts/               # seed_demo_data.py
│   └── tests/
├── frontend/                  # React 18 + Vite + Tailwind + Recharts
│   └── src/
│       ├── pages/             # Dashboard, Chatbot
│       ├── services/          # apiClient (axios + SSE)
│       └── types/
├── niagara-module/            # (Phase 3) module natif Java pour intégration profonde
├── infra/
│   ├── docker/                # Dockerfiles backend + frontend
│   ├── nginx/                 # Config nginx (SPA + proxy API + SSE)
│   └── sql/                   # Schéma TimescaleDB
├── docs/                      # Cartographie, benchmarks, architecture
├── .github/workflows/         # CI
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## 🧪 Tests

```bash
make test-backend    # pytest, couverture incluse
make test-frontend   # tests Vitest (à compléter)
```

---

## 📘 Documentation

| Fichier | Contenu |
|---------|---------|
| [`PLAN_ACTION.md`](PLAN_ACTION.md) | Plan d'action détaillé : 10 milestones, 30 semaines, risques, dépendances AER |
| [`docs/architecture.md`](docs/architecture.md) | Architecture technique des 4 couches |
| [`docs/cartographie_points_gtb.md`](docs/cartographie_points_gtb.md) | Modélisation canonique des points GTB |
| [`docs/integration_niagara_benchmark.md`](docs/integration_niagara_benchmark.md) | Benchmark iFrame vs REST vs module natif |

---

## 🤝 Contribuer

Branches : `feature/<sujet>` → PR vers `develop` → merge vers `main` sur release.
CI obligatoire (lint + tests + build Docker) avant merge.

Convention de commit : [Conventional Commits](https://www.conventionalcommits.org/).

---

## ⚠️ Données confidentielles

Les documents et exports fournis par AER (CSV historique, comptes rendus,
documentation Niagara client) sont **strictement confidentiels** et ne
doivent **jamais** être committés. Les déposer dans `docs/private/` qui est
gitignored.

---

## 📄 Licence

Projet pédagogique EPITA — propriétaire AER. Tous droits réservés.
