# Technify (Portfolio Version)

Django-based e-commerce demo with a simple cart/checkout flow and optional email/SMS notifications.

This repo is configured to be safe for a public portfolio: no live keys are committed, and card payments are expected to run in **test** mode via environment variables.

## Quick start (local)

1. `cd technify`
2. Create `.env` from `technify/.env.example` (do not commit your real `.env`)
3. Install deps: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Start server: `python manage.py runserver`

## Payments (Yoco)

- Configure `YOCO_MODE=test` and set `YOCO_PUBLIC_KEY` / `YOCO_SECRET_KEY` in `.env`.
- If `YOCO_SECRET_KEY` is missing (or still set to the placeholder), checkout will show a demo message and skip the Yoco call.

## Production template

Use `technify/.env.production.example` as a template and upload it to your host as `.env`. Keep payments in test mode for portfolio deployments.


## Live working site
www.technify.co.za
