from pathlib import Path

from pydantic import BaseModel

from media_manager.common.import_match import ImportMatchConfidence
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult


class MediaImportSuggestion(BaseModel):
    directory: Path
    match: MetaDataProviderSearchResult | None = None
    """The single best match for the directory, or None when nothing matched."""
    confidence: ImportMatchConfidence = ImportMatchConfidence.none
