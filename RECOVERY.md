Team Recovery & Cleanup Instructions

What happened
- Repository history was rewritten to remove sensitive files (.env, gadget_store/db.sqlite3).

Immediate owner actions (you)
1. Rotate any exposed secrets now (Paystack, Flutterwave, Cloudinary, Sentry).
2. Force-push the cleaned history to remote:

```powershell
git fetch origin
git push --force-with-lease -u origin main
```

3. Verify Railway env vars are set (`SECRET_KEY`, `DATABASE_URL`, payment keys, webhook secrets) and restart the service.

How collaborators should recover (safe, recommended)
- If they have no uncommitted local work:

```powershell
git fetch origin
git checkout main
git reset --hard origin/main
```

- If they have local changes to keep:

```powershell
# save current work
git checkout -b my-local-backup
# update main to rewritten remote
git fetch origin
git checkout main
git reset --hard origin/main
# rebase your work onto the new main
git checkout my-local-backup
git rebase main
# resolve conflicts if any, then push your branch
```

- If unsure, re-clone the repo after force-push:

```powershell
# safest option
git clone https://github.com/Linkindadaba/gadget-store.git
```

Post-cleanup checklist
- Rotate/disable any keys that were committed and update deployment env variables.
- Confirm you can run `manage.py check` and `manage.py migrate` on staging/production.
- Add `pre-commit` hooks (detect-secrets) and CI secret scanning to prevent reoccurrence.

Coordination
- Communicate the force-push time to the team and instruct them to re-clone or reset before pushing.
- If you want, share this file in your team chat or attach it to the GitHub PR describing the rewrite.

Contact
- If you need help coordinating, tell me and I’ll prepare a short message you can post to the team.
