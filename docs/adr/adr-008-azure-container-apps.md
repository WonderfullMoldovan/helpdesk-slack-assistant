````markdown
# ADR-008: Azure Container Apps over AKS / App Service

**Status:** Accepted (target deployment; v1 implementation is local)
**Date:** 2026-05-13

## Context

Il Charter specifica un deployment **solo locale** via Docker Compose, con il 
deployment su cloud **documentato a livello di architettura** ma non implementato 
nella v1. Di conseguenza, la topologia Azure obiettivo va comunque documentata 
come architettura di riferimento, anche se non viene realizzata.

Forze:
- Applicazione containerizzata (Python + dipendenze)
- Scala di 1–3 istanze (non su larga scala)
- Sviluppatore unico — la complessità operativa è importante
- Necessità di un ingress HTTPS per i webhook di Slack
- La stessa architettura logica deve poter girare in locale e, in futuro, su Azure 
  senza modifiche al codice (portabilità architetturale)

## Decision

Use **Azure Container Apps** as the target compute platform for both 
FastAPI App and Scheduler containers. Container Registry, Key Vault, 
PostgreSQL Flexible Server, and Cache for Redis as supporting services.

## Alternatives Considered

**1. Azure Kubernetes Service (AKS)**
- Rejected: operational overhead disproportionate to single-app scope
- Maximum control but requires K8s expertise (RBAC, networking, ingress 
  controllers, certificate management)
- Justified only when needs (custom operators, sidecars, mesh) exceed what 
  managed alternatives provide — not our case

**2. Azure App Service**
- Rejected: tier-based pricing; container support exists but Container Apps 
  is the modern equivalent for containerized workloads
- Weaker concurrency model for async Python apps in our experience

**3. Azure Functions (Premium / Container plan)**
- Rejected: designed for short-lived event handlers; long-running LLM 
  calls (5–15s) and stateful execution don't fit FaaS model
- Cold starts impact already-slow flows

**4. Azure Virtual Machines**
- Rejected: manual patching, manual orchestration, manual TLS — defeats 
  cloud-managed benefits

## Consequences

**Positive:**
- Managed HTTPS ingress (no certificate management)
- Auto-scaling within configured bounds
- Per-revision deployment with traffic splitting (blue/green possible)
- KEDA-based scaling rules available if needed
- Native integration with Container Registry, Key Vault, Log Analytics

**Negative:**
- Less control than AKS; some advanced K8s features unavailable
- Container Apps still evolving; some features behind AKS in maturity
- Vendor lock-in to Azure-specific platform (mitigated: standard container 
  image runs anywhere)

**Neutral:**
- Cost at low scale is comparable to App Service; cheaper than AKS at this 
  scale due to no node pool overhead
- v1 is local-only; this decision is forward-looking
````