"""Validated input contracts for the macro-expansion command."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class ExpandRequest(BaseModel):
    """Files and options required for one macro-expansion operation."""

    model_config = ConfigDict(frozen=True, strict=True)

    input_path: Path
    output_path: Path | None = None
    style_path: Path | None = None
    bibliography_path: Path | None = None
    strip: bool = True

    @field_validator("input_path", "style_path", "bibliography_path")
    @classmethod
    def require_existing_file(cls, path: Path | None) -> Path | None:
        """Reject supplied source paths that are not readable files."""
        if path is not None and not path.is_file():
            raise ValueError(f"not a file: {path}")
        return path
