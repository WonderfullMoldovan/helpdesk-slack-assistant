Project Charter: IT Helpdesk Slack Assistant
Version: 1.0
Date: 2026-05-13
Status: Draft → pending sign-off
Author: Andrei Vasiliev

1.Project Name: It Helpdesk slack Asistant 
Asistente Slack bassato sull'intelegenza artificiale che automatizza le richieste di supporto IT di routine per i dipendenti interni con inoltro intelegente agli operatori umani quando necessario

2.Problem statement:
In piccoli e medie tech-aziende  IT riceve tanti richieste simile dal dipendenti 
tipo: cambiare password, richieste accesso in sistema, base su trableshooting, onboarding nouvi dipendenti
Questi richieste sono con struttura simile(80% richieste sono in 10-15 categorie)
Mangiano tempo It - ingegnere(Tempo costa)
ce sta High latency per user (ore o giorni aspettattiva)
Spesso questi richieste risolvono con runbook successivi che gia ci sono in knowledge base, pero dipendenti non leggano.
Conteporamente full automatizzazione non po essere fatta: Perche ce stanno richieste ambiguo o hanno unp rezzo alto per un erorre, o richiede contesto che in knowledge base non ce sta.


3.Primary Goals:
Demostrare una conoscenza approfondita dell'ingegneria dell'intelegenza artificiale moderna. AI engineering - include multiagent orchestrazione, hitl, observabillity, gestione dello stato persistente - attraverso un sistema funzionante e implementato che possa reggere confronto in sede di revisione tecnica

4.Success Criteria:
1. Functional:end-to-end demo dove dipendente scrive IT richiesta in slack e risposta ageguata (risoluzione automatica OPPURE inoltro a un operatore) entro 30 secondi.
2.Architectural: Almeno 2 agenti distinti con chiari confini di responsabilita, che comunicano tramite uno stato strutturato.
3.HITL: Almeno un percorso di escalation implementato, attivato in caso di basso levollo di affidabilita o di elevata sensibilita dell'azione.
4.observabiolity: ogni interazione dell user genera una traccia completa in Langfuse che mostra tutte le chiamate LLM, le chiamate agli strumenti, i ccosti e la latenza.
5.State: il contesto della conversazione viene mantenuto anche tra piu messaggi e in caso di riavvio del sistema
6.Knowledge: gli agenti sono in grado di recuperare e utilizzare le informazioni contenute in una base di conoscenza (Rag di base + almeno una tecnica avanzata con giunstificaziopne documentata)
7.Deployment: Sistema corre in cloude azure con Slack external integration
8.Documentation: Project Charter, C4 diagrams (levels 1-3), 5+ ADR, diagrammi di sequenza per i flussi principali
9.Defendability:Per ogni scelta tecnologica, esiste una motivazione scritta di un paragrafo che risponde alle domande "problem solved/alternetives rejectd/WHY"

5.Stakeholder:
(Stakeholder, Role, Primary Interest)
1. Andrei Vasiliev - engineer, architect, Responsabile  - Crea sistema, impara l'ingegneria AI mmoderna
2. Pietro Ciattaglia - Reviewer - Valutare l'approccio architettonico, le scelte tecnologiche e il levello di compressione
3.Hypothentical It Staff(normal) - User finale in Unikey - Ottiene una resoluzione rapida delle richieste IT di routine; un chiaro sistema de escalation quando l'AI non e in grado di fornire assistenza
4. Hypothentical It staff(It-Engignere) - User finale in Unikey - Riceve solo segnalazioni significative con il contesto complet; non essere sommerso da richieste di scarsa rilevanza generata dall'AI

6. Scope:

In Scope:
milti-agent orchestration(langgraph-based)
HITL escalation
Observability via Langfuse
Persistent state(Postgresql + redis)
basic RAG + 1 advanced RAG technique
Slack integration via slack SDK/Bolt
FastApi as web layer
OpenAI(o simile) as LLM provider

Stretch:
Azure development
second advanced rag technique

Out of Scope:
Production - grade security (full 0auth flows, encryption-at-rest, etc)
Multi-tenancy
Fine-tuning models
Voice/image input
Full agentic RAG / RAG evaluation framework
High-load scaling / horizontal scaling
Admin UI

7. Constraints

Timeline:
Total target : 10-14 giorni di calendario di lavoro intensivo
Daily capacity: 7 ore productive work (~10 ore totale investimento)
Revisioni settimanali delle tappe fondamentali con il mentore; ogni settimana deve produrre progressi dimostrabili dall'inizio alla fine

People : 
Developer, Mentor.

Budget:
Local-only deployment via Docker Compose, cloud deployment documentata a livello di architettura
OpenAI API: gpt-40-mini as default, gpt-4o solo con spiegazioni;hard spending limit configured, Langfuse: piano gratuito o self-hosted

Technology:
Stack preferente: Python, FastAPI, LangGraph, OpenAI, Slack SDK, PostgreSQL, Redis, Azure, Langfuse

Compliance:

No real PII handled (solo data sintetica)
No production data


8. Key Assumptions

1. Slack free workspace 
2. Open AI API 
3.gpt-4o-mini 
4. Knowledge base - 30 documenti semantiche basta per demonstrare RAG
5.Azure free tier
6.Latency 30 secondi va bene per Utente

9. Risks & Mitigations
voglio chiedere se serve.


Signed: Andrei Vasiliev, 2026-05-13