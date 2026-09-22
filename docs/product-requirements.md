# Product Requirements — RootCause

## Vision

Help engineers find the most likely root cause of production symptoms using retrieved evidence, not free-form inventiveness.

## Users

- SRE / on-call engineers
- Backend developers investigating regressions

## Core flows

1. Authenticate
2. Start investigation (symptom, service, environment, time window)
3. System invokes tools + RAG retrieval
4. LLM (Mock or Ollama) produces structured, evidence-cited report
5. Engineer reviews hypothesis, confidence, evidence trail, next steps

## Non-goals

- General chat companion
- Automated remediations / kubectl exec
- Paid model APIs

## Success criteria

- Investigations always list tools invoked and evidence IDs
- Hypotheses cite only collected evidence IDs
- Evaluation gate passes on controlled incidents (see docs/evaluation.md)
