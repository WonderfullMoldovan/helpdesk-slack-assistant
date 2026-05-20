````markdown
# ADR-001: Modular Monolith over Microservices

**Status:** Accepted
**Date:** 2026-05-13

## Context

L'IT Helpdesk Slack Assistant richiede molteplici responsabilità: integrazione 
con Slack, orchestrazione dell'LLM, recupero della conoscenza, stato persistente, 
job programmati. Ognuna potrebbe plausibilmente essere un servizio separato.

Forze che hanno orientato la decisione:
- Sviluppatore unico, tempistica di 10–14 giorni
- Ambito del capstone: nessun carico di produzione reale
- Necessità di dimostrare il ragionamento architetturale in sede di revisione
- Il percorso di evoluzione futura è importante — la decisione non deve mettere in un vicolo cieco

## Decision

Costruire il sistema come un **monolite modulare**: una singola applicazione Python 
distribuibile, organizzata internamente in moduli con confini chiaramente definiti che 
corrispondono ai sottodomini (adapter Slack, grafo degli agenti, RAG, tool, repository, 
observability).

## Alternatives Considered

**1. Microservizi (servizi separati per Slack handler, agent runner, RAG, scheduler)**
- Scartata: overhead operativo sproporzionato rispetto all'ambito; uno sviluppatore unico 
  non può mantenere in modo significativo i contratti tra servizi in 14 giorni
- I benefici reali (deployment indipendente, autonomia del team) non si applicano a 
  un progetto con un solo sviluppatore

**2. Funzioni serverless (una funzione per agente / handler)**
- Scartata: l'esecuzione stateful degli agenti con checkpoint non si adatta al modello 
  delle funzioni di breve durata; i cold start aggiungono latenza a flussi già di 5–15s; l'integrazione 
  di LangGraph con FaaS è immatura

**3. Script unico (nessuna separazione in moduli)**
- Scartata: la difendibilità in sede di revisione richiede una struttura architetturale visibile; 
  il codice piatto è tecnicamente un "monolite" ma vanifica lo scopo


## Consequences

**Positive:**
- Singolo artefatto di deployment, singolo repo git, sviluppo locale semplice
- Chiamate di funzione in-process — nessun overhead di serializzazione tra i moduli
- Più facile rifattorizzare i confini dei moduli man mano che la comprensione evolve
- LangGraph + FastAPI funzionano nativamente in un singolo processo

**Negative:**
- Impossibile scalare i moduli in modo indipendente (ad es. l'indicizzazione RAG rispetto alla gestione delle richieste)
- Singolo punto di guasto
- Memoria e CPU condivise tra tutte le responsabilità

**Neutre:**
- Il percorso di migrazione verso i servizi in un secondo momento è possibile perché i moduli hanno confini 
  chiari; non è bloccato, solo rimandato
````