# 0002. Cosmos DB NoSQL serverless for data

## Status

Accepted.

## Context

The data is three small collections (products, orders, users) with simple access patterns: list the catalog, read one product, list the orders of a pickup day, look up a user by email. Traffic is low and irregular. Stock must not go negative when two customers order the same product.

## Decision

Use Cosmos DB for NoSQL in serverless capacity mode, database `migas`, one container per collection:

| Container | Partition key | Notes |
| --- | --- | --- |
| `products` | `/category` | Catalog reads and per-category queries. |
| `orders` | `/pickupDate` | The admin lists orders of a day. |
| `users` | `/email` | Unique key on `/email`; login is a point read. |

Stock is protected with optimistic concurrency: each stock change reads the product with its ETag and writes with an `if-match` condition. On a conflict the service retries up to 5 times, then answers 409. Orders apply stock in a fixed order and compensate (restore) when a later line fails.

Images are not stored in Cosmos. The API signs a short-lived Blob SAS URL and the browser uploads straight to Blob Storage (see the README security notes).

## Consequences

- Pay per request and storage, so idle cost is near zero.
- No schema migrations. Seeds are idempotent and run on every deploy.
- ETag locking needs no lock service, but a crash between stock steps can leave a small inconsistency. This window is accepted.
- The last unit can be sold twice in a race. The order is then accepted as made to order. This is accepted behavior.
- Locally the app uses in-memory adapters, so tests and `uvicorn` need no Azure account. The memory fallback is allowed only when `PDC_ENVIRONMENT=local`.

## Alternatives

| Option | Why not |
| --- | --- |
| Azure SQL (serverless) | Relational power is not needed. Needs schema and migration handling, and auto-pause adds a slow first query. |
| Table Storage | Limited querying (no flexible filters by day or category) and no unique key on email. |
| Cosmos provisioned throughput | Fixed cost with no benefit at this traffic. |
