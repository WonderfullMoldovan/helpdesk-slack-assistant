````markdown
# ADR-005: pgvector over Specialized Vector DB

**Status:** Accepted
**Date:** 2026-05-13

## Context

Il sistema richiede una ricerca per similarità vettoriale per il RAG su una piccola knowledge 
base (~30 documenti). Esistono molteplici opzioni di storage vettoriale, ciascuna con 
trade-off diversi.

Forze:
- La semplicità operativa è importante (sviluppatore unico, ambito del capstone)
- La scala è piccola (~30 documenti = al massimo qualche migliaio di chunk)
- PostgreSQL è già richiesto per altri dati
- Si vuole una decisione difendibile, non un "ho usato lo strumento di tendenza"


## Decision

Usare **pgvector** — un'estensione di PostgreSQL che fornisce tipi di dato vettoriali e 
operatori di ricerca per similarità — come vector store. Gli embedding sono memorizzati 
insieme ai documenti sorgente nella stessa istanza PostgreSQL usata per gli altri 
dati persistenti.

## Alternatives Considered

**1. Pinecone**
- Scartata: servizio hosted con vendor lock-in; il costo per la scala del capstone 
  è ingiustificato; introduce una dipendenza esterna per un dataset piccolo

**2. Qdrant (self-hosted o cloud)**
- Scartata: aggiunge un componente operativo senza un beneficio chiaro alla nostra scala; 
  Qdrant diventa prezioso con milioni di vettori e filtraggio avanzato — 
  non è il nostro caso

**3. Weaviate**
- Scartata: ragionamento simile a quello di Qdrant; il set di funzionalità più ricco (moduli 
  integrati, GraphQL) resta inutilizzato nella nostra implementazione RAG minimale

**4. FAISS (in-process, senza persistenza)**
- Scartata: solo in memoria; perde gli embedding al riavvio; richiederebbe 
  un livello di persistenza custom; non praticabile per un servizio stateful

**5. Azure AI Search**
- Scartata: si adatta meglio alla ricerca ibrida out of the box, ma ci lega ad 
  Azure e aggiunge costi; la nostra ricerca ibrida sarà implementata con pgvector 
  + la ricerca full-text di Postgres, che è sufficiente

## Consequences

**Positive:**
- Un servizio in meno da deployare e monitorare
- Dati vettoriali collocati insieme ai metadati — nessuna sincronizzazione necessaria
- Il tooling di Postgres (psql, dbeaver, migrazioni) funziona anche per i dati vettoriali
- Costo: zero spese aggiuntive di servizio

**Negative:**
- Tetto prestazionale: gli indici IVFFlat / HNSW di pgvector sono competitivi ma 
  non i migliori della categoria a scale molto elevate (milioni e più di vettori)
- Limitato agli operatori di PostgreSQL; mancano alcune primitive di filtraggio avanzato 
  disponibili nei DB specializzati

**Percorso di migrazione:**
- A partire da ~100k+ vettori, valutare la migrazione a Qdrant o simili
- La migrazione toccherebbe solo il modulo RAG (il pattern Repository isola lo 
  storage dagli agenti)

**Neutre:**
- pgvector è in sviluppo attivo; il divario prestazionale con i DB specializzati 
  si riduce nel tempo
````