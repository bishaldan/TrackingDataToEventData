from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tracking_to_event.catalog import list_supported_games
from tracking_to_event.config import DetectorConfig
from tracking_to_event.metrica import reference_events_path
from tracking_to_event.models import EVENT_COLUMNS
from tracking_to_event.pipeline import generate_dataframe_for_game, generate_dataframe_from_paths
from tracking_to_event.validation import validate_generated_dataframe


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
MAX_UPLOAD_BYTES = 64 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
MAX_FRAME_ROWS = 2000


def create_app(data_dir: str | Path = "data") -> FastAPI:
    app = FastAPI(title="Tracking To Event Data", version="2.0.0")
    app.state.data_dir = str(Path(data_dir))
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = _content_security_policy()
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        games = list_supported_games(app.state.data_dir)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "games": games,
            },
        )

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/api/games")
    async def games() -> JSONResponse:
        return JSONResponse({"games": list_supported_games(app.state.data_dir)})

    @app.get("/api/analyze")
    async def analyze(
        game_id: int = Query(..., alias="gameId", ge=1),
        start_frame: int | None = Query(None, alias="startFrame", ge=0),
        end_frame: int | None = Query(None, alias="endFrame", ge=0),
    ) -> JSONResponse:
        _validate_frame_window(start_frame, end_frame)
        try:
            generated_df = generate_dataframe_for_game(
                data_dir=app.state.data_dir,
                game_id=game_id,
                input_format="metrica",
                start_frame=start_frame,
                end_frame=end_frame,
                config=DetectorConfig(),
            )
            reference_df = pd.read_csv(reference_events_path(app.state.data_dir, game_id))
            report = validate_generated_dataframe(
                generated_df=generated_df,
                reference_df=reference_df,
                game_id=game_id,
                start_frame=start_frame,
                end_frame=end_frame,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        preview_rows = _json_records(generated_df, 120)
        reference_preview = _json_records(reference_df, 40)

        return JSONResponse(
            {
                "game": {"id": game_id, "format": "metrica"},
                "summary": {
                    "eventCount": len(generated_df),
                    "previewCount": len(preview_rows),
                    "columns": EVENT_COLUMNS,
                },
                "validation": report.to_dict(),
                "events": preview_rows,
                "referencePreview": reference_preview,
                "downloadUrl": f"/api/download?gameId={game_id}&format=metrica"
                + (f"&startFrame={start_frame}" if start_frame is not None else "")
                + (f"&endFrame={end_frame}" if end_frame is not None else ""),
            }
        )

    @app.post("/api/upload")
    async def upload(
        home_file: UploadFile = File(...),
        away_file: UploadFile = File(...),
        start_frame: int | None = Form(None, ge=0),
        end_frame: int | None = Form(None, ge=0),
    ) -> JSONResponse:
        _validate_frame_window(start_frame, end_frame)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                home_path = Path(tmpdir) / _safe_upload_name(home_file.filename, "home_tracking.csv")
                away_path = Path(tmpdir) / _safe_upload_name(away_file.filename, "away_tracking.csv")
                await _write_upload_file(home_file, home_path, label="Home tracking")
                await _write_upload_file(away_file, away_path, label="Away tracking")

                generated_df = generate_dataframe_from_paths(
                    home_path=home_path,
                    away_path=away_path,
                    input_format="metrica",
                    start_frame=start_frame,
                    end_frame=end_frame,
                    config=DetectorConfig(),
                )
        except HTTPException:
            raise
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        preview_rows = _json_records(generated_df, 120)

        buffer = io.StringIO()
        generated_df.to_csv(buffer, index=False)
        csv_data = buffer.getvalue()

        return JSONResponse(
            {
                "game": {"id": "uploaded", "format": "metrica"},
                "summary": {
                    "eventCount": len(generated_df),
                    "previewCount": len(preview_rows),
                    "columns": EVENT_COLUMNS,
                },
                "validation": None,
                "events": preview_rows,
                "referencePreview": [],
                "csvData": csv_data,
            }
        )

    @app.get("/api/download")
    async def download(
        game_id: int = Query(..., alias="gameId", ge=1),
        start_frame: int | None = Query(None, alias="startFrame", ge=0),
        end_frame: int | None = Query(None, alias="endFrame", ge=0),
    ) -> StreamingResponse:
        _validate_frame_window(start_frame, end_frame)
        try:
            generated_df = generate_dataframe_for_game(
                data_dir=app.state.data_dir,
                game_id=game_id,
                input_format="metrica",
                start_frame=start_frame,
                end_frame=end_frame,
                config=DetectorConfig(),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        buffer = io.StringIO()
        generated_df.to_csv(buffer, index=False)
        buffer.seek(0)
        filename = f"game_{game_id}_events.csv"
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/frames")
    async def frames(
        game_id: int = Query(..., alias="gameId", ge=1),
        start_frame: int | None = Query(None, alias="startFrame", ge=0),
        end_frame: int | None = Query(None, alias="endFrame", ge=0),
        sample_rate: int = Query(5, alias="sampleRate", ge=1, le=20),
    ) -> JSONResponse:
        """Return sampled raw tracking frames for animated match replay."""
        from tracking_to_event.metrica import iter_metrica_frames

        _validate_frame_window(start_frame, end_frame)
        try:
            frame_list = []
            count = 0
            for fr in iter_metrica_frames(
                app.state.data_dir, game_id,
                start_frame=start_frame, end_frame=end_frame,
            ):
                count += 1
                if count % sample_rate != 0:
                    continue
                frame_list.append({
                    "frame": fr.frame,
                    "time": round(fr.time_seconds, 3),
                    "period": fr.period,
                    "ball": [round(fr.ball.x, 4), round(fr.ball.y, 4)],
                    "home": [
                        {"number": p.number, "x": round(p.x, 4), "y": round(p.y, 4)}
                        for p in fr.players if p.team == "Home"
                    ],
                    "away": [
                        {"number": p.number, "x": round(p.x, 4), "y": round(p.y, 4)}
                        for p in fr.players if p.team == "Away"
                    ],
                })
                if len(frame_list) >= MAX_FRAME_ROWS:
                    break
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return JSONResponse({"frames": frame_list, "totalSampled": len(frame_list)})

    return app


def _json_records(dataframe: pd.DataFrame, limit: int) -> list[dict[str, object]]:
    limited = dataframe.head(limit).copy()
    limited = limited.astype(object)
    limited = limited.where(pd.notnull(limited), None)
    return limited.to_dict("records")


def _content_security_policy() -> str:
    return (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'"
    )


def _validate_frame_window(start_frame: int | None, end_frame: int | None) -> None:
    if start_frame is not None and end_frame is not None and end_frame < start_frame:
        raise HTTPException(status_code=400, detail="End frame must be greater than or equal to start frame.")


def _safe_upload_name(filename: str | None, fallback_name: str) -> str:
    if not filename:
        return fallback_name

    candidate = Path(filename).name
    if not candidate.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported.")
    return candidate


async def _write_upload_file(upload_file: UploadFile, destination: Path, label: str) -> None:
    _safe_upload_name(upload_file.filename, destination.name)
    header = await upload_file.read(4096)
    if not _looks_like_csv(header):
        raise HTTPException(status_code=400, detail=f"{label} must be a valid CSV file.")
    await upload_file.seek(0)

    bytes_written = 0
    with destination.open("wb") as target:
        while True:
            chunk = await upload_file.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break

            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{label} exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.",
                )
            target.write(chunk)

    await upload_file.close()


def _looks_like_csv(payload: bytes) -> bool:
    if not payload:
        return False

    try:
        sample = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False

    rows = [line for line in sample.splitlines() if line.strip()]
    return any("," in row for row in rows[:3])
