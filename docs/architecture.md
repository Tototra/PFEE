# Architecture technique — Coach IA GTB

> Référence consolidée à partir du document AER *CoachIA_Architecture_Technique_V1*.
> À mettre à jour à chaque revue d'architecture (Comité bi-mensuel).

---

## 1. Vue d'ensemble

L'application est organisée en **4 couches** clairement séparées :

| Couche | Rôle | Stack |
|--------|------|-------|
| **C1 — Connecteur Niagara** | Lecture des points & alarmes depuis la supervision | Python httpx + Obix REST / Phase 3 : module Java natif |
| **C2 — Backend** | API REST, persistance, orchestration | FastAPI · SQLAlchemy · TimescaleDB · Redis |
| **C3 — Agents IA + RAG** | Diagnostic, priorisation, génération de réponses | Mistral Large · Gemini (fallback) · ChromaDB · `bge-m3` |
| **C4 — Frontend** | Dashboard + chatbot exploitant | React 18 · Vite · TypeScript · Tailwind · Recharts |

---

## 2. Détail des couches

### C1 — Connecteur Niagara

- **Protocole MVP** : Obix REST (HTTP/HTTPS, XML), polling configurable
  (`NIAGARA_POLL_INTERVAL_SEC`, défaut 60 s).
- **Auth** : Basic Auth sur compte service dédié (lecture seule).
- **Points exposés** : mesures (°C, %, ppm…), consignes, états, alarmes actives.
- **Évolution Phase 3** : module Niagara natif (Java/Niagara AX SDK) pour
  pousser les événements en temps réel via webhook → backend (cf. benchmark
  dans `integration_niagara_benchmark.md`).
