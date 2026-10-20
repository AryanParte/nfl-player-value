"""Explicit public-source choices; loader licenses do not license their data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    season: int
    tag: str
    filename: str
    schema_version: str
    license_id: str
    license_url: str
    attribution: str

    @property
    def metadata_url(self) -> str:
        return f"https://api.github.com/repos/nflverse/nflverse-data/releases/tags/{self.tag}"

    @property
    def download_url(self) -> str:
        return f"https://github.com/nflverse/nflverse-data/releases/download/{self.tag}/{self.filename}"


def source_spec(kind: str, season: int) -> SourceSpec:
    if type(season) is not int or not 1999 <= season <= 2100:
        raise ValueError("season must be an integer from 1999 through 2100")
    choices = {
        "pbp": ("pbp", f"play_by_play_{season}.csv.gz", "pbp-csv-v1"),
        "rosters": ("rosters", f"roster_{season}.csv.gz", "rosters-csv-v1"),
        "depth_charts": ("depth_charts", f"depth_charts_{season}.csv.gz", "depth-2025-csv-v1"),
    }
    if kind not in choices:
        raise ValueError(f"unreviewed source: {kind!r}")
    if kind == "depth_charts" and season < 2025:
        raise ValueError("pre-2025 depth charts require a different schema adapter")
    tag, filename, schema = choices[kind]
    return SourceSpec(
        kind, season, tag, filename, schema, "CC-BY-4.0",
        "https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md",
        "nflverse contributors; source-specific upstream credits retained with source metadata",
    )
