# 🚀 Deployment Guide - Railway.app

This guide shows how to deploy your Django app **online in 5 minutes** using Railway.app (free tier available).

---

## ✅ Prerequisites

1. **GitHub Account** - [Sign up free](https://github.com/signup)
2. **Railway Account** - [Sign up free](https://railway.app)

---

## 📋 Step-by-Step Deployment

### Step 1: Push Your Code to GitHub

```bash
# Initialize git (if not done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - ready for deployment"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to **[Railway.app](https://railway.app)** → Sign in/Sign up
2. Click **"New Project"** → **"Deploy from GitHub"**
3. Select your repository
4. Railway will auto-detect Django and create a deployment
5. Wait for build to complete (2-3 minutes)

### Step 3: Configure Environment Variables

In Railway dashboard:
1. Go to **Variables** tab
2. Add these variables:

```
SECRET_KEY = (generate a new one: https://djecrety.ir/)
DEBUG = False
ALLOWED_HOSTS = your-app.railway.app,yourdomain.com
PAYSTACK_PUBLIC_KEY = your_key (optional)
PAYSTACK_SECRET_KEY = your_key (optional)
```

### Step 4: Set Up Database

Railway provides a **PostgreSQL database** for free (limited resources).

1. In Railway: **"New"** → **Add PostgreSQL**
2. Connect it to your Django app
3. Railway auto-sets `DATABASE_URL` ✅

Update your `settings.py` to use it:

```python
import dj_database_url

if not DEBUG:
    DATABASES = {
        'default': dj_database_url.config(
            default='sqlite:///db.sqlite3',
            conn_max_age=600
        )
    }
```

Then run migrations:
```bash
python manage.py migrate --database default
```

### Step 5: Run Initial Setup

In Railway terminal:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

---

## 🌐 Your Live App

Your app is now live at: `https://YOUR-APP.railway.app`

- **Admin**: `https://YOUR-APP.railway.app/admin`
- **Store**: `https://YOUR-APP.railway.app`

---

## 🔗 Custom Domain (Optional)

1. Buy domain (Namecheap, GoDaddy, etc.)
2. In Railway → **Settings** → **Custom Domain**
3. Add your domain and follow DNS instructions

---

## 🐛 Troubleshooting

### Deployment fails
- Check **Deployments** tab → View logs
- Ensure `requirements.txt` has all packages
- Make sure `Procfile` exists

### Static files missing
- Run: `python manage.py collectstatic --noinput`
- WhiteNoise middleware is already configured

### Database errors
- Verify `DATABASE_URL` is set in Railway
- Run migrations: Check the release command in `Procfile`

### 500 errors
- Check Railway logs: **Deployments** → View logs
- Ensure `DEBUG=False` and `ALLOWED_HOSTS` is correct

---

## 📊 Monitoring

In Railway dashboard:
- **Logs**: Real-time app output
- **Metrics**: CPU, Memory, Bandwidth usage
- **Deployments**: Deployment history

---

## 💡 Tips

- **Scale up**: Click **"Scale"** to add more RAM if needed (paid)
- **Auto-deploy**: Pushes to `main` branch automatically redeploy
- **Environment secrets**: Use Railway's **Variables** tab (not in code)
- **Backup database**: PostgreSQL data persists across redeployments

---

**Your app is now live! 🎉**
