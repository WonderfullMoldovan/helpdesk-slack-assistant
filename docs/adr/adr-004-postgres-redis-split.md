````markdown
# ADR-004: PostgreSQL as Source of Truth + Redis as Performance Layer

**Status:** Accepted
**Date:** 2026-05-13

## Context

Il sistema richiede uno storage persistente per lo stato delle conversazioni, le escalation, 
gli embedding e le mappature degli utenti. Beneficia inoltre di caching, deduplicazione 
e persistenza dei job per lo scheduler.

Dati diversi hanno pattern di accesso e requisiti di durabilità diversi.

## Decision

Usare **PostgreSQL** come unica fonte di verità per tutti i dati durevoli, interrogabili 
e relazionali. Usare **Redis** come livello prestazionale per tre concern distinti:

1. **Cache** — chunk della KB e (opzionalmente) risposte LLM ad accesso frequente
2. **Deduplicazione** — ID di evento di breve durata con TTL per l'idempotenza di Slack
3. **Backend dello scheduler** — RedisJobStore di APScheduler per i job persistiti

**Invariante rigida:** Redis non è mai la fonte di verità. Se Redis viene azzerato, 
il sistema perde prestazioni, non correttezza.

## Alternatives Considered

**1. Solo PostgreSQL (senza Redis)**
- Scartata: praticabile alla scala del capstone, ma perde tre vantaggi specifici:
  (a) il TTL di Redis per la deduplicazione è più semplice della scadenza delle righe in Postgres,
  (b) APScheduler ha un RedisJobStore maturo ma alternative Postgres immature,
  (c) la latenza di un cache hit su Redis è circa 10 volte più bassa di quella di Postgres
- Il guadagno in semplicità operativa (un servizio in meno) non giustifica la perdita

**2. Solo Redis (senza PostgreSQL)**
- Scartata: nessuna garanzia ACID, nessuna query relazionale, nessuna durabilità 
  di livello audit; il PostgresSaver di LangGraph non ha un equivalente Redis di pari maturità

**3. Database separati per tipo di dato (DB di audit, DB di stato, ecc.)**
- Scartata: suddivisione prematura; complessità senza una scala che la giustifichi


## Consequences

**Positive:**
- Ogni livello di storage è usato per i suoi punti di forza
- Un'unica verità ACID semplifica il ragionamento sulla consistenza
- La logica di invalidazione della cache è isolata (TTL di Redis) anziché sparsa nel codice
- Dimostra la comprensione dei principi della persistenza poliglotta

**Negative:**
- Due componenti di storage da deployare, monitorare e sottoporre a backup
- Gli sviluppatori devono capire quale dato vive dove (mitigato dal pattern Repository 
  che nasconde la scelta)
- Lo sviluppo locale richiede che entrambi i servizi siano in esecuzione

**Neutre:**
- Entrambi disponibili come servizi gestiti in Azure (PostgreSQL Flexible Server, 
  Cache for Redis), quindi il deployment di produzione non aggiunge onere operativo
````