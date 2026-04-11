# certificate-service

RED-zone service. Issues digital certificates (baptism, confirmation, etc.)
and exposes a privacy-preserving verification endpoint.

## Key design choice

Verification never reveals identity. A verifier scans the QR on a certificate
and learns only:

- certificate type (e.g. `baptism`)
- issued date
- issuing church name
- status (`valid` | `revoked` | `frozen`)

No name, no personnummer, no email. The certificate_id is a UUID — not a
sequential or predictable identifier.

## Actions

| Action | Role |
|---|---|
| Issue certificate | admin, pastor |
| Revoke certificate | admin, pastor |
| Freeze certificate | admin |
| Verify certificate | public (privacy-preserving) |

## Running

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Ports

- `CertificateRepository` — storage
- `AuthPort` — PropelAuth
- `PdfGenerator` — renders the PDF (stub in MVP)
- `AuditPort` — audit log

## Example template

See `templates/baptism.txt` for a minimal human-readable template used by the
stub PDF generator in tests.
