# F.B Nation Gadget Store

A full-featured Django e-commerce platform for gadgets and accessories, targeting customers in Ghana with mobile money and card payment integrations.

## Tech Stack

- **Framework**: Django 6.x (Python)
- **Database**: PostgreSQL (Replit Helium DB in dev, configurable via `DATABASE_URL`)
- **Static Files**: WhiteNoise
- **Media Storage**: Cloudinary (optional; falls back to local filesystem)
- **Payments**: Flutterwave and Paystack integrations
- **Task Queue**: Celery + Redis (optional; not required for basic dev)

## Project Structure

```
gadget_store/         # Django project root
  gadget_store/       # Core settings, URLs, WSGI, Celery config
  store/              # Product catalog, search, cart
  orders/             # Checkout and order management
  payments/           # Flutterwave & Paystack webhooks
  logistics/          # Delivery regions and fees
  static/             # Global CSS/JS
  templates/          # HTML templates
```

## Running Locally

The app is configured to run on port 5000 via the "Start application" workflow:

```
cd gadget_store && python manage.py runserver 0.0.0.0:5000
```

## Environment Variables

Key variables (set in Replit Secrets or environment):

| Variable | Required | Description |
|----------|----------|-------------|
| `DEBUG` | Yes | `True` for dev, `False` for prod |
| `SECRET_KEY` | Yes (prod) | Django secret key |
| `ALLOWED_HOSTS` | Yes (prod) | Comma-separated allowed host names |
| `DATABASE_URL` | Prod only | PostgreSQL connection string |
| `PAYSTACK_SECRET_KEY` | Prod | Paystack server secret |
| `PAYSTACK_PUBLIC_KEY` | Prod | Paystack public key |
| `FLUTTERWAVE_SECRET_KEY` | Prod | Flutterwave secret key |
| `CLOUDINARY_CLOUD_NAME` | Optional | Cloudinary cloud name for media |

## Deployment

Production uses Gunicorn with autoscale deployment. Migrations and collectstatic run automatically on deploy.

## User Preferences

- Keep `requirements.txt` using flexible version pins (`>=`) rather than strict `==` to avoid Replit package firewall blocks on older pinned versions.
