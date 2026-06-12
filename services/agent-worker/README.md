# agent-worker

Första drift-agenten enligt [docs/28-agentisk-driftmodell.md](../../docs/28-agentisk-driftmodell.md):
**rapportagenten**. Cloud Scheduler publicerar `{"job": "monthly-report"}`
på Pub/Sub-topicen `agent-jobs`; en push-prenumeration levererar till
`POST /pubsub` här; workern hämtar YELLOW-aggregat från reporting-service
och genererar månadsrapporten. Varje konsumerat meddelande lämnar exakt
en audit-post i Firestore-kollektionen `audit_events`.

## Säkerhetsmodell

- Kör som servicekontot `sa-agent-worker` (egen identitet → attribuerbart).
- Endast YELLOW/GREEN-data passerar: perioder, aggregat, rapport-id.
- Endpointen skyddas av Cloud Run IAM (`--no-allow-unauthenticated`);
  push-prenumerationen autentiserar med OIDC. Ingen applikationsauth.
- Agenten *genererar* rapporter — den fattar inga beslut och rör aldrig
  RED-data (AOM §3, rollen motsvarar "Ops/Research").

## Pub/Sub-semantik

| Utfall | HTTP-svar | Pub/Sub |
|---|---|---|
| Lyckat jobb | 204 | ack |
| Dublett (samma messageId redan klar) | 204 | ack, körs inte om |
| Okänt jobb / trasig payload | 204 | ack (retry hjälper aldrig), auditeras som `rejected` |
| Transient fel (reporting-service nere) | 500 | redelivery med backoff |

## Miljövariabler (production)

| Variabel | Beskrivning |
|---|---|
| `ADAPTER_MODE` | `production` i molnet, `memory` lokalt/test |
| `REPORTING_SERVICE_URL` | Bas-URL till reporting-service |
| `AGENT_REPORTING_TOKEN` | Zitadel-maskinanvändartoken; dess org-claim avgör vilken kyrka rapporterna genereras för |

## Tester

```bash
cd services/agent-worker && pytest
```
