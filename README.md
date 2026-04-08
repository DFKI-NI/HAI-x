# HAIx Interface

A web-based interface for the HAIx project — an autonomous aquatic weed-management system. The application provides an interactive map dashboard (Dash/Plotly), area and path management forms, data tables, and integration with AI-based satellite image analysis and path-planning services.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Running with Docker Compose (Recommended)](#running-with-docker-compose-recommended)
- [Running Locally (Without Docker)](#running-locally-without-docker)
- [Accessing the Application](#accessing-the-application)
- [Container Management](#container-management)
- [Environment Variables](#environment-variables)
- [Development Workflow](#development-workflow)
- [Adding an AI Plugin](#adding-an-ai-plugin)
- [Data & Videos](#data--videos)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The application is composed of four services:

| Service | Description | Port |
|---|---|---|
| **interface** | Flask + Dash web frontend/backend | `5000` |
| **postgis_container** | PostgreSQL 17 with PostGIS 3.5 (database) | `5432` |
| **path_planning_vrpy** | CVRP path-planning microservice | `10002` |
| **estimate_areas_of_interest** | Satellite NDVI-based area-of-interest detector | `10003` |

All services communicate over a shared Docker network (`haix-network`).

---

## Prerequisites

### For Docker Compose

- [Docker Engine](https://docs.docker.com/engine/install/) ≥ 20.10
- [Docker Compose](https://docs.docker.com/compose/install/) v2 (included with Docker Desktop)
- Access to the DFKI GitLab container registry (`git.ni.dfki.de:5050`) for the `path_planning_vrpy` and `estimate_areas_of_interest` images
- (Optional) Sentinel Hub credentials for satellite data (see [Environment Variables](#environment-variables))

### For Local Development (Without Docker)

- **Python** 3.10+
- **pip** (Python package manager)
- **PostgreSQL** 17 with the **PostGIS** extension installed
- **OpenSSL** (for generating self-signed TLS certificates, if not already present)
- Access to the path-planning and area-of-interest services (either running in Docker or available at a reachable host)

---

## Running with Docker Compose (Recommended)

This is the easiest way to start the full application stack.

### 1. Set Environment Variables

Create a `.env` file in the project root (next to `compose.yaml`) with your Sentinel Hub credentials:

```env
sh_client_id=YOUR_CLIENT_ID
sh_client_secret=YOUR_CLIENT_SECRET
sh_instance_id=YOUR_INSTANCE_ID
```

> These credentials are required by the `estimate_areas_of_interest` service to fetch satellite imagery from the Copernicus Data Space. If you do not need satellite-based AOI detection, the other services will still start without them.

### 2. Log in to the DFKI Container Registry

```bash
docker login git.ni.dfki.de:5050
```

This is required to pull the `path_planning_vrpy` and `estimate_areas_of_interest` images.

### 3. Build and Start All Services

```bash
docker compose up --build
```

Add `-d` to run in detached (background) mode:

```bash
docker compose up --build -d
```

Docker Compose will:
1. Build the `interface` container from the root `dockerfile`.
2. Build the `postgis_container` from `sql/dockerfile` (initialises the `haix` database with seed data from CSV files).
3. Pull the `path_planning_vrpy` and `estimate_areas_of_interest` images from the registry.
4. Wait for the database to be healthy before starting the interface.

### 4. Open the Application

Navigate to **<https://localhost:5000>** in your browser.

> The application uses a self-signed TLS certificate (`cert.pem` / `key.pem`). Your browser will show a security warning — accept the risk to proceed.

### 5. Stop All Services

```bash
docker compose down
```

To also remove the database volume (resetting all data):

```bash
docker compose down -v
```

---

## Running Locally (Without Docker)

### 1. Set Up PostgreSQL with PostGIS

Install PostgreSQL 17 and the PostGIS extension for your platform, then initialise the database:

```bash
# Start the PostgreSQL server (platform-specific)
# Connect to PostgreSQL and run the init script:
psql -U postgres -f sql/script.sql
```

This creates the `haix` database, the `interface` schema, all required tables, and imports the seed data from the CSV files in `sql/`.

### 2. Update the Database Host

The application connects to the database using the hostname `postgis_container` (the Docker service name). For local development, update the host in `utils/database/database.py`:

```python
# Change this line:
host="postgis_container",
# To:
host="localhost",
```

> **Tip:** You can also make this configurable via an environment variable to avoid changing committed code:
> ```python
> host=os.environ.get("DB_HOST", "localhost"),
> ```

### 3. Install Python Dependencies

It is recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **Note:** The `psycopg2` package requires the PostgreSQL client libraries. If installation fails, try `pip install psycopg2-binary` instead, or install the system package `libpq-dev` (Debian/Ubuntu) / `postgresql-devel` (Fedora/RHEL).

### 4. Generate TLS Certificates (if missing)

If `cert.pem` and `key.pem` are not present in the project root:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

### 5. Start the External Services

The interface depends on two microservices. For local development you can either:

- **Run them in Docker** (recommended):
  ```bash
  docker network create haix-network

  # Path planning service
  docker run -d --name path_planning_vrpy \
    --network haix-network \
    -p 10002:10002 \
    git.ni.dfki.de:5050/hai-x/path-planning/cvrp-with-vrpy:latest

  # Area-of-interest estimator
  docker run -d --name estimate_areas_of_interest \
    --network haix-network \
    -p 10003:10003 \
    -e sh_client_id=YOUR_CLIENT_ID \
    -e sh_client_secret=YOUR_CLIENT_SECRET \
    -e sh_instance_id=YOUR_INSTANCE_ID \
    git.ni.dfki.de:5050/hai-x/area-of-interest-detectors/estimate-weeding-areas-from-ndvi/estimate_weeding_areas_from_apa:2.1.1
  ```

- **Skip them** — the core interface (dashboard, tables, area/path forms) will still work, but path generation and satellite AOI detection will fail with connection errors.

> When running the services locally via Docker but the Flask app natively, update the service URLs in the code from Docker hostnames to `localhost`:
> - `routes/routes.py`: change `http://path_planning_vrpy:10002` → `http://localhost:10002`
> - `routes/new_area.py`: change any reference to `estimate_areas_of_interest:10003` → `localhost:10003`

### 6. Run the Flask Application

**With TLS (recommended — matches production):**

```bash
flask --app main.py run --cert=cert.pem --key=key.pem --host=0.0.0.0
```

**Without TLS (plain HTTP):**

```bash
flask --app main.py run --host=0.0.0.0
```

**Or directly via Python:**

```bash
python main.py
```

The application will be available at **<https://localhost:5000>** (or `http://localhost:5000` without TLS).

---

## Accessing the Application

| Page | URL | Description |
|---|---|---|
| Dashboard | `https://localhost:5000/` | Interactive map with areas, paths, and trajectories |
| New Area | `https://localhost:5000/newarea` | Add areas of interest manually or via satellite |
| New Path (Manual) | `https://localhost:5000/newpath/add` | Draw paths on the map |
| New Path (Generate) | `https://localhost:5000/newpath/generate` | Auto-generate paths from AOIs |
| Tables (Areas) | `https://localhost:5000/tables/view/area` | View/edit area data |
| Tables (Paths) | `https://localhost:5000/tables/view/path` | View/edit path data |
| Tables (Trajectories) | `https://localhost:5000/tables/view/traj` | View trajectory data |

---

## Container Management

### Rebuild Containers After Code Changes

```bash
docker compose up --build
```

To rebuild only the interface container:

```bash
docker compose build interface
docker compose up
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f interface
docker compose logs -f postgis_container
```

### Open a Shell Inside a Running Container

```bash
docker compose exec interface bash
docker compose exec postgis_container psql -U postgres -d haix
```

### Restart a Single Service

```bash
docker compose restart interface
```

---

## Environment Variables

| Variable | Used By | Description |
|---|---|---|
| `sh_client_id` | `estimate_areas_of_interest` | Copernicus Data Space account client ID |
| `sh_client_secret` | `estimate_areas_of_interest` | Copernicus Data Space account client secret |
| `sh_instance_id` | `estimate_areas_of_interest` | Sentinel Hub service/instance ID |
| `POSTGRES_PASSWORD` | `postgis_container` | Database password (default: `secret`) |

For Docker Compose, place these in a `.env` file in the project root. Docker Compose reads it automatically.

---

## Development Workflow

### Hot Reload

Flask's built-in reloader is active by default when using `flask run`. Changes to Python files will automatically restart the server. Template (Jinja2) changes are reflected on the next page refresh without a restart.

When using Docker Compose, the application source is **copied** into the container at build time. To see code changes you must **rebuild**:

```bash
docker compose up --build
```

> **Tip:** For faster iteration during development, you can add a volume mount to `compose.yaml` to map the local source into the container:
> ```yaml
> services:
>   interface:
>     volumes:
>       - .:/app          # mount project root into container
>       - /mnt/maschsee_videos:/static/video/
>     environment:
>       - FLASK_DEBUG=1   # enable auto-reload
> ```

### Volume Mounts

The `compose.yaml` maps the host video directory into the container:

```yaml
volumes:
  - /mnt/maschsee_videos:/static/video/
```

Update this path to match the location of videos on your machine.

### Database Persistence

The PostGIS container uses a Docker-managed volume. Data persists across restarts but is lost if you run `docker compose down -v`. To back up the database:

```bash
docker compose exec postgis_container pg_dump -U postgres haix > db_backup.sql
```

---

## Adding an AI Plugin

1. Import the package into the `ai/` folder.
2. Add all necessary imports in the plugin's `__init__.py` file (using `importlib` is recommended).
3. If setup steps are required, add a script in the `docker/` folder and reference it in the root `dockerfile`.
4. Create a utility/wrapper script in the `utils/` folder to integrate with the Flask routes.

---

## Data & Videos

- **Videos** are expected at the path configured in `compose.yaml` (`/mnt/maschsee_videos` by default).
- **Seed data** (areas, paths, trajectories, geometries) is loaded from CSV files in `sql/` when the database container is first created.
- **GeoJSON** is generated at runtime and written to `data/geo.json`.

---

## Troubleshooting

### Browser shows "Your connection is not private"

The application uses a self-signed TLS certificate. Click **Advanced → Proceed to localhost** (Chrome) or **Accept the Risk and Continue** (Firefox).

### `psycopg2` installation fails

Install the PostgreSQL client libraries first:

```bash
# Debian / Ubuntu
sudo apt-get install libpq-dev python3-dev

# macOS (Homebrew)
brew install postgresql

# Or use the binary wheel instead:
pip install psycopg2-binary
```

### Database connection refused

- **Docker Compose:** Ensure the `postgis_container` is healthy — `docker compose ps` should show `healthy` status. The interface waits for the health check automatically.
- **Local:** Verify PostgreSQL is running on port `5432` and that `utils/database/database.py` uses `host="localhost"`.

### Path generation or AOI detection fails

These features require the `path_planning_vrpy` (port `10002`) and `estimate_areas_of_interest` (port `10003`) services. Verify they are running:

```bash
docker compose ps
# or
curl http://localhost:10002
curl http://localhost:10003
```

### Port already in use

If port `5000` is occupied (e.g., by macOS AirPlay Receiver):

```bash
# Find the process
lsof -i :5000

# Or change the port in compose.yaml:
# ports:
#   - "8000:5000"
```

### Container registry authentication error

```bash
docker login git.ni.dfki.de:5050
```

Ensure you have access to the HAIx group on the DFKI GitLab instance.

### Database needs to be reset

```bash
docker compose down -v
docker compose up --build
```

This removes the database volume and reinitialises from the seed CSV files.
