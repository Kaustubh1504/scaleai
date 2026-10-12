# 10. API key vs OAuth bearer token

Your billing job joins **orders** with **catalog prices**. The two services
live behind the same host but authenticate differently: the Catalog takes a
static API key, the Orders service uses **OAuth2 client credentials**. Write
two small clients that get auth right and never leak a secret.

## The API

**Catalog**: `GET /v1/items/{sku}` with header `X-API-Key: <key>`

```json
{"sku": "SKU-100", "name": "Bounding boxes, 1k", "price_cents": 12000}
```

Missing/wrong key → **401**. Unknown SKU → **404**.

**Token**: `POST /oauth/token`, body **form-encoded**
(`application/x-www-form-urlencoded`, i.e. httpx `data=`, *not* `json=`):

```
grant_type=client_credentials&client_id=<id>&client_secret=<secret>
```

```json
{"access_token": "tok_00001", "token_type": "bearer", "expires_in": 3600}
```

A JSON body or another grant type → **400**. Wrong credentials → **401**.

**Orders**: `GET /v1/orders` with header `Authorization: Bearer <access_token>`
(exactly `Bearer`, capital B, even though `token_type` is lowercase).

```json
{"orders": [{"id": "ord_001", "customer": "acme", "sku": "SKU-100", "qty": 3}, ...]}
```

Missing/invalid/expired token → **401**.

## Setup

```python
from problem_api import make_api, API_KEY, CLIENT_ID, CLIENT_SECRET
http = make_api().client()   # one httpx.Client (base_url set) for all three endpoints
```

The `if __name__ == "__main__":` block is what the Run button executes: use it
to hit each endpoint by hand (try the token request with `json=` and with
`data=`) and print the raw responses.

## Your task

Your module must define:

* `class ApiError(Exception)`: `ApiError(status, path, message="")`; attributes
  `.status: int` and `.path: str`.
* `class AuthError(ApiError)`: same constructor; used for auth failures.
* `class CatalogClient`: `CatalogClient(http: httpx.Client, api_key: str)`,
  method `get_item(sku: str) -> dict`.
* `class OrdersClient`: `OrdersClient(http: httpx.Client, client_id: str, client_secret: str)`,
  method `list_orders() -> list[dict]`.

Rules:

* `get_item` returns the item dict. 401 → `AuthError`; any other non-2xx → `ApiError`.
* `OrdersClient` makes **no request in `__init__`**. It fetches a token the
  first time it needs one and **reuses** it for every later call.
* `list_orders` returns the `orders` list.
* A non-200 from `/oauth/token` → `AuthError`. A 401 from `/v1/orders` →
  `AuthError` (no refresh in this problem). Other non-2xx → `ApiError`.
* Secrets never leak: `repr()` / `str()` of either client, and `str()` of any
  error you raise, must not contain the API key, the client secret or the
  access token, and nothing you print or log may contain them.

## Example

```python
orders = OrdersClient(http, CLIENT_ID, CLIENT_SECRET)
orders.list_orders(); orders.list_orders()
# 3 requests: POST /oauth/token, GET /v1/orders, GET /v1/orders (same token)
CatalogClient(http, API_KEY).get_item("SKU-100")["price_cents"]   # 12000
```

## Constraints

* Go through `http` only (its `base_url` is set). Don't touch `api.issuer`.
* `AuthError` must be a subclass of `ApiError`.

<details><summary>Hint 1</summary>

`data=` form-encodes; `json=` doesn't and gets a 400. Store the token on
`self` and fetch it only when you don't have one yet.
</details>

<details><summary>Hint 2</summary>

A `@dataclass` or a careless `__repr__` prints every field. Write
`__repr__` yourself and show only non-secret fields (e.g. `client_id`).
</details>

## Follow-up (talk it through)

* API key vs OAuth client credentials: what does each buy you (rotation,
  scoping, expiry, revocation)? Where should either secret live in production?
* The token expires after an hour. What changes? (That's problem 11.)
* Two threads share one `OrdersClient` and both see "no token yet". What happens, and how would you fix it?
