# Budget Approval Dashboard

A small full-stack internal tool: employees submit expense/budget requests,
managers approve or reject them, and a dashboard aggregates approved spend
by department and category.

**Stack:** React (frontend) · Flask REST API (backend) · SQLite (database)

---

## 1. Run it locally (5 minutes)

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
This starts the API on **http://localhost:5000** and auto-creates
`expenses.db` with sample seed data on first run.

### Frontend
No build step needed — it's a single static HTML file using React via CDN.
```bash
cd frontend
python -m http.server 5500
```
Then open **http://localhost:5500** in your browser.

(You can also just double-click `index.html`, but serving it avoids
occasional browser fetch/CORS quirks with the `file://` protocol.)

---

## 2. What it demonstrates

| Skill | Where |
|---|---|
| REST API design | `backend/app.py` — CRUD endpoints, filtering via query params |
| SQL / data modeling | SQLite schema + parameterized queries |
| Data aggregation | `/api/aggregate` — GROUP BY spend by department/category/status |
| Frontend (React) | `frontend/index.html` — components, state, fetch calls |
| Role-based workflow | Employee view (submit) vs Manager view (approve/reject) |
| Full-stack integration | Frontend calls backend via `fetch`, CORS enabled |

---

## 3. Deploying it live (so you can link it on your resume)

**Backend → Render (free tier):**
1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com), create a new **Web Service**, point it at the repo's `backend/` folder.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py` (or `gunicorn app:app` for production — add `gunicorn` to requirements.txt if so)
5. Render gives you a public URL like `https://your-app.onrender.com`.

**Frontend → Vercel / Netlify / GitHub Pages (all free):**
1. In `frontend/index.html`, change:
   ```js
   const API = "http://localhost:5000/api";
   ```
   to your deployed backend URL:
   ```js
   const API = "https://your-app.onrender.com/api";
   ```
2. Deploy the `frontend/` folder as a static site (drag-and-drop onto Netlify works too).

Once deployed, you'll have a live link plus a GitHub repo — both worth
putting on your resume next to the project bullet.

---

## 4. Suggested resume bullet

> Built and deployed a full-stack internal budget-approval application
> (React, Flask, SQLite) with role-based approval workflows, REST APIs,
> and a data-aggregation endpoint powering spend-by-department/category
> dashboards.

---

## 5. Easy extensions if you have extra time

- Swap SQLite → PostgreSQL (closer to production/enterprise setups)
- Add JWT-based login instead of the role toggle
- Add pagination to the requests table
- Add a "export to CSV" button (quick win, shows data-handling range)
