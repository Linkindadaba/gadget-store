# 🚀 DEPLOYMENT CHECKLIST

Follow these steps to deploy your app online in ~5 minutes:

## ✅ Local Preparation (You)

- [ ] Run `pip install -r requirements.txt` locally
- [ ] Test locally: `python manage.py runserver`
- [ ] Commit all changes: `git add . && git commit -m "Deploy"`

## ✅ Push to GitHub (You)

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## ✅ Deploy on Railway (3 minutes)

1. Go to **https://railway.app** → Sign up (free)
2. Click **"New Project"** → **"Deploy from GitHub"**
3. Select your GitHub repo
4. Wait for build (2-3 min)

## ✅ Configure on Railway Dashboard

1. **Variables** tab → Add these:
   - `SECRET_KEY` = Generate at https://djecrety.ir/
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `your-app.railway.app`

2. **Add PostgreSQL** (optional but recommended):
   - New → PostgreSQL
   - Railway auto-sets `DATABASE_URL` ✅

3. **Deploy Domain** tab:
   - Your app is at: `https://YOUR-APP.railway.app`

## ✅ Your App is LIVE! 🎉

- **Admin**: `https://YOUR-APP.railway.app/admin`
- **Store**: `https://YOUR-APP.railway.app`

---

## 📖 Full Guide

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

## 🆘 Need Help?

- Check Railway logs: **Deployments** tab → Select latest → View logs
- Railway docs: https://docs.railway.app/
- Django deployment: https://docs.djangoproject.com/en/stable/howto/deployment/
