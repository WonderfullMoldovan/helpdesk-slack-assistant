````markdown
# ADR-007: LLM-evaluated Tool Sensitivity (with documented risk)

**Status:** Accepted (with explicit risk acknowledgement)
**Date:** 2026-05-13

## Context

Alcune azioni del sistema sono ad alto rischio (concedere accesso admin, modificare 
risorse critiche) e devono attivare un'approvazione umana prima dell'esecuzione. La 
domanda è **come** identificare quali azioni sono ad alto rischio.

Forze:
- Nuovi tool possono essere aggiunti nel tempo; le liste statiche si disallineano
- La sensibilità può dipendere dal contesto (ad es. "reset della password" è a basso rischio per 
  se stessi, più alto per qualcun altro)
- Una classificazione sbagliata ha un costo asimmetrico: mancare un'azione ad alta 
  sensibilità (falso negativo) è molto peggio che sovra-classificare (falso positivo)

## Decision

Usare la **sensibilità valutata dall'LLM**: quando l'Action Agent considera di chiamare 
un tool, valuta la sensibilità dell'azione nel contesto come parte del suo 
ragionamento. L'output è un campo strutturato (`sensitivity: LOW | MED | HIGH`) 
che attiva il routing HITL quando è HIGH.

**Riconoscimento esplicito del rischio:** questo approccio ha un tasso di falsi 
negativi diverso da zero (l'LLM può non rilevare la sensibilità).

**Mitigazioni del rischio applicate:**
1. Il system prompt dell'Action Agent enumera esplicitamente le categorie di azioni 
   ad alta sensibilità
2. La sensibilità viene loggata su Langfuse; le classificazioni errate diventano rilevabili 
   tramite il monitoraggio
3. La v2 aggiungerà una baseline hardcoded (difesa in profondità): alcuni tool sono 
   sempre HIGH indipendentemente dalla valutazione dell'LLM


## Alternatives Considered

**1. Sensibilità hardcoded nella definizione di ogni tool**
- Scartata come meccanismo unico: richiede che ogni nuovo tool sia classificato 
  manualmente dallo sviluppatore che lo aggiunge; rischio di tool sensibili non marcati 
  per una svista
- Verrà reintrodotta nella v2 come livello di baseline (non come sostituzione)

**2. Autorizzazione per-utente (RBAC)**
- Scartata: richiede un modello di identità che va oltre lo user_id di Slack; fuori dall'ambito; 
  non sostituisce la sensibilità per-azione (concern ortogonale)

**3. Fare sempre escalation (nessuna automazione delle azioni)**
- Scartata: vanifica lo scopo di un sistema di automazione; l'80% delle azioni 
  è di routine e non dovrebbe richiedere l'intervento umano


## Consequences

**Positive:**
- Flessibile: i nuovi tool ereditano automaticamente il ragionamento sulla sensibilità
- Consapevole del contesto: lo stesso tool può essere MED o HIGH a seconda delle circostanze
- Scelta architetturale dimostrabile con un ragionamento difendibile

**Negative:**
- Tasso di falsi negativi diverso da zero (rischio riconosciuto)
- Dipende dal comportamento dell'LLM, che può variare tra le versioni del modello
- Richiede un'attenta progettazione del prompt e un monitoraggio continuo

**Neutre:**
- Combinare la valutazione dell'LLM con una baseline hardcoded (pianificata per la v2) è 
  l'approccio di livello produttivo; la v1 dimostra il percorso LLM e riconosce 
  il gap esplicitamente
````