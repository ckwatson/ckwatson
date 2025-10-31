# CKWatson AI Coding Instructions

## Project Overview

CKWatson is a chemical kinetics educational game built with Flask. Players solve "puzzles" by proposing elementary reactions to match experimental data. The app simulates chemical reactions using numerical integration and provides real-time feedback through plots.

## Architecture & Key Components

### Core Structure (3-layer)

- **`kernel/`** - Chemical simulation engine (pure Python, no Flask dependencies)
  - `data/` - Chemical data models (puzzle, reaction_mechanism, solution classes)
  - `engine/` - Simulation algorithms (driver.py for equilibration, plotter.py for visualization)
- **`web/`** - Flask web application layer
  - `main.py` - Flask app with SSE, caching, rate limiting
  - `run_simulation.py` - Orchestrates kernel simulations for web requests
  - `redis_utils.py` - Redis SSE streaming for long-running jobs
- **`puzzles/`** - JSON puzzle definitions with chemical data

### Data Flow Pattern

1. User submits reactions via `play.html` → `/plot` endpoint
2. `handle_plot_request()` calls `simulate_experiments_and_plot()`
3. Simulation runs both "true" (correct) and "proposed" (user) experiments
4. Results cached by request hash, streamed via Redis SSE if available
5. SVG plots returned as JSON for frontend rendering

### Key Dependencies & Infrastructure

- **Flask Extensions**: Flask-SSE (real-time updates), Flask-Caching (Redis-backed), Flask-Limiter (rate limiting), Flask-Compress (gzip SVGs)
- **Scientific Stack**: NumPy/SciPy for numerical integration, Matplotlib for plotting
- **Optional Redis**: Enables SSE streaming and distributed caching (gracefully degrades without)

## Development Workflow

### Running & Testing

```bash
# Start development server
just run  # Uses gunicorn with gevent workers, 6000s timeout for long simulations

# Run tests with coverage
just test  # Runs pytest with coverage for web/ and kernel/engine/

# Optional: Start Redis for SSE features
redis-server
```

### Project Conventions

#### File Organization

- Puzzle files: `puzzles/*.json` (JSON format, validated against `schema.json`)
- Templates: Standard Flask structure in `web/templates/` with Bootstrap 5
- Static assets: `web/static/` with CSS/JS following standard naming

#### Chemical Data Models

- **Puzzle Class**: Extends `reaction_mechanism`, defines species, reactions, energies
- **Coefficient Arrays**: 2D NumPy arrays where rows=reactions, cols=species
- **Reagent Dictionary**: Maps starting materials to pre-equilibration mechanisms

#### Caching Strategy

Cache key generation in `make_plot_cache_key()` hashes: puzzle name, reactions, temperature, conditions. Results include SVG plots as strings for frontend rendering.

## Frontend Integration Patterns

### Real-time Updates

When Redis available: logging streams to frontend via SSE channels (job ID = channel name). JavaScript listens on `/stream/<jobID>` for progress updates during long simulations.

### Form Validation

- Puzzle names: `^[\w\- ]+$` pattern (alphanumeric + dash/underscore/space)
- Chemical formulas: `^\\w*$` pattern in schema validation
- JSON schema validation for all puzzle submissions in `/save` endpoint

### Error Handling

- Graceful Redis degradation (SSE disabled, simple caching fallback)
- Comprehensive logging with `colorlog` for development
- Client-side validation before server submission

## Security & Performance

### Rate Limiting

- Default: 200/day, 50/hour per IP
- Puzzle creation: 5/minute (authenticated with `CKWATSON_PUZZLE_AUTH_CODE`)
- Redis-backed storage when available, in-memory fallback

### Authentication

Single environment variable `AUTH_CODE` for puzzle creation. Production deployments should use strong random values.

## Deployment Configurations

- **Render.com**: Primary deployment via `render.yaml`
- **Docker**: Single container or compose with Redis
- **Kubernetes**: Manifests in `k8s/` with resource limits and health checks
- **Development**: Local with `just run`, optional Redis

When modifying chemical simulations, understand that `equilibrate()` function in `driver.py` is the core - it finds rate constants, reaction profiles, and flat regions for equilibrium detection.
