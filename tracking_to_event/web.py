from __future__ import annotations

import io
import shutil
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


def create_app(data_dir: str | Path = "data") -> FastAPI:
    app = FastAPI(title="Tracking To Event Data", version="1.0.0")
    app.state.data_dir = str(data_dir)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    async def landing(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "landing.html",
            {},
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        games = list_supported_games(app.state.data_dir)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "games": games,
                "default_data_dir": app.state.data_dir,
            },
        )

    @app.get("/api/games")
    async def games() -> JSONResponse:
        return JSONResponse({"games": list_supported_games(app.state.data_dir)})

    @app.get("/api/analyze")
    async def analyze(
        game_id: int = Query(..., alias="gameId"),
        start_frame: int | None = Query(None, alias="startFrame"),
        end_frame: int | None = Query(None, alias="endFrame"),
    ) -> JSONResponse:
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
        start_frame: int | None = Form(None),
        end_frame: int | None = Form(None),
    ) -> JSONResponse:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                home_path = Path(tmpdir) / (home_file.filename or "home.csv")
                away_path = Path(tmpdir) / (away_file.filename or "away.csv")
                
                with home_path.open("wb") as f:
                    shutil.copyfileobj(home_file.file, f)
                with away_path.open("wb") as f:
                    shutil.copyfileobj(away_file.file, f)

                generated_df = generate_dataframe_from_paths(
                    home_path=home_path,
                    away_path=away_path,
                    input_format="metrica",
                    start_frame=start_frame,
                    end_frame=end_frame,
                    config=DetectorConfig(),
                )
        except Exception as exc:
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
        game_id: int = Query(..., alias="gameId"),
        start_frame: int | None = Query(None, alias="startFrame"),
        end_frame: int | None = Query(None, alias="endFrame"),
    ) -> StreamingResponse:
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
        game_id: int = Query(..., alias="gameId"),
        start_frame: int | None = Query(None, alias="startFrame"),
        end_frame: int | None = Query(None, alias="endFrame"),
        sample_rate: int = Query(5, alias="sampleRate"),
    ) -> JSONResponse:
        """Return sampled raw tracking frames for animated match replay."""
        from tracking_to_event.metrica import iter_metrica_frames

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
                        [round(p.x, 4), round(p.y, 4), p.number]
                        for p in fr.players if p.team == "Home"
                    ],
                    "away": [
                        [round(p.x, 4), round(p.y, 4), p.number]
                        for p in fr.players if p.team == "Away"
                    ],
                })
                if len(frame_list) >= 2000:
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
