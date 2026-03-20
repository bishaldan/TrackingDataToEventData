# Project Documentation

## Overview

`TrackingDataToEventData` is a Docker-first Python project that converts football tracking data into a simplified Metrica-style event feed.

The current implementation focuses on:

- Metrica CSV sample games included in [`data/`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/data)
- Rule-based possession and event detection
- CLI workflows for generation, validation, testing, and serving a web app
- A browser frontend for running analysis and previewing results
- Docker as the default runtime

The project does **not** currently support the FIFA/EPTS sample in `Sample_Game_3`, and it no longer depends on the missing `FootballMatchAnalysis` package that the original prototype used.

## What Problem This Project Solves

Football tracking data gives frame-by-frame positions for the ball and players, but analysts often need event-style data such as:

- `PASS`
- `RECOVERY`
- `BALL LOST`
- `BALL OUT`
- `SET PIECE`
- `SHOT`

This project attempts to infer those events from tracking coordinates alone.

In practical terms, it:

1. Reads raw tracking CSVs.
2. Detects which player likely controls the ball in each frame.
3. Groups frame-level control into possession segments.
4. Converts possession transitions into event records.
5. Compares generated events with the included reference event files.

## Current Features

### CLI

The package exposes these commands through [`tracking_to_event/cli.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/cli.py):

- `generate`
- `validate`
- `test`
- `serve`

### Frontend

The web app is powered by FastAPI and serves:

- a dashboard homepage
- sample game selection
- event generation + validation in one request
- generated event preview table
- reference event preview table
- validation summary cards
- CSV download endpoint

### Docker Workflow

The Docker image is defined in [`Dockerfile`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/Dockerfile) and starts the web server by default.

### Validation

The project can compare generated outputs against the included labeled event files and report:

- generated event count
- supported reference event count
- matched event count
- matched ratio
- sequence agreement
- mean start frame error
- type-by-type count comparison

## Project Architecture

### High-Level Flow

The full application flow is:

1. Input tracking data is loaded from `data/Sample_Game_*`.
2. Frames are parsed into internal models.
3. The detector estimates controller changes and ball-out segments.
4. The pipeline turns segments into event records.
5. The validator compares generated records to the reference CSV.
6. Results are exposed either through the CLI or the frontend API.

### Main Modules

#### [`tracking_to_event/cli.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/cli.py)

This is the primary entrypoint for the package.

Responsibilities:

- parse command-line arguments
- call generation and validation logic
- run tests
- launch the frontend server

#### [`tracking_to_event/web.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/web.py)

This module creates the FastAPI app.

Routes:

- `/`
- `/api/games`
- `/api/analyze`
- `/api/download`

Responsibilities:

- serve the HTML UI
- return supported sample games
- generate events and validation results as JSON
- stream generated CSV downloads

#### [`tracking_to_event/catalog.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/catalog.py)

Provides discovery of sample games from the `data/` directory.

Responsibilities:

- find supported sample games
- expose file names and metadata for the frontend

#### [`tracking_to_event/metrica.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/metrica.py)

Handles the Metrica-specific input format.

Responsibilities:

- locate tracking files
- locate reference event files
- read Metrica tracking CSV structure
- merge home and away player positions into a unified frame stream
- tolerate frames where the ball is missing

#### [`tracking_to_event/models.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/models.py)

Defines the core internal data structures.

Important types:

- `PlayerPosition`
- `BallPosition`
- `FrameRecord`
- `PossessionSegment`
- `BallOutSegment`
- `EventRecord`

#### [`tracking_to_event/config.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/config.py)

Defines detector thresholds and JSON-based config overrides.

Current configurable values include:

- `control_radius`
- `sticky_radius`
- `competing_radius`
- `switch_confirmation_frames`
- `ball_out_tolerance`
- `goal_y_min`
- `goal_y_max`

#### [`tracking_to_event/geometry.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/geometry.py)

Contains geometry and pitch-boundary helper logic.

Responsibilities:

- player-to-ball distance calculations
- ball-out checks
- touchline vs goal-line classification
- shot path checks toward goal

