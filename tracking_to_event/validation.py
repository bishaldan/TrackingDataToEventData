from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tracking_to_event.config import DetectorConfig
from tracking_to_event.metrica import reference_events_path
from tracking_to_event.pipeline import generate_dataframe_for_game


SUPPORTED_TYPES = {"SET PIECE", "PASS", "BALL LOST", "RECOVERY", "BALL OUT", "SHOT"}


@dataclass(slots=True)
class ValidationReport:
    game_id: int
    generated_event_count: int
    reference_event_count: int
    supported_reference_count: int
    matched_event_count: int
    matched_ratio: float
    sequence_agreement: float
    mean_start_frame_error: float | None
    type_counts: list[dict[str, object]]

    def render(self) -> str:
        lines = [
            f"Validation report for game {self.game_id}",
            f"Generated events: {self.generated_event_count}",
            f"Reference events: {self.reference_event_count}",
            f"Supported reference events: {self.supported_reference_count}",
            f"Matched events: {self.matched_event_count}",
            f"Matched ratio: {self.matched_ratio:.2%}",
            f"Sequence agreement: {self.sequence_agreement:.2%}",
        ]
        if self.mean_start_frame_error is not None:
            lines.append(f"Mean start frame error: {self.mean_start_frame_error:.2f}")
        lines.append("Type counts:")
        for row in self.type_counts:
            lines.append(
                f"  - {row['Type']}: generated={row['Generated']} reference={row['Reference']} delta={row['Delta']}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "gameId": self.game_id,
            "generatedEventCount": self.generated_event_count,
            "referenceEventCount": self.reference_event_count,
            "supportedReferenceCount": self.supported_reference_count,
            "matchedEventCount": self.matched_event_count,
            "matchedRatio": self.matched_ratio,
            "sequenceAgreement": self.sequence_agreement,
            "meanStartFrameError": self.mean_start_frame_error,
            "typeCounts": self.type_counts,
        }


def validate_game(
    data_dir: str | Path,
    game_id: int,
    input_format: str = "metrica",
    start_frame: int | None = None,
    end_frame: int | None = None,
    config: DetectorConfig | None = None,
    generated_output_path: str | Path | None = None,
) -> ValidationReport:
    generated_df = generate_dataframe_for_game(
        data_dir=data_dir,
        game_id=game_id,
        input_format=input_format,
        start_frame=start_frame,
        end_frame=end_frame,
        config=config,
    )
    if generated_output_path is not None:
        generated_df.to_csv(generated_output_path, index=False)

    reference_df = pd.read_csv(reference_events_path(data_dir, game_id))
    return validate_generated_dataframe(
        generated_df=generated_df,
        reference_df=reference_df,
        game_id=game_id,
        start_frame=start_frame,
        end_frame=end_frame,
    )


def validate_generated_dataframe(
    generated_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    game_id: int,
    start_frame: int | None = None,
    end_frame: int | None = None,
) -> ValidationReport:
    supported_reference_df = reference_df[reference_df["Type"].isin(SUPPORTED_TYPES)].copy()

    if start_frame is not None:
        supported_reference_df = supported_reference_df[supported_reference_df["Start Frame"] >= start_frame]
    if end_frame is not None:
        supported_reference_df = supported_reference_df[supported_reference_df["Start Frame"] <= end_frame]

    type_counts = _type_counts(generated_df, supported_reference_df)
    matched_event_count, matched_ratio, mean_start_frame_error = _match_summary(generated_df, supported_reference_df)
    sequence_agreement = _sequence_agreement(generated_df, supported_reference_df)

    return ValidationReport(
        game_id=game_id,
        generated_event_count=len(generated_df),
        reference_event_count=len(reference_df),
        supported_reference_count=len(supported_reference_df),
        matched_event_count=matched_event_count,
        matched_ratio=matched_ratio,
        sequence_agreement=sequence_agreement,
        mean_start_frame_error=mean_start_frame_error,
        type_counts=type_counts,
    )


def _type_counts(generated_df: pd.DataFrame, reference_df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    all_types = sorted(set(generated_df.get("Type", pd.Series(dtype=object)).dropna()) | set(reference_df["Type"].dropna()))
    for event_type in all_types:
        generated_count = int((generated_df["Type"] == event_type).sum()) if "Type" in generated_df else 0
        reference_count = int((reference_df["Type"] == event_type).sum())
        rows.append(
            {
                "Type": event_type,
                "Generated": generated_count,
                "Reference": reference_count,
                "Delta": generated_count - reference_count,
            }
        )
    return rows


def _match_summary(
    generated_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    tolerance: int = 75,
) -> tuple[int, float, float | None]:
    generated_records = generated_df.to_dict("records")
    reference_records = reference_df.to_dict("records")
    used_reference_indices: set[int] = set()
    diffs: list[int] = []

    for generated in generated_records:
        best_index: int | None = None
        best_diff: int | None = None
        for index, reference in enumerate(reference_records):
            if index in used_reference_indices:
                continue
            if reference["Type"] != generated["Type"]:
                continue
            if reference["Team"] != generated["Team"]:
                continue
            diff = abs(int(reference["Start Frame"]) - int(generated["Start Frame"]))
            if best_diff is None or diff < best_diff:
                best_index = index
                best_diff = diff
        if best_index is not None and best_diff is not None and best_diff <= tolerance:
            used_reference_indices.add(best_index)
            diffs.append(best_diff)

    matched_count = len(diffs)
    matched_ratio = matched_count / max(len(reference_records), 1)
    mean_diff = (sum(diffs) / len(diffs)) if diffs else None
    return matched_count, matched_ratio, mean_diff


def _sequence_agreement(generated_df: pd.DataFrame, reference_df: pd.DataFrame) -> float:
    generated_sequence = [f"{row['Team']}::{row['Type']}" for row in generated_df.to_dict("records")]
    reference_sequence = [f"{row['Team']}::{row['Type']}" for row in reference_df.to_dict("records")]
    comparable = min(len(generated_sequence), len(reference_sequence))
    if comparable == 0:
        return 0.0
    matches = sum(1 for left, right in zip(generated_sequence, reference_sequence) if left == right)
    return matches / comparable
