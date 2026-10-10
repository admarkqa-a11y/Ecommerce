# Frontend deployment and runtime configuration

Use the backend deployment runbook for infrastructure, secret generation, SMTP and merchant prerequisites. This release adds a frontend overlay; no public hosting or DNS changes were performed.

```bash
docker build -f backend/Dockerfile -t REGISTRY/retail-api:0.4.0 .
docker build -f deployment/frontend.Dockerfile --build-arg APP=storefront -t REGISTRY/retail-storefront:0.4.0 .
docker build -f deployment/frontend.Dockerfile --build-arg APP=admin -t REGISTRY/retail-admin:0.4.0 .
```

Push and record immutable image digests. Generate a fresh client environment with `scripts/new_production_client.py` as documented in `docs/backend/DEPLOYMENT.md`. Add these deployment-specific values securely:

- STOREFRONT_IMAGE and ADMIN_IMAGE: the respective `registry/image@sha256:...` values.
- STOREFRONT_DOMAIN and ADMIN_DOMAIN: separate public DNS hostnames.
- ALLOWED_HOSTS: API, storefront and admin hostnames plus `api` for private SSR API requests.
- CSRF_TRUSTED_ORIGINS: exact HTTPS storefront/admin origins and any deliberately supported API browser origin.
- CUSTOMER_ORIGIN: HTTPS storefront origin; password reset links redirect to the localized reset screen.
- PAYMENT_RETURN_URL: HTTPS storefront `/en/orders` (or `/ar/orders`). This is navigation only; the backend provider verification determines payment status.
- INDEXABLE: false for staging; enable only after final SEO/content review.

```bash
export CLIENT_ENV_FILE=client-deployments/CLIENT/.env
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml -f compose.frontend.production.yaml up -d
```

The Caddy overlay terminates HTTPS, routes same-origin `/api/*` requests to Django and sends page requests to the appropriate Next server. No direct frontend/API/DB/Redis ports are exposed beyond the proxy. Internal SSR uses API_HTTPS_TERMINATED=true only because the private API connection is behind this controlled HTTPS ingress. Do not enable that flag on an untrusted public plain-HTTP deployment. No untrusted request header can set it.

Builds contain no client branding or merchant credentials. Server-side API_ORIGIN selects the deployment backend at runtime. Both UI applications read client identity, logo/color/contact/currency and commerce data from the backend. Images are client-provided HTTPS URLs or same-origin paths; no media uploader/storage service is added in this release. Host any same-origin media path explicitly at ingress or use a reviewed HTTPS media service. Provider credentials never enter the browser bundle.

Each client needs isolated media/storage, DB, queue/cache, secrets and users. Use separate hosts/IPs for unchanged Compose stacks, which bind 80/443, or deliberately provision a routing layer for multiple stacks on one host. Do not accidentally reuse COMPOSE_PROJECT_NAME or client volume names.

The full image build, Caddy TLS path, public domains and two isolated Docker deployments remain target-host verification gates. Local source/HTTP checks are not proof of those deployment properties. Pin dependency image digests and apply your registry, backup, security monitoring and rollback policies before launch.
