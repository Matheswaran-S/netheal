"""Formatting and CSV export helpers (no Streamlit dependency)."""
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from core.simulation import SimulationResult

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"


def format_route(path) -> str:
    return " → ".join(path) if path else "No route"


def results_frame(results: dict[str, SimulationResult]) -> pd.DataFrame:
    """One row per run: configuration + every metric."""
    rows = []
    for mode, r in results.items():
        cfg = r.config
        rows.append({"mode": mode, "source": cfg.source, "destination": cfg.destination,
                     "seed": cfg.seed, "duration_s": cfg.duration, "link_loss": cfg.link_loss,
                     "failures": "; ".join(f"{f.kind}:{f.label}@{f.time}s" for f in cfg.failures),
                     "final_route": format_route(r.final_route), **asdict(r.metrics)})
    return pd.DataFrame(rows)


def events_frame(result: SimulationResult) -> pd.DataFrame:
    cfg = result.config
    return pd.DataFrame([{"timestamp": round(e.time, 6), "event_type": e.event_type.value,
                          "packet_id": e.packet_id, "source": cfg.source,
                          "destination": cfg.destination, "element": e.element,
                          "message": e.message} for e in result.events],
                        columns=["timestamp", "event_type", "packet_id", "source",
                                 "destination", "element", "message"])


def comparison_frame(results: dict[str, SimulationResult]) -> pd.DataFrame:
    """Metric-by-mode table shown in the dashboard."""
    frame = results_frame(results).set_index("mode")
    metric_cols = list(asdict(next(iter(results.values())).metrics))
    return frame[metric_cols].T.rename_axis("metric")


def export_csv(results: dict[str, SimulationResult], directory: Path = EXPORT_DIR) -> list[Path]:
    """Write simulation_results.csv and event_log.csv (one per mode)."""
    directory.mkdir(parents=True, exist_ok=True)
    written = [directory / "simulation_results.csv"]
    results_frame(results).to_csv(written[0], index=False)
    for mode, result in results.items():
        path = directory / f"event_log_{mode.replace(' ', '_').lower()}.csv"
        events_frame(result).to_csv(path, index=False)
        written.append(path)
    return written