- **Implémentation** : `backend/app/connectors/niagara_client.py`
  (classe `NiagaraClient`, `NiagaraPoller` tâche d'arrière-plan).

### C2 — Backend

- **API REST** sous `/api/v1` :
  - `sites/`, `points/`, `alarms/` (lecture + endpoints métier)
  - `agent/diagnose` (POST synchrone), `agent/chat/stream` (SSE)
  - `energy/analysis`, `energy/optimizations`
  - `health/`, `health/ready`
- **Persistance** :
  - **Postgres** pour le métier (sites, équipements, points, alarmes, utilisateurs).
  - **TimescaleDB** (extension) pour les séries temporelles (hypertables
    `measurements` et `alarm_events`, agrégats continus horaires / journaliers,
    rétention 90 j brut + 2 ans agrégés, compression au-delà de 7 j).
- **Cache** : Redis (résultats LLM courte durée, météo, rate limiting).
- **Validation** : Pydantic v2.
- **Observabilité** : `structlog` en JSON, prometheus-fastapi-instrumentator
  prévu (à brancher en Phase 2).

### C3 — Agents IA + RAG

- **LLM principal** : Mistral Large via API officielle. Streaming SSE pour
  le chatbot.
- **Fallback** : Gemini 1.5 Pro si Mistral indisponible (`LLMProvider` gère
  la bascule).
- **RAG** :
  - Vector store **ChromaDB** persistant.
  - Embeddings **BAAI/bge-m3** (multilingue, bonne perf FR).
  - `top_k` configurable (`RAG_TOP_K`, défaut 5).
  - Filtrage par métadonnées (site, équipement, famille).
- **Sources alimentant le RAG** :
  - Cas de troubleshooting (table `troubleshooting_cases`).
  - Documentation constructeur PDF (ingestion via `ingest_pdf`).
  - Comptes rendus d'intervention AER.
  - Normes / règles métier CVC.
- **Règles métier déterministes** : `business_rules.yaml` évalué par
  `RulesEngine` (sandbox sans `__builtins__`). Permet de détecter des
  patterns connus sans LLM (ex. dérive consigne > 3°C pendant > 30 min).
- **Priorisation des alarmes** : score pondéré 5 dimensions
  (criticité 35 %, énergie 25 %, fréquence 15 %, persistance 15 %, occupation 10 %).

### C4 — Frontend

- **Pages MVP** :
  - **Dashboard** : KPI (T° moyenne, conso, alarmes actives, DJU),
    plan d'action du jour, graphique 24 h.
  - **Chatbot** : 4 rubriques (Dépannage, Analyse, Énergie, Plan d'action),
    streaming des réponses, historique.
  - **Énergie** (placeholder en S20).
- **Routing** : React Router v6.
- **State / data** : React Query (cache, refetch).
- **Streaming SSE** : `fetch` + `TextDecoder` (cf. `apiClient.chatStream`).
- **Auth (Phase 2)** : JWT côté backend, stockage `httpOnly cookie`.

---

## 3. Flux clés

### 3.1. Diagnostic d'une alarme

```
Niagara  ──poll──►  Backend  ──insert──►  TimescaleDB
                       │
                       ▼
              AlarmPrioritizer (score)
                       │
                       ▼
               DiagnosticAgent
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   contexte points  RAG (cas)    règles métier
        └──────────────┼──────────────┘
                       ▼
                 Mistral / Gemini
                       │
                       ▼
            DiagnosticResult (4 sections)
                       │
                       ▼
                  Frontend (SSE)
```

### 3.2. Plan d'action quotidien

1. Récupération des alarmes actives sur les dernières 24 h.
2. Enrichissement : équipement, occupation, météo, fréquence.
3. Calcul du score par `AlarmPrioritizer`.
4. Top N → endpoint `/alarms/action-plan/daily` → carte dashboard.

---

## 4. Sécurité

| Domaine | Mesure |
|---------|--------|
| Secrets | `.env` jamais committé, `.env.example` fourni |
| Authentification | JWT (Phase 2), refresh token, RBAC (admin/exploitant) |
| Réseau Niagara | VPN AER, IP whitelistée côté supervision |
| LLM | Pas d'envoi de données nominatives, anonymisation des prompts |
| Données | Chiffrement at-rest (volumes OVH), TLS partout |
| Logs | Pas de secrets en clair, masquage des tokens |
| Dépendances | `pip-audit` / `npm audit` en CI (à ajouter) |

---

## 5. Déploiement (cible Phase 2)

- **Hébergement** : OVH (instance dédiée + managed Postgres).
- **Orchestration** : docker-compose pour le POC, K8s envisagé en V2.
- **CI/CD** : GitHub Actions (lint + tests + build images) → push registry → déploiement manuel pour MVP.
- **Monitoring** : Grafana + Prometheus (Phase 2).
- **Backups** : snapshots quotidiens Postgres, rétention 30 j.

---

## 6. Choix techniques justifiés

| Choix | Alternative écartée | Raison |
|-------|---------------------|--------|
| Mistral Large | OpenAI GPT-4o | Hébergement EU (RGPD), partenariat AER |
| Gemini fallback | Aucun | Continuité de service si Mistral indispo |
| TimescaleDB | InfluxDB | SQL standard, jointures avec métier, extension Postgres |
| ChromaDB | Pinecone, Weaviate | Open source, embeddable, pas de SaaS externe |
| FastAPI | Django, Flask | Async natif, OpenAPI auto, Pydantic v2 |
| React + Vite | Next.js | SPA suffit, build léger, pas de besoin SSR |
| Tailwind | CSS Modules | Vitesse de prototypage |
| Niagara Obix REST (MVP) | Module natif d'emblée | Délai POC court, complexité Niagara AX SDK |

---

## 7. Points ouverts

- [ ] Décision finale sur l'authentification utilisateur (S15).
- [ ] Modèle d'embeddings : confirmer `bge-m3` après évaluation sur corpus AER.
- [ ] Format précis des exports CSV AER (à recevoir).
- [ ] Stratégie de versioning des prompts (Phase 2).
- [ ] Tests de charge sur le polling Niagara à fort volume de points (> 5 000).
