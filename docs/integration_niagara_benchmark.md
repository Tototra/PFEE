# Benchmark — Stratégies d'intégration Niagara

> Document décisionnel pour le choix d'intégration côté supervision Niagara
> Tridium. À valider au comité d'architecture **S5** avec AER.

---

## 1. Contexte

Niagara est une plateforme propriétaire de Tridium qui pilote la GTB AER.
Elle expose plusieurs surfaces d'intégration. Le choix impacte directement :

- Le **délai de mise en œuvre** (critique : MVP en 30 semaines à 1 j/sem).
- La **richesse fonctionnelle** (lecture, écriture, événementiel).
- Le **coût** (licences, développement, maintenance).
- La **dépendance AER** (accès VPN, support Niagara interne).

---

## 2. Options évaluées

### Option A — iFrame Niagara dans le frontend

**Principe** : on n'intègre pas Niagara, on l'**affiche** dans une iframe
au sein de notre frontend React.

| Critère | Évaluation |
|---------|------------|
| Effort dev | ⭐ Très faible (1-2 jours) |
| Délai mise en œuvre | ⭐⭐⭐⭐⭐ Immédiat |
| Lecture des données | ❌ L'IA n'a **aucun accès** aux données |
| Écriture / commandes | ❌ Impossible côté IA |
| Cohérence UX | ⚠️ Deux UIs côte à côte |
| Coût | ⭐⭐⭐⭐⭐ Nul |
| Verrou Niagara | Bloque la suite |

> **Verdict** : utile uniquement comme **mise en main rapide** pour la démo
> S1-S2. Inutilisable pour les cas d'usage IA. **Non retenu pour MVP**.

---

### Option B — Obix REST (HTTP/XML standard Niagara) ✅ **MVP**

**Principe** : Niagara expose nativement les points et alarmes via
**Project Haystack / Obix** sur HTTP. On code un client REST en Python qui
poll les valeurs et les insère dans TimescaleDB.

| Critère | Évaluation |
|---------|------------|
| Effort dev | ⭐⭐⭐ Modéré (~10-15 j/h) |
| Délai mise en œuvre | ⭐⭐⭐⭐ 2-3 semaines |
| Lecture des données | ✅ Tous les points exposés |
| Écriture / commandes | ⚠️ Possible mais à éviter en MVP (sécurité) |
| Événementiel | ❌ Pas de push, polling uniquement |
| Latence | ~ poll interval (30-60 s) |
| Coût | ⭐⭐⭐⭐ Aucun ajout licence |
| Dépendance AER | VPN + compte service Niagara |

> **Verdict** : **choix retenu pour le MVP**. Compromis effort / valeur optimal.
> Limite : pas de temps réel, polling consomme côté Niagara.

Implémentation : `backend/app/connectors/niagara_client.py`.

---

### Option C — Module Niagara natif (Java / Niagara AX SDK)

**Principe** : on développe un **module Niagara** déployé directement sur
la station. Il pousse les événements (changements de valeur, alarmes) en
temps réel vers le backend via webhook.

| Critère | Évaluation |
|---------|------------|
| Effort dev | ⭐ Élevé (Java + SDK Niagara ~ 30-40 j/h) |
| Délai mise en œuvre | ❌ 2-3 mois |
| Lecture des données | ✅ Optimale |
| Écriture / commandes | ✅ Native |
| Événementiel | ⭐⭐⭐⭐⭐ Push temps réel |
| Latence | < 1 s |
| Coût | Licence Niagara dev + formation |
| Dépendance AER | Forte (validation déploiement station) |

> **Verdict** : **cible Phase 3** (après MVP). À engager une fois les cas
> d'usage validés et le besoin de temps réel confirmé.

---

### Option D — Bus de messages (MQTT / Kafka) côté Niagara

**Principe** : Niagara publie sur un broker MQTT, le backend s'abonne.

| Critère | Évaluation |
|---------|------------|
| Effort dev Niagara | ⭐⭐ Élevé (config Niagara + module MQTT) |
| Effort dev backend | ⭐⭐⭐⭐ Standard |
| Lecture | ✅ Push temps réel |
| Écriture | ⚠️ Selon implémentation |
| Coût | Broker à héberger |
| Maturité Niagara | Variable selon version client |

> **Verdict** : alternative à C si le module MQTT est déjà déployé chez AER.
> À investiguer en discussion d'architecture.

---

## 3. Synthèse comparative

| Critère | A (iFrame) | **B (Obix REST)** | C (Module natif) | D (MQTT) |
|---------|:---------:|:-----------------:|:----------------:|:--------:|
| Délai | ⭐⭐⭐⭐⭐ | **⭐⭐⭐⭐** | ⭐⭐ | ⭐⭐⭐ |
| Effort dev | ⭐⭐⭐⭐⭐ | **⭐⭐⭐** | ⭐ | ⭐⭐⭐ |
| Données dispo IA | ❌ | **✅** | ✅ | ✅ |
| Temps réel | ❌ | ⚠️ polling | ✅ | ✅ |
| Écriture | ❌ | ⚠️ | ✅ | ⚠️ |
| Adéquation MVP | ❌ | **✅** | ❌ | ⚠️ |
| Adéquation Phase 3 | ❌ | ⚠️ scale-up | **✅** | ✅ |

---

## 4. Décision

| Phase | Stratégie |
|-------|-----------|
| **POC (S1-S5)** | Option A (iframe) **uniquement pour la démo UI**, en parallèle du dev B |
| **MVP (S5-S25)** | **Option B (Obix REST)** — implémentation complète |
| **Phase 3 (post-MVP)** | Migration vers **Option C ou D** selon retours utilisateurs |

---

## 5. Points à clarifier avec AER

- [ ] Version exacte de Niagara installée (4.x ?) → conditionne l'API Obix.
- [ ] Endpoint Obix exposé ? URL, port, certificat.
- [ ] Compte de service dédié pour lecture (login/MDP).
- [ ] Politique réseau : VPN ou IP whitelistée ?
- [ ] Volume estimé de points à poller (impact perf Niagara).
- [ ] Disponibilité d'un environnement de test (station de démo).

---

## 6. Références

- Documentation Tridium Niagara 4 — Obix Driver Guide
- Project Haystack — https://project-haystack.org/
- BACnet/IP (alternative si Niagara expose BACnet)
