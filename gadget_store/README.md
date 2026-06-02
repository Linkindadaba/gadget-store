# FB Nation — Django E-Commerce

A full-featured e-commerce platform for gadgets & accessories built with Django.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply migrations
python manage.py migrate

# 3. Seed demo data (products, categories, delivery zones)
python manage.py seed_data

# 4. Create admin user
python manage.py createsuperuser

# 5. Run the server
python manage.py runserver
```

Visit: http://127.0.0.1:8000
Admin: http://127.0.0.1:8000/admin

---

## 📁 Project Structure

```
gadget_store/
├── gadget_store/          # Project config
│   ├── settings.py        # All settings + delivery region fees
│   └── urls.py            # Root URL routing
├── store/                 # Product catalog & cart
│   ├── models.py          # Category, Product, ProductImage
│   ├── views.py           # Home, product list/detail, cart CRUD
│   └── context_processors.py  # Cart count in navbar
├── orders/                # Checkout & order management
│   ├── models.py          # Order, OrderItem
│   ├── forms.py           # CheckoutForm with region selector
│   └── views.py           # Checkout, order history
├── payments/              # Paystack integration
│   ├── models.py          # Payment record
│   └── views.py           # Initiate, verify, webhook
├── logistics/             # Delivery fee engine
│   ├── models.py          # DeliveryZone (per-region fees)
│   └── views.py           # JSON API for fee lookup
└── templates/
    ├── base.html           # Navbar, footer, global styles
    ├── store/              # Home, product list, detail, cart
    ├── orders/             # Checkout, confirmation, my orders
    └── payments/           # Payment page, failure page
```

---

## ✅ Features Built

### 1. Product Showcase
- Category browsing with icons
- Grid/list product catalog with search & sort
- Product detail page with image, description, stock status
- Discount badges (shows % off)
- Featured products section on homepage

### 2. Direct Ordering (replaces DMs)
- Add to cart (session-based, works for guests)
- Cart management (update quantity, remove)
- Checkout form: name, email, phone, full address
- Guest checkout — no account required
- Order tracking for logged-in users

### 3. Integrated Payments (Flutterwave)
- Flutterwave v4 sandbox checkout for Ghana mobile money
- Payment reference tracking
- Webhook handler for async confirmation
- Payment status: pending → success/failed
- Order status auto-updates on payment success

### 4. Logistics — Delivery Fee Calculator
- 16 Ghana regions with individual fee rates
- Real-time fee display on checkout (JS)
- Order total updates dynamically when region selected
- DeliveryZone model for admin-editable fees

---

## ⚙️ Configuration

### Flutterwave Keys (.env)
```python
import os
FLUTTERWAVE_CLIENT_ID = os.getenv('FLUTTERWAVE_CLIENT_ID')
FLUTTERWAVE_CLIENT_SECRET = os.getenv('FLUTTERWAVE_CLIENT_SECRET')
FLUTTERWAVE_ENCRYPTION_KEY = os.getenv('FLUTTERWAVE_ENCRYPTION_KEY')
```

### Paystack Test Keys (local testing only)
```bash
PAYSTACK_SECRET_KEY=sk_test_50dd7ba51e84e0b6128e1ccc1788a15a0b824e60
PAYSTACK_PUBLIC_KEY=pk_test_03c30ee7d776a8167cc3b3d1e178e3028471e895
PAYSTACK_WEBHOOK_SECRET=your_paystack_webhook_secret
PAYSTACK_ALLOWED_IPS=127.0.0.1,::1
```

For local testing, the project already exposes these endpoints:
- Test Callback URL: `http://localhost:8000/payments/callback/`
- Test Webhook URL: `http://localhost:8000/payments/webhook/`

If you expose the app through a public tunnel like ngrok, use the tunnel URL instead:
- `https://<your-tunnel>.ngrok.io/payments/callback/`
- `https://<your-tunnel>.ngrok.io/payments/webhook/`

### ngrok Testing
1. Start your app locally:
```bash
cd gadget_store
.\.venv\Scripts\python.exe manage.py runserver
```
2. Open a second terminal and run ngrok:
```bash
ngrok http 8000
```
3. Copy the generated public URL and register these Paystack sandbox endpoints:
   - `https://<your-tunnel>.ngrok.io/payments/callback/`
   - `https://<your-tunnel>.ngrok.io/payments/webhook/`
4. If you set `PAYSTACK_ALLOWED_IPS`, also add the webhook source IP(s) reported by ngrok.

If `PAYSTACK_ALLOWED_IPS` is set, webhook requests will be rejected unless the source IP matches the allowlist.

### Delivery Fees (settings.py)
4. If you set `PAYSTACK_ALLOWED_IPS`, also add the webhook source IP(s) reported by ngrok.

If `PAYSTACK_ALLOWED_IPS` is set, webhook requests will be rejected unless the source IP matches the allowlist.

### Delivery Fees (settings.py)
```python
DELIVERY_REGIONS = {
    'Greater Accra': 15.00,
    'Ashanti': 35.00,
    # ... customize per region
}
```
Fees can also be updated live from the admin panel under **Logistics → Delivery Zones**.

---
Manage:
- **Products** — add images, set prices, mark featured, manage stock
- **Categories** — add/edit with Bootstrap icon names
- **Orders** — view all orders, update status (paid/shipped/delivered)
- **Payments** — audit payment records
- **Delivery Zones** — adjust regional delivery fees live

---

## 🌍 Deployment Checklist

- [ ] Set `DEBUG = False` in settings.py
- [ ] Set `SECRET_KEY` from environment variable
- [ ] Replace Flutterwave sandbox credentials with live credentials
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up PostgreSQL (replace SQLite)
- [ ] Configure media file storage (Cloudinary or S3)
- [ ] Add Flutterwave webhook URL in Flutterwave dashboard: `yourdomain.com/payments/webhook/`
- [ ] Run `python manage.py collectstatic`
