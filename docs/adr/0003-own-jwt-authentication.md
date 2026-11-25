# 0003. Own JWT authentication

## Status

Accepted.

## Context

Customers register with email and password, can also order as guests, and an admin manages products and orders. There are two roles: customer and admin. The project needs to run locally without any identity service.

## Decision

The API owns authentication:

- Passwords are hashed with scrypt (random salt, constant-time compare). The hash is stored in the `users` container.
- Login returns a JWT signed with HS256 using `PDC_JWT_KEY`, valid for 1 hour, with claims `sub`, `email`, `role`, `iat`, `exp`.
- Roles are read from the token. Admin routes require role `admin`. Registration ignores any `role` field.
- Login failures return one generic `401 Invalid credentials` for an unknown email and for a wrong password, after a short delay. An unknown email still costs one scrypt run, so timing does not reveal accounts.
- The client sends the token in the header `X-Pdc-Token: Bearer <jwt>`. SWA managed Functions overwrite the `Authorization` header, so a standard bearer header never reaches the API on a deployed site. A custom header passes through.
- The browser keeps the token in `localStorage`. A strict CSP and DOM-only rendering (`textContent`) limit XSS risk.

## Consequences

- No external identity dependency, no extra cost, works offline with the memory adapters.
- The team owns password and token handling, so the code is small and tested (hashing, expiry, role guards).
- No refresh token, no password reset and no social login. The user logs in again after 1 hour.
- A role change takes effect only when the token expires.
- A leaked `PDC_JWT_KEY` invalidates all trust. Terraform generates one random key per environment (`random_password`) and sets it as the SWA app setting `PDC_JWT_KEY`.

## Alternatives

| Option | Why not |
| --- | --- |
| Entra External ID | Real identity platform with MFA and reset flows, but a new tenant, setup, redirect flows and a learning cost out of proportion for this project. |
| SWA built-in auth | Only supports fixed providers (no email and password), and gives roles by invitation, not by self-registration. |
| `Authorization: Bearer` header | Overwritten by SWA managed Functions. Replaced by `X-Pdc-Token`. |