#### [`tracking_to_event/detector.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/detector.py)

This module converts frames into possession-related segments.

Responsibilities:

- identify the likely controlling player
- keep possession sticky across noisy frames
- detect contested/on-ball players
- debounce team/player switches
- emit `PossessionSegment` and `BallOutSegment`

#### [`tracking_to_event/events.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/events.py)

Creates event records from detected segments.

Responsibilities:

- generate `PASS`
- generate `BALL LOST`
- generate `RECOVERY`
- generate `BALL OUT`
- generate `SET PIECE`
- generate `SHOT`
- classify restart subtype

#### [`tracking_to_event/pipeline.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/pipeline.py)

This is the orchestration layer for event generation.

Responsibilities:

- run frame loading
- run detection
- build event records from segments
- convert events to dataframes
- write CSV output

#### [`tracking_to_event/validation.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/validation.py)

Compares generated data against labeled reference data.

Responsibilities:

- filter to supported event types
- compare counts
- estimate matching quality
- render textual reports
- expose structured validation payloads for the frontend

## Frontend Architecture

### Files

- HTML template: [`tracking_to_event/templates/index.html`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/templates/index.html)
- CSS: [`tracking_to_event/static/app.css`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/static/app.css)
- JavaScript: [`tracking_to_event/static/app.js`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/static/app.js)

### What The Frontend Does

The frontend is intentionally lightweight. It does not have a separate JavaScript framework build step.

It works like this:

1. The HTML page renders the available sample games.
2. The user selects a game and optional frame range.
3. The browser calls `/api/analyze`.
4. The backend generates events and validation metrics.
5. The frontend renders:
   - summary cards
   - type count table
   - generated event preview
   - reference event preview
6. The user can download the generated CSV from `/api/download`.

### Why This Frontend Was Chosen

This frontend keeps the project simple:

- no Node.js toolchain
- no frontend build pipeline
- no extra runtime container
- easy Docker integration
- fast iteration while the detector logic is still evolving

## Supported Input Format

The supported v1 format is Metrica CSV.

Expected files for each game:

- `Sample_Game_<id>_RawTrackingData_Home_Team.csv`
- `Sample_Game_<id>_RawTrackingData_Away_Team.csv`
- `Sample_Game_<id>_RawEventsData.csv`

The loader assumes the standard Metrica layout:

- first rows contain team and player metadata
- each later row contains frame-level player coordinates and ball coordinates

## Generated Output Schema

Generated event CSVs use the following columns:

- `Team`
- `Type`
- `Subtype`
- `Period`
- `Start Frame`
- `Start Time [s]`
- `End Frame`
- `End Time [s]`
- `From`
- `To`
- `Start X`
- `Start Y`
- `End X`
- `End Y`

