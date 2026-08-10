# HAIx Interface (Django)

A web-based interface for the HAI-x project — an autonomous aquatic weed-management
system. The application provides an interactive map dashboard (Plotly Dash), area
and path management forms, data tables, and integration with AI-based satellite
image analysis and path-planning services.

This project was migrated from Flask to **Django**. All public URLs of the Flask
version are preserved, and the Dash dashboard is embedded through
[django-plotly-dash](https://django-plotly-dash.readthedocs.io/).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Layout](#project-layout)
3. [Environment Variables](#environment-variables)
4. [Running with Docker Compose](#running-with-docker-compose-recommended)
5. [Running Locally (Without Docker)](#running-locally-without-docker)
6. [How to Add a New Route (Django)](#how-to-add-a-new-route-django)
7. [How to Add a New Dash App](#how-to-add-a-new-dash-app)
8. [API Endpoints](#api-endpoints)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The system is intentionally **distributed**:

* The **Django application** (this repository) is the web UI layer, the Dash
  integration layer and an API gateway for the frontend.
* **Specialised computations run as separate FastAPI services**, each in its own
  Docker container:

  | Compose service              | Port  | Purpose                                            |
  |------------------------------|-------|----------------------------------------------------|
  | `path_planning_vrpy`         | 10002 | CVRP path planning (VRPy), `POST /routePos/`       |
  | `estimate_areas_of_interest` | 10003 | AoI estimation from NDVI/APA, `POST /api/get_aois` |
  | `evaluation_service`         | 10005 | Satellite/onboard-camera detection evaluation      |
  | `data_extraction`            | 10006 | ROS bag extraction (GPS, images, videos)           |
  | `bathymetry_service`         | 10007 | Bathymetry GeoJSON                                 |
  | `apa_index_service`          | 10008 | Sentinel-2 APA index                               |
  | `capacitated_aoi_service`    | 10010 | Density-based AoI clustering + plant volume        |
  | `capacitated_path_service`   | 10011 | Capacitated-cluster CVRP                           |

* Django talks to these services **via HTTP only** (`apps/services/clients/`).
  Their base URLs are configured through environment variables; inside Docker
  Compose the containers address each other **by service name**, never
  `localhost`.
* A **PostGIS** container stores the domain data (schema `interface`); Django
  additionally keeps its own bookkeeping (sessions, django-plotly-dash state) in
  the same PostgreSQL database, or in a local SQLite file during development.

> Note: the public GitHub repository contains the service source code inline as
> an overview/reference version. In the internal project those services live in
> separate repositories and are pulled as prebuilt images from the DFKI
> registry. Do not assume the service source folders exist here — only the API
> contracts matter, and they are equivalent to the GitHub overview version.

## Project Layout

```txt
.
├── manage.py
├── hai_x/                  # Django project (settings, urls, wsgi/asgi, jinja2 env)
├── apps/
│   ├── core/               # /config, /changelog, /switch_language
│   ├── dashboard/          # "/" home page + Dash apps
│   │   └── dash_apps/      #   haix.py (DjangoDash "HaixDashboard"), sonar UI/callbacks
│   ├── planning/           # /newarea*, /newpath* (+ services.py business logic)
│   ├── data/               # /data*, /evaluation*, /traj/load
│   ├── tables/             # /tables/*
│   ├── services/clients/   # HTTP clients for the external FastAPI services
│   └── common/             # shared view helpers
├── templates/              # Jinja2 templates (migrated unchanged from Flask)
├── static/                 # CSS/JS/images/videos (served by WhiteNoise)
├── utils/                  # database access, variables, language, dash helpers
├── sql/                    # PostGIS init scripts (own container build)
├── tests/                  # smoke + service-client tests
├── requirements.txt
├── dockerfile
└── compose.yaml
```

Two template engines are configured: the **Django** engine for app templates
and django-plotly-dash internals, and a **Jinja2** engine for the legacy
templates in `templates/` (it provides a Flask-compatible `url_for()` shim, so
the old templates work unchanged).

## Environment Variables

| Variable                       | Default                                  | Description                              |
|--------------------------------|------------------------------------------|------------------------------------------|
| `SECRET_KEY`                   | insecure dev key                         | Django secret key — set in production!   |
| `DEBUG`                        | `1` (local) / `0` (compose)              | Django debug mode                        |
| `ALLOWED_HOSTS`                | `*`                                      | Comma-separated host list                |
| `CSRF_TRUSTED_ORIGINS`         | _(empty)_                                | Comma-separated origins (https://...)    |
| `POSTGRES_HOST`                | _(empty → SQLite)_                       | PostGIS host; `postgis_container` in compose |
| `POSTGRES_PORT`                | `5432`                                   |                                          |
| `POSTGRES_DB`                  | `haix`                                   |                                          |
| `POSTGRES_USER`                | `postgres`                               |                                          |
| `POSTGRES_PASSWORD`            | `secret`                                 |                                          |
| `VRPY_SERVICE_URL`             | `http://path_planning_vrpy:10002`        | VRPy path-planning service               |
| `AOI_SERVICE_URL`              | `http://estimate_areas_of_interest:10003`| AoI estimation service                   |
| `EVALUATION_SERVICE_URL`       | `http://evaluation_service:10005`        | Evaluation service                       |
| `DATA_EXTRACTION_SERVICE_URL`  | `http://data_extraction:10006`           | ROS data extraction service              |
| `BATHYMETRY_SERVICE_URL`       | `http://bathymetry_service:10005`        | Bathymetry service (container-internal port) |
| `APA_INDEX_SERVICE_URL`        | `http://apa_index_service:10003`         | Sentinel-2 APA index service (container-internal port) |
| `CAPACITATED_AOI_SERVICE_URL`  | `http://capacitated_aoi_service:10010`   | Capacitated AoI clustering / volume      |
| `CAPACITATED_PATH_SERVICE_URL` | `http://capacitated_path_service:10011`  | Capacitated path planning                |
| `SERVICE_REQUEST_TIMEOUT`      | `30`                                     | Default HTTP timeout (seconds)           |
| `SONAR_SERVICE_URL`            | `http://localhost:8000`                  | Optional SONAR explanation service       |
| `LOG_LEVEL`                    | `INFO`                                   | Root log level                           |

Sentinel Hub credentials are required by the **AoI / APA services** (not by
Django itself) and are passed to the `estimate_areas_of_interest` container by
Docker Compose:

```bash
export sh_instance_id="your-instance-id"
export sh_client_id="your-client-id"
export sh_client_secret="your-client-secret"
```

(Browser-entered credentials on the `/config` page are stored in cookies and
forwarded to the services per request.)

## Running with Docker Compose (Recommended)

```bash
# 1. Sentinel Hub credentials for the AoI service
export sh_instance_id=... sh_client_id=... sh_client_secret=...

# 2. Log in to the DFKI container registry (service images)
docker login git.ni.dfki.de:5050

# 3. Build and start everything
docker compose up --build
```

The interface is then available at <http://localhost:8000>. The container runs
`python manage.py migrate` automatically and serves the app with gunicorn.
Static files (including the mounted video volume) are served by WhiteNoise.

Stop everything with `docker compose down` (add `-v` to also reset the
database volume).

## Running Locally (Without Docker)

```bash
# 1. Virtualenv + dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Database
#    Option A (quick start): nothing to do — Django uses a local SQLite file
#    for its own tables. Domain features that need PostGIS will be limited.
#    Option B (full): start the PostGIS container and point Django at it:
docker compose up -d postgis_container
export POSTGRES_HOST=localhost

# 3. External FastAPI services — run the containers you need and use
#    localhost URLs (NOT the compose service names):
docker compose up -d path_planning_vrpy estimate_areas_of_interest
export VRPY_SERVICE_URL=http://localhost:10002
export AOI_SERVICE_URL=http://localhost:10003
# (see compose.yaml for the host ports of the remaining services, e.g.
#  export BATHYMETRY_SERVICE_URL=http://localhost:10007
#  export APA_INDEX_SERVICE_URL=http://localhost:10008)

# 4. Migrate + run
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Open <http://localhost:8000>.

## How to Add a New Route (Django)

1. **Create a view** in the appropriate app, e.g. `apps/data/views.py`:

   ```python
   from django.http import JsonResponse

   def water_quality(request):
       if request.method != "POST":
           return JsonResponse({"error": "POST required"}, status=405)
       lake = request.POST.get("lake_name", "")
       if not lake:
           return JsonResponse({"error": "lake_name is required"}, status=400)
       return JsonResponse({"lake": lake, "quality": "good"})
   ```

2. **Register the URL** in the app's `urls.py` (`apps/data/urls.py`):

   ```python
   urlpatterns = [
       # ...
       path("data/water_quality", _post(views.water_quality), name="data_water_quality"),
   ]
   ```

   (`_post` is the local helper that applies `csrf_exempt` + `require_POST`;
   use it for JSON/form endpoints called by the legacy frontend.)

3. **Include the app URLconf** in `hai_x/urls.py` — already done for the
   existing apps; only needed for brand-new apps:

   ```python
   path("", include("apps.data.urls")),
   ```

4. **Add a template** if the route renders HTML. Legacy-style Jinja templates
   go to `templates/`; reference static files with `{{ static('css/style.css') }}`
   (or the Flask-compatible `url_for('static', filename=...)`) and other routes
   with `{{ url('data_water_quality') }}`.

5. Use the **route name** (`reverse("data_water_quality")` / `{{ url(...) }}`)
   instead of hardcoding paths wherever possible.

## How to Add a New Dash App

1. **Create the app module** in `apps/dashboard/dash_apps/`, e.g. `my_app.py`:

   ```python
   from django_plotly_dash import DjangoDash
   from dash import html, dcc, Input, Output

   app = DjangoDash("MyApp")
   app.layout = html.Div([dcc.Input(id="inp"), html.Div(id="out")])

   @app.callback(Output("out", "children"), Input("inp", "value"))
   def echo(value):
       return value or ""
   ```

2. **Register it at startup** by importing it in
   `apps/dashboard/apps.py::DashboardConfig.ready()`:

   ```python
   from .dash_apps import haix, my_app  # noqa: F401
   ```

3. **Embed it in a page** — either with the django-plotly-dash template tag in
   a Django-engine template:

   ```html
   {% load plotly_dash %}
   {% plotly_app name="MyApp" ratio=0.6 %}
   ```

   or, like the main dashboard (which uses Jinja templates), via the iframe
   endpoint django-plotly-dash exposes for every registered app:

   ```html
   <iframe src="/django_plotly_dash/app/MyApp/" style="width:100%;height:80vh;border:none;"></iframe>
   ```

4. **Add a Django view + URL** for the page (see the previous section).
   `django_plotly_dash` URLs are already included in `hai_x/urls.py`, and
   `X_FRAME_OPTIONS = "SAMEORIGIN"` is set so the iframes are allowed.

The main dashboard itself is `apps/dashboard/dash_apps/haix.py`
(`DjangoDash("HaixDashboard")`), embedded by `templates/dashboard.html` and
served at `/`.

## API Endpoints

All Flask-era paths are preserved. The most relevant endpoints:

### Path planning (gateway to the VRPy service)

`POST /newpath/path` (form-encoded, fields `date`, `hours`, `volume`,
`submit_btn=generate|approve|approve_all`) — generates routes covering all
areas of interest of one day. Internally Django forwards to the VRPy service:

```http
POST {VRPY_SERVICE_URL}/routePos/
{
  "vehicle_capacity": 20,
  "duration": 2,
  "aoi": {
    "1": {"amount": 5, "cords": [[lat, lon], ...]},
    ...
  }
}
→ {"routes": {"1": [[lat, lon], ...], ...}}
```

### Areas of interest (gateway to the AoI service)

`POST /newarea/get_aois` (form fields `aoi_date`, `lake_query`, `resolution`,
`cloud_coverage`, `n_areas`; Sentinel Hub credentials from cookies) — Django
forwards to the AoI estimation service:

```http
POST {AOI_SERVICE_URL}/api/get_aois
{
  "day": "2025-06-01",
  "resolution_in_m": 10.0,
  "cloud_coverage": 0.5,
  "n_areas": 5,
  "lake_query": "Maschsee, Hannover, Germany",
  "instance_id": "...", "client_id": "...", "client_secret": "..."
}
→ {"<date>": {"raw_apa": [...], "cropped_apa": [...], "gps": [...],
              "areas_of_interest": [[[lon, lat], ...], ...]}}
```

`POST /newarea/get_dates` returns the possible satellite fly-over dates
(`{AOI_SERVICE_URL}/api/get_available_dates`).

### Other gateways

* `POST /traj/load` `{"date": "YYYY-MM-DD"}` → ROS bag extraction
  (`/rosbag/extract_navsatfix`, `/rosbag/img`, `/rosbag/mpeg`,
  `/rosbag/trajectory` on the data-extraction service).
* `POST /data/bathymetry`, `POST /data/apa`, `POST /data/volume` → bathymetry /
  APA-index / volume services.
* `POST /newarea/capacitated_aoi`, `POST /newpath/capacitated` → capacitated
  clustering and path services.

Service failures are translated into clear errors: connection problems map to
**502**, timeouts to **504** (`apps/services/clients/base.py`); page-rendering
views show the error message inline instead.

## Testing

```bash
python manage.py check
python manage.py test tests
```

The test-suite mocks all HTTP calls — no service containers or database are
required. It covers URL resolution, page smoke tests, Dash registration, HTTP
method enforcement, input validation, the service-client layer (correct URL,
payload and timeout forwarding, 502/504 mapping) and the AoI gateway.

## Troubleshooting

**Dash app not rendering on `/`**
The iframe loads `/django_plotly_dash/app/HaixDashboard/`. Make sure
`django_plotly_dash` is in `INSTALLED_APPS`, its URLs are included, migrations
have been applied (`python manage.py migrate`) and `X_FRAME_OPTIONS` is
`SAMEORIGIN`. Check the server log for import errors from
`apps/dashboard/dash_apps/haix.py`.

**Missing migrations / `no such table: django_session`**
Run `python manage.py migrate`.

**Static files not loading**
Static files are served by WhiteNoise straight from `static/`. Verify the file
exists under `static/` and the page references it via `/static/...`. In
production behind a proxy run `python manage.py collectstatic` if you serve
`staticfiles/` directly.

**Sentinel Hub errors from AoI/APA features**
The `sh_instance_id` / `sh_client_id` / `sh_client_secret` variables must be
exported before `docker compose up`, or entered on the `/config` page (stored
as cookies).

**Django cannot connect to the VRPy/AoI service (502)**
The service container is not running or the URL is wrong. Inside Docker
Compose the URLs must use the **service names** (e.g.
`http://path_planning_vrpy:10002`); `localhost` inside a container points to
the container itself. For local development without Docker use
`http://localhost:<host-port>` and check the port mapping in `compose.yaml`
(e.g. bathymetry is `10007` on the host but `10005` inside the network).

**Timeout while calling an external service (504)**
Long computations may exceed `SERVICE_REQUEST_TIMEOUT` (default 30 s) —
increase it via the environment. The ROS-extraction calls already use a
45-minute timeout.

**FastAPI service returns a validation error (HTTP 422)**
The forwarded payload is missing fields — usually the Sentinel Hub credentials
(see above) or an empty date/lake selection in the form.

**`psycopg2` installation fails**
Install the PostgreSQL client headers (`libpq-dev` on Debian/Ubuntu,
`brew install postgresql` on macOS) or use `psycopg2-binary`.

**Database connection refused**
Start the PostGIS container (`docker compose up -d postgis_container`) and set
`POSTGRES_HOST` (compose: `postgis_container`, local: `localhost`).

**Database needs to be reset**
Reset the datbase with the following commands.

```bash
docker compose down -v
docker compose up --build
```

**Container registry authentication error**
`docker login git.ni.dfki.de:5050` — you need access to the HAI-x group on the
DFKI GitLab instance.

---

## Project Context

HAI-x is developed at DFKI (German Research Center for Artificial
Intelligence). The external service images are hosted on the DFKI GitLab
registry (`git.ni.dfki.de:5050`); see `compose.yaml` for the exact images.
