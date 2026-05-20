````markdown
# ADR-006: Hybrid Search as Advanced RAG Technique

**Status:** Accepted
**Date:** 2026-05-13

## Context

Il Project Charter si è impegnato a fornire "RAG di base + almeno una tecnica avanzata 
con giustificazione documentata". Esistono diverse tecniche RAG avanzate; la 
scelta deve essere difendibile per il nostro dominio specifico.

Forze:
- Il dominio è quello di un helpdesk IT: le query contengono spesso identificatori esatti 
  (codici di errore, nomi di sistemi, versioni di software)
- La ricerca puramente vettoriale tratta il testo come semantico, perdendo la fedeltà del match esatto
- Il budget di implementazione è limitato; bisogna scegliere una sola tecnica con un'alta 
  aderenza al dominio

## Decision

Implementare la **ricerca ibrida** combinando la similarità vettoriale densa (pgvector con 
distanza del coseno) e il matching sparso per keyword (la ricerca full-text di PostgreSQL 
con ranking in stile BM25). I risultati di entrambe vengono uniti tramite una weighted 
reciprocal rank fusion.

## Alternatives Considered

**1. Re-ranking (cross-encoder sopra i risultati vettoriali)**
- Scartata per questo ambito: è più vantaggioso quando il recupero restituisce 50–100 
  candidati; con ~30 documenti in totale, il pool di candidati è troppo piccolo perché 
  il re-ranking aggiunga un valore misurabile
- Costo di implementazione più alto (modello aggiuntivo, latenza aggiuntiva)

**2. HyDE (Hypothetical Document Embeddings)**
- Scartata: genera una risposta ipotetica da usare come query; aggiunge una chiamata LLM 
  per ogni query (latenza + costo); le evidenze per query tecniche brevi sono 
  contrastanti; non affronta il problema dell'identificatore esatto

**3. Riscrittura / espansione della query**
- Scartata come tecnica primaria: aiuta con query verbose o ambigue; 
  non risolve il problema del match esatto intrinseco al recupero puramente vettoriale
- Nota: una forma leggera di affinamento della query fa già parte del flusso del 
  Knowledge Agent (preparazione della query per il recupero)

**4. Parent document retrieval**
- Scartata: utile quando i chunk sono troppo piccoli per fornire contesto; per 
  la documentazione IT, dimensioni dei chunk ben scelte (300–500 token) catturano 
  risposte complete senza l'espansione al documento padre

## Consequences

**Positive:**
- Le query con identificatori esatti (ad es. "ERROR_CODE_2003", "macOS Sonoma 14.5") 
  vengono recuperate correttamente tramite il percorso BM25
- Le query semantiche (ad es. "non riesco a connettermi a internet") vengono recuperate 
  correttamente tramite il percorso vettoriale
- Entrambe implementate in PostgreSQL — nessun nuovo componente
- Dimostra la comprensione del *perché* questa tecnica anziché altre

**Negative:**
- La taratura dei pesi (importanza del vettoriale rispetto alla keyword) richiede una valutazione; la v1 
  usa default difendibili senza un framework di valutazione formale
- Latenza delle query leggermente più alta (due passate di recupero + fusione)
- Aggiunge complessità rispetto alla ricerca puramente vettoriale

**Neutre:**
- La ricerca ibrida è un pattern ben consolidato; non è ricerca innovativa
- Il pattern di implementazione (RRF) è semplice da estendere con il re-ranking 
  in seguito, se la scala cresce
````