These are defined centrally in [`tracking_to_event/models.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tracking_to_event/models.py).

## Supported Generated Event Types

The current detector generates:

- `SET PIECE`
- `PASS`
- `BALL LOST`
- `RECOVERY`
- `BALL OUT`
- `SHOT`

Current restart subtypes inferred by rules:

- `KICK OFF`
- `THROW IN`
- `CORNER KICK`
- `GOAL KICK`

## Detection Logic

### Possession Detection

The detector estimates control using distance from the ball.

Important concepts:

- `control_radius`: player is close enough to be considered in control
- `sticky_radius`: active controller can stay controller with a slightly larger tolerance
- `competing_radius`: nearby players are considered contesting the ball
- `switch_confirmation_frames`: a possible new controller must persist before a switch is accepted

This helps reduce noise and overreacting to one-frame player switches.

### Ball Out Detection

The geometry helpers determine whether the ball has left the pitch:

- outside horizontal bounds -> goal line
- outside vertical bounds -> touchline

The pipeline then decides whether the next event should look like:

- ball out
- restart
- goal / shot followed by kickoff

### Event Building

Event generation currently uses a simple transition model:

- same-team possession change -> `PASS`
- different-team possession change -> `BALL LOST` + `RECOVERY`
- possession ending with out-of-bounds -> `BALL OUT`
- goal-line path through the goal mouth -> `SHOT`
- restart after goal or ball out -> `SET PIECE`

## Validation Logic

Validation compares generated events with the included reference event file for the same game.

The current report includes:

- total generated events
- total reference events
- supported reference events
- matched events
- matched ratio
- sequence agreement
- mean start frame error
- per-type count deltas

Validation currently focuses only on supported event types:

- `SET PIECE`
- `PASS`
- `BALL LOST`
- `RECOVERY`
- `BALL OUT`
- `SHOT`

It intentionally ignores reference-only types that the current detector does not infer yet, such as:

- `CHALLENGE`
- `CARD`
- `FAULT RECEIVED`

## How To Run The Project

### Recommended: Docker Frontend

Build the image:

```bash
docker build -t tracking-to-event .
```

Run the web app:

```bash
docker run --rm \
  -p 8000:8000 \
  -v "$PWD/data:/app/data:ro" \
  tracking-to-event
```

Open:

- [http://localhost:8000](http://localhost:8000)

### Docker CLI

Generate CSV:

```bash
docker run --rm \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/out:/app/out" \
  tracking-to-event \
  generate \
  --data-dir /app/data \
  --game-id 1 \
  --format metrica \
  --output /app/out/game_1_events.csv
```

Validate:

```bash
docker run --rm \
  -v "$PWD/data:/app/data:ro" \
  tracking-to-event \
  validate \
  --data-dir /app/data \
  --game-id 1 \
  --format metrica
```

Run tests:

```bash
docker run --rm tracking-to-event test
```

### Local Python

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run the web app:

```bash
python -m tracking_to_event serve --data-dir ./data --host 127.0.0.1 --port 8000
```

Run generation:

```bash
python -m tracking_to_event generate \
  --data-dir ./data \
  --game-id 1 \
  --format metrica \
  --output ./out/game_1_events.csv
```

Run validation:

```bash
python -m tracking_to_event validate \
  --data-dir ./data \
  --game-id 1 \
  --format metrica
```

Run tests:

```bash
python -m tracking_to_event test
```

## Testing

The tests are in [`tests/`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tests).

Current coverage includes:

- geometry helpers
- detector behavior
- pipeline behavior
- frontend/API smoke tests

Important files:

- [`tests/test_geometry.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tests/test_geometry.py)
- [`tests/test_detector.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tests/test_detector.py)
- [`tests/test_pipeline.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tests/test_pipeline.py)
- [`tests/test_web.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/tests/test_web.py)

## Legacy Files

These files come from the earlier prototype and are no longer the main runtime path:

- [`parse_possessions.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/parse_possessions.py)
- [`utils/generate.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/utils/generate.py)
- [`utils/utils.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/utils/utils.py)

[`generate_event_data.py`](/Users/bishalmahatchhetri/Developer/Personal/Personal%20Project%20/TrackingDataToEventData/generate_event_data.py) now acts as a compatibility wrapper around the new package entrypoint.

## Current Limitations

- Only the Metrica CSV path is supported
- `Sample_Game_3` is not supported yet
- Event detection is still heuristic and not fully accurate
- The system currently over-detects some `BALL LOST` and `RECOVERY` events
- Advanced event subtypes such as fouls, cards, aerial challenges, and most shot/pass subtypes are not inferred yet
- Validation is useful for comparison, but it is still a simplified evaluation model

## Recommended Next Steps

The strongest next improvements would be:

1. Improve possession switching accuracy to reduce false `BALL LOST` and `RECOVERY` events.
2. Expand restart and shot subtype classification.
3. Add richer debugging views in the frontend, such as mismatch inspection and timeline visualization.
4. Support uploaded datasets instead of only bundled sample games.
5. Add support for additional tracking formats such as FIFA/EPTS.

## Quick Summary

This project is now:

- runnable
- Docker-first
- package-based instead of script-only
- test-backed
- able to generate and validate events
- equipped with a browser frontend

It is a solid base for improving event-detection quality and growing toward a more complete football analytics tool.
