````markdown
# ADR-003: Supervisor Pattern with Three Specialists

**Status:** Accepted
**Date:** 2026-05-13

## Context

I sistemi multi-agente possono essere organizzati in diverse topologie. La scelta 
plasma sia la complessità di implementazione sia la capacità di dimostrare il 
ragionamento architetturale in sede di revisione.

Forze:
- Necessità di una chiara separazione tra logica di classificazione e logica di esecuzione
- Necessità di gestire tre concern distinti: recupero delle informazioni, esecuzione 
  delle azioni, escalation umana
- Necessità di una topologia che scali concettualmente (aggiungere agenti = modifica locale)
- Necessità di una topologia difendibile rispetto alle domande del tipo "perché non X"

## Decision

Usare il **pattern Supervisor**: un agente orchestratore (Supervisor) classifica 
le richieste in ingresso e le instrada verso uno di tre **agenti specialisti**:

1. **Knowledge Agent** — risponde a domande informative tramite RAG
2. **Action Agent** — esegue operazioni con effetti collaterali tramite tool
3. **Escalation Agent** — gestisce le escalation human-in-the-loop


## Alternatives Considered

**1. Swarm (agenti peer-to-peer)**
- Scartata: nel nostro dominio gli agenti non collaborano su compiti condivisi; 
  gestiscono tipi di richiesta distinti. L'overhead di uno swarm senza i benefici di uno swarm.

**2. Agente unico con tutti i tool**
- Scartata: logica di classificazione mescolata con logica di esecuzione in un unico prompt; 
  più difficile da debuggare, più difficile da far evolvere, separazione concettuale più debole
- La difendibilità in sede di revisione ne risente — l'affermazione "multi-agente" diventa vuota

**3. Due agenti (unendo Action + Escalation)**
- Scartata: l'escalation ha una semantica di runtime fondamentalmente diversa 
  (interrupt + attesa persistente); unirli rende sfocato quel confine
- Due agenti sembra artificiale come dimostrazione "multi-agente"

**4. Quattro o più agenti (ad es. aggiungendo un Clarification Agent)**
- Scartata: valore marginale; il chiarimento multi-turno può essere gestito all'interno 
  del Knowledge Agent o dell'Action Agent tramite il normale prompting dell'LLM; aggiunge costo 
  di implementazione senza un apprendimento proporzionale

## Consequences

**Positive:**
- Chiara separazione dei concern: classificazione, recupero, azione ed escalation 
  isolati
- Facile da estendere: nuovo specialista = nuovo nodo + una rotta del supervisor
- Ogni agente ha un prompt focalizzato e un piccolo set di tool, il che migliora l'affidabilità
- Difendibile in sede di revisione: "tre specialisti, il supervisor instrada" è un 
  pattern riconoscibile

**Negative:**
- Due chiamate LLM per richiesta (supervisor + specialista) anziché una
- La classificazione del supervisor può essere sbagliata, portando a un routing subottimale
- Più codice rispetto all'approccio a singolo agente

**Neutre:**
- La soglia di confidenza del supervisor fornisce un trigger di escalation quando 
  la classificazione stessa è incerta (trasformando un aspetto negativo in positivo)
````