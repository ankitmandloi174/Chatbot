"""Dataset upload / listing / deletion endpoints."""

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.deps import get_dataset_service, get_settings
from app.core.config import Settings
from app.core.exceptions import BadRequestError
from app.schemas.dataset import DatasetOut, RelationshipOut, UploadFailure, UploadResponse
from app.services.ingestion.dataset_service import DatasetService, PreparedDataset, prepare_dataset
from app.services.ingestion.loader import validate_filename

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
logger = logging.getLogger(__name__)
_CHUNK = 1024 * 1024


async def _save_upload(file: UploadFile, destination: Path, max_bytes: int) -> None:
    """Stream an upload to disk, enforcing the size limit."""
    written = 0
    with destination.open("wb") as out:
        while chunk := await file.read(_CHUNK):
            written += len(chunk)
            if written > max_bytes:
                raise BadRequestError(f"file exceeds the {max_bytes // (1024 * 1024)} MB limit")
            out.write(chunk)


@router.post("", response_model=UploadResponse)
async def upload_datasets(
    files: list[UploadFile],
    settings: Settings = Depends(get_settings),
    service: DatasetService = Depends(get_dataset_service),
) -> UploadResponse:
    """Upload several CSVs; each is validated, cleaned and profiled in parallel."""
    if not files:
        raise BadRequestError("No files provided")
    if len(files) > settings.max_files_per_upload:
        raise BadRequestError(f"At most {settings.max_files_per_upload} files per upload")

    names = [f.filename or "dataset.csv" for f in files]
    table_names = await run_in_threadpool(service.reserve_table_names, names)
    semaphore = asyncio.Semaphore(settings.max_upload_workers)

    async def process(file: UploadFile, name: str, table_name: str) -> PreparedDataset:
        raw_path = settings.raw_dir / f"{uuid4()}.csv"
        async with semaphore:
            try:
                validate_filename(name)
                await _save_upload(file, raw_path, settings.max_upload_bytes)
                return await run_in_threadpool(
                    prepare_dataset, raw_path, name, table_name, settings.parquet_dir, settings
                )
            finally:
                raw_path.unlink(missing_ok=True)

    results = await asyncio.gather(
        *(process(f, n, t) for f, n, t in zip(files, names, table_names)), return_exceptions=True
    )

    response = UploadResponse(datasets=[], failures=[], relationships=[])
    for name, outcome in zip(names, results):
        if isinstance(outcome, BaseException):
            if not isinstance(outcome, BadRequestError):
                logger.error("upload failed", extra={"file": name}, exc_info=outcome)
            message = outcome.message if isinstance(outcome, BadRequestError) else f"processing failed: {outcome}"
            response.failures.append(UploadFailure(filename=name, error=message))
            continue
        dataset, relationships = await run_in_threadpool(service.register, outcome)
        response.datasets.append(DatasetOut.model_validate(dataset))
        response.relationships.extend(RelationshipOut.model_validate(r) for r in relationships)
    return response


@router.get("", response_model=list[DatasetOut])
def list_datasets(service: DatasetService = Depends(get_dataset_service)) -> list[DatasetOut]:
    return [DatasetOut.model_validate(d) for d in service.list_datasets()]


@router.get("/relationships", response_model=list[RelationshipOut])
def list_relationships(service: DatasetService = Depends(get_dataset_service)) -> list[RelationshipOut]:
    return [RelationshipOut.model_validate(r) for r in service.list_relationships()]


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, service: DatasetService = Depends(get_dataset_service)) -> None:
    service.delete(dataset_id)
