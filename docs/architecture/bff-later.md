# BFF — later, not now

We explicitly defer a Backend-For-Frontend layer.

## Why not now

- MVP has five small services and a static Wi-Fi portal. A BFF is unnecessary complexity.
- Each frontend module can call the service it needs directly via documented REST endpoints.
- Adding a BFF now would duplicate validation and RBAC code.

## When to reconsider

- When the admin portal (mobile-web) exists and needs to fan out to 3+ services per page.
- When we add a native mobile client.
- When we need response shaping that differs per client.

## If/when we build it

- FastAPI service in `services/bff`.
- Depends only on PropelAuth for auth; forwards tokens to downstream services.
- No business logic — shape and fan out only.
- Must not bypass downstream RBAC.
