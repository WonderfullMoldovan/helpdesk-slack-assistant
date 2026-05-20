````markdown
# ADR-002: LangGraph for Agent Orchestration

**Status:** Accepted
**Date:** 2026-05-13

## Context

Il sistema richiede l'orchestrazione di molteplici agenti guidati da LLM con:
- Flusso non deterministico (chiamate ai tool variabili per ogni richiesta)
- Routing condizionale basato sulla classificazione
- Stato persistente attraverso conversazioni multi-turno
- Interrupt human-in-the-loop con ripresa
- Esecuzione ciclica (agente → tool → agente → tool → ...)

Un framework che supporti questi pattern nativamente riduce il rischio di implementazione 
rispetto a una costruzione da zero.

## Decision

Usare **LangGraph** come framework di orchestrazione degli agenti. Gestione dello stato tramite 
il checkpointing integrato di LangGraph con PostgresSaver. I nodi del grafo corrispondono 
ad agenti e tool; gli archi codificano la logica di routing.

## Alternatives Considered

**1. Semplice function calling di OpenAI in un loop Python**
- Scartata: richiederebbe di re-implementare la persistenza dello stato, gli interrupt, 
  gli hook di observability, la visualizzazione del grafo. Replica il valore di LangGraph 
  con settimane di lavoro.
- Nessun pattern standard: ogni progetto crea il proprio; difficile da difendere in sede di revisione

**2. CrewAI**
- Scartata: astrazione più opinionated (Crew, Task, Agent come concetti fissi); 
  minore controllo sulla struttura del grafo; supporto più debole agli interrupt HITL 
  al momento della decisione
- Più adatta a pattern di collaborazione multi-agente; il nostro sistema è più 
  gerarchico (supervisor → specialista)

**3. AutoGen (Microsoft)**
- Scartata: astrazione multi-agente in stile conversazione; migliore per il dialogo 
  agente-agente che per una topologia supervisor-tool; l'integrazione con lo stato persistente 
  e l'HITL è meno diretta

**4. State machine custom + asyncio**
- Scartata: alto costo di implementazione; reinventare ciò che LangGraph fornisce; 
  nessuna integrazione standard di observability

## Consequences

**Positive:**
- Supporto nativo per i pattern richiesti (stato, interrupt, archi 
  condizionali, cicli)
- Stretta integrazione con Langfuse (callback `langfuse-langchain`)
- Sviluppo attivo; esempi della community per pattern simili
- La visualizzazione del grafo facilita il debugging e la presentazione in sede di revisione

**Negative:**
- Accoppiamento a un singolo framework — cambiarlo in seguito richiede di riscrivere 
  il livello di orchestrazione
- Il framework è ancora in evoluzione; possibili breaking change tra versioni minori
- Curva di apprendimento per la progettazione dello schema di stato e i pattern di checkpointing

**Neutre:**
- Versione fissata (pinned) nelle dipendenze; gli upgrade vengono valutati esplicitamente
````