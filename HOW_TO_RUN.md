# PayCrest – Docker Compose Local Testing Guide

## Files needed per service

Place these Dockerfiles inside each service folder:

```
paycrest/                        ← project root
├── docker-compose.yaml          ← (provided)
│
├── frontend/
│   ├── Dockerfile               ← (provided)
│   ├── nginx.conf               ← (provided – must sit next to Dockerfile)
│   ├── package.json
│   └── src/
│
├── api-gateway/
│   ├── Dockerfile               ← (provided)
│   ├── package.json
│   └── server.js
│
├── auth-service/
│   ├── Dockerfile               ← (provided)
│   ├── requirements.txt
│   └── app/
│       └── main.py
│
├── loan-service/                ← same structure
│   ├── Dockerfile               ← (same as auth-service Dockerfile)
│   ├── requirements.txt
│   └── app/
│
├── emi-service/                 ← same structure
├── wallet-service/              ← same structure
├── payment-service/             ← same structure
├── verification-service/        ← same structure
├── admin-service/               ← same structure
└── manager-service/             ← same structure
```

---

## ⚠️ The PORT env var explained (important!)

Your `.env` files have `PORT=3001`, `PORT=3002`, etc.

**These do NOT crash anything.** Here's why:

| Thing            | What port it actually uses              |
|------------------|-----------------------------------------|
| uvicorn (Python) | Always `8000` (hardcoded in `CMD`)      |
| `PORT=3001` etc. | Only used by API gateway to build URLs  |

In Docker Compose the API gateway talks to services like this:
```
http://auth-service:8000   ← container name + uvicorn port
```
NOT `http://auth-service:3001`. That's why the compose file overrides
all `*_SERVICE_URL` env vars to use `:8000`.

---

## ⚠️ VITE_API_BASE_URL is baked at BUILD time

Vite embeds env variables into the JS bundle when you run `npm run build`.
So the Docker build arg `VITE_API_BASE_URL` must equal what the
**browser** can reach — not what the container can reach.

- Local: `http://localhost:3000/api`  (browser → your machine → docker)
- Production: `https://api.yourdomain.com/api`

---

## ⚠️ UPLOAD_BASE_PATH Windows path fix

Your `.env` files have:
```
UPLOAD_BASE_PATH=C:\Users\noelm\Desktop\paycrest 2\paycrest\uploads
```

This is a Windows path and **will break** inside a Linux container.
The docker-compose.yaml overrides it to:
```
UPLOAD_BASE_PATH: /app/uploads
```
And mounts a Docker named volume there. You don't need to change your `.env` files.

---

## Step-by-step: Run the whole app

### Step 1 – Prerequisites
```bash
# Make sure Docker Desktop is running
docker --version       # should be 24+
docker compose version # should be 2.x
```

### Step 2 – Place the files
Copy the provided Dockerfiles into each service folder (see structure above).
Copy `nginx.conf` into the `frontend/` folder alongside its Dockerfile.
Place `docker-compose.yaml` at the project root.

### Step 3 – Build and start everything
```bash
# From the project root (where docker-compose.yaml is)
docker compose up --build
```

This will:
1. Build all 10 Docker images (takes ~3-5 min first time)
2. Start MongoDB first, wait for it to be healthy
3. Start all 8 Python services
4. Start the API gateway
5. Start the frontend (nginx)

### Step 4 – Verify it's running
```bash
# In a second terminal:
docker compose ps

# You should see all containers as "running" or "healthy"
```

### Step 5 – Open in browser
- **Frontend app**: http://localhost
- **API directly**: http://localhost:3000/api
- **MongoDB** (Compass/Studio 3T): `mongodb://pycrest:pycrest123@localhost:27017/pycrest?authSource=admin`

### Step 6 – View logs
```bash
# All services
docker compose logs -f

# Single service
docker compose logs -f auth-service
docker compose logs -f api-gateway
docker compose logs -f mongodb
```

### Step 7 – Rebuild after code changes
```bash
# Rebuild only what changed:
docker compose up --build auth-service

# Or rebuild everything:
docker compose up --build
```

### Step 8 – Stop everything
```bash
docker compose down

# Stop AND delete volumes (wipes MongoDB data):
docker compose down -v
```

---

## Troubleshooting

### "Cannot connect to MongoDB"
The Python services wait for MongoDB to be healthy before starting.
If you see this, MongoDB might still be initializing.
Check: `docker compose logs mongodb`

### "Module not found" in Python service
Your `requirements.txt` might be missing a package.
Check: `docker compose logs auth-service`

### Frontend shows blank page / API errors
The `VITE_API_BASE_URL` build arg must match what YOUR BROWSER can reach.
If running locally it should be `http://localhost:3000/api`.
Rebuild after changing: `docker compose up --build frontend`

### "Address already in use" on port 80 or 3000
Something else is using that port. Find and stop it, or change the
`ports:` mapping in docker-compose.yaml:
```yaml
ports:
  - "8080:80"    # access frontend on http://localhost:8080
```

### Upload not persisting
The `uploads-data` named volume is shared between loan, wallet,
verification, admin, and manager services. All of them mount it at
`/app/uploads`. Files saved by one service are visible to all.
