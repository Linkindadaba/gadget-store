# TechHub Ghana — Django E-Commerce

A full-featured e-commerce platform for gadgets & accessories built with Django.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install django pillow django-crispy-forms crispy-bootstrap5 requests

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

### 3. Integrated Payments (Paystack)
- Paystack popup checkout (card, mobile money, bank)
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

### Paystack Keys (settings.py)
```python
PAYSTACK_PUBLIC_KEY = 'pk_live_xxxx'   # from dashboard.paystack.com
PAYSTACK_SECRET_KEY = 'sk_live_xxxx'
```

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

## 🔐 Admin Panel

URL: `/admin/` | Default: `admin` / `admin123`

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
- [ ] Replace Paystack test keys with live keys
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up PostgreSQL (replace SQLite)
- [ ] Configure media file storage (Cloudinary or S3)
- [ ] Add Paystack webhook URL in Paystack dashboard: `yourdomain.com/payments/webhook/`
- [ ] Run `python manage.py collectstatic`
