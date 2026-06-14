# Cartographie canonique des points GTB

> Template à compléter avec AER une fois la documentation Niagara reçue (jalon J2).
> Cette cartographie est la **source de vérité** pour la modélisation côté base
> et l'interprétation par les agents IA.

---

## 1. Méthodologie

1. **Inventaire brut** depuis l'export Niagara (CSV ou parcours Obix).
2. **Normalisation** : on regroupe les points par famille fonctionnelle et on
   leur affecte un **code canonique** indépendant du nom Niagara.
3. **Mapping** : table de correspondance `niagara_path` ↔ `code_canonique`.
4. **Documentation** : pour chaque point, on précise unité, type, plage, criticité.

---

## 2. Familles d'équipements (taxonomie)

```
Bâtiment
├── Production de chaleur
│   ├── Chaudière (gaz, fioul, biomasse)
│   ├── PAC (air/eau, eau/eau)
│   └── Sous-station urbaine
├── Production de froid
│   ├── Groupe froid
│   └── Tour aéro-réfrigérante
├── Distribution
│   ├── Circuit chauffage
│   ├── Circuit ECS
│   └── Pompes de circulation
├── Émission
│   ├── Radiateurs
│   ├── Plancher chauffant
│   └── Ventilo-convecteurs
├── Ventilation
│   ├── CTA simple flux
│   ├── CTA double flux
│   └── VMC
└── Comptage & énergie
    ├── Compteur gaz
    ├── Compteur électricité
    └── Compteur calorifique
```

---

## 3. Types de points (enum `PointType`)

| Type | Code | Description | Exemple |
|------|------|-------------|---------|
| Mesure | `measurement` | Grandeur physique instantanée | T° départ, débit, CO2 |
| Consigne | `setpoint` | Valeur cible imposée à la régulation | Consigne T° ambiante 21 °C |
| État | `state` | Variable discrète (marche/arrêt, mode) | État chaudière (0/1) |
| Commande | `command` | Sortie écriture (Phase 2 uniquement) | Forçage vanne |
| Alarme | `alarm` | Événement d'alerte | Défaut brûleur |
| Comptage | `counter` | Index cumulatif | Conso gaz cumulée |

---

## 4. Convention de nommage canonique

Format : `<GRANDEUR>_<LOCALISATION>_<INDEX?>`

| Grandeur | Code | Unité |
|----------|------|-------|
| Température départ | `T_DEP` | °C |
| Température retour | `T_RET` | °C |
| Température ambiante | `T_AMB` | °C |
| Température extérieure | `T_EXT` | °C |
| Hygrométrie | `HR` | % |
| Pression | `P` | bar |
| Débit | `Q` | m³/h |
| CO2 | `CO2` | ppm |
| Consigne | `SP_<...>` | (idem grandeur) |
| État | `ETAT_<...>` | bool |
| Conso gaz | `E_GAZ` | kWh |
| Conso élec | `E_ELEC` | kWh |

**Exemples** : `T_DEP_CHAUD_01`, `SP_AMB_RDC_BUREAU`, `CO2_ETG2_SALLE_REUNION`.

---

## 5. Tableau de cartographie (à remplir avec AER)

| Code canonique | Famille équipement | Type | Unité | Plage min | Plage max | Criticité | Chemin Niagara | Commentaire |
|----------------|--------------------|------|-------|-----------|-----------|-----------|----------------|-------------|
| `T_DEP_CHAUD_01` | production_chaleur | measurement | °C | 20 | 90 | high | `station:/Bld/Chaud01/Tdep` | Capteur PT1000 |
| `T_RET_CHAUD_01` | production_chaleur | measurement | °C | 15 | 80 | medium | `station:/Bld/Chaud01/Tret` | |
| `SP_CHAUD_01` | production_chaleur | setpoint | °C | 50 | 80 | high | `station:/Bld/Chaud01/SP` | |
| `ETAT_CHAUD_01` | production_chaleur | state | — | 0 | 1 | high | `station:/Bld/Chaud01/Run` | 1=marche |
| `T_SOUF_CTA_RDC` | ventilation | measurement | °C | 10 | 35 | medium | `station:/Bld/CTA_RDC/Tsouf` | |
| `CO2_RDC_BUREAU` | ventilation | measurement | ppm | 350 | 2000 | medium | `station:/Bld/CTA_RDC/CO2` | Seuil 1000 ppm |
| `E_GAZ_TOTAL` | comptage | counter | kWh | 0 | — | low | `station:/Comptage/Gaz` | Index cumulatif |
| … | … | … | … | … | … | … | … | … |

> 📌 **À faire avec AER** : extraire le CSV complet depuis Niagara, le déposer
> dans `docs/private/` puis dérouler le mapping ligne par ligne en S5-S6.

---

## 6. Stockage en base

Table `points` (Postgres) :

```sql
points (
  id            UUID PK,
  equipment_id  UUID FK → equipments,
  code          VARCHAR UNIQUE,        -- code canonique
  niagara_path  VARCHAR,               -- chemin Obix d'origine
  label         VARCHAR,
  point_type    ENUM(PointType),
  unit          VARCHAR,
  range_min     FLOAT,
  range_max     FLOAT,
  metadata      JSONB                   -- libre : marque capteur, étalonnage, etc.
)
```

Table `measurements` (TimescaleDB hypertable) :

```sql
measurements (
  time          TIMESTAMPTZ NOT NULL,
  point_id      UUID NOT NULL,
  value_num     DOUBLE PRECISION,
  value_bool    BOOLEAN,
  quality       SMALLINT,                -- 0=ok, 1=substituée, 2=invalide
  PRIMARY KEY (point_id, time)
)
```

---

## 7. Validation qualité

À l'ingestion, chaque mesure passe par :

1. **Bornes** : valeur hors `[range_min ; range_max]` → `quality = 2`, log.
2. **Continuité** : delta vs. mesure précédente > seuil → flag à investiguer.
3. **Fraîcheur** : si pas de point depuis > 5 × poll_interval → alarme "perte capteur".

Ces règles sont implémentées dans le pipeline d'ingestion (à coder en S8-S10).
