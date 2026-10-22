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
    def license_declaration_url(self) -> str | None:
        if self.kind == "participation":
            return "https://raw.githubusercontent.com/nflverse/nflreadr/main/R/load_participation.R"
        return None

    @property
    def metadata_url(self) -> str:
        return f"https://api.github.com/repos/nflverse/nflverse-data/releases/tags/{self.tag}"

    @property
    def download_url(self) -> str:
        return f"https://github.com/nflverse/nflverse-data/releases/download/{self.tag}/{self.filename}"


def source_spec(kind: str, season: int) -> SourceSpec:
    if type(season) is not int or not 1999 <= season <= 2100:
        raise ValueError("season must be an integer from 1999 through 2100")
    if kind == "participation":
        if not 2023 <= season <= 2025:
            raise ValueError("reviewed FTN participation is historical 2023–2025 only")
        return SourceSpec(
            kind, season, "pbp_participation", f"pbp_participation_{season}.csv",
            "ftn-participation-csv-v1", "CC-BY-SA-4.0",
            "https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt",
            "FTN Data via nflverse",
        )
    choices = {
        "pbp": ("pbp", f"play_by_play_{season}.csv.gz", "pbp-csv-v1"),
        "rosters": ("rosters", f"roster_{season}.csv.gz", "rosters-csv-v1"),
        "depth_charts": ("depth_charts", f"depth_charts_{season}.csv.gz", "depth-2025-csv-v1"),
        "schedules": ("schedules", "games.csv.gz", "schedules-csv-v1"),
    }
    if kind not in choices:
        raise ValueError(f"unreviewed source: {kind!r}")
    if kind == "depth_charts" and season < 2025:
        raise ValueError("pre-2025 depth charts require a different schema adapter")
    tag, filename, schema = choices[kind]
    return SourceSpec(
        kind, season, tag, filename, schema, "CC-BY-4.0",
        "https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md",
        "Lee Sharpe (nfldata) via nflverse" if kind == "schedules" else "nflverse contributors; source-specific upstream credits retained with source metadata",
    )
