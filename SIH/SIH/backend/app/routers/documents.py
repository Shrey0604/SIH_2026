from typing import Annotated, Any

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.container import AppContainer
from app.dependencies import get_container


router = APIRouter(tags=["documents"])


@router.post("/documents/upload", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    container: Annotated[AppContainer, Depends(get_container)],
    file: UploadFile = File(...),
    document_type: str = Form("DDR"),
    well_id: str = Form("ctx-rj-01"),
) -> dict[str, object]:
    content = await file.read(20 * 1024 * 1024 + 1)
    if container.ingestion is None:
        raise HTTPException(status_code=503, detail="Ingestion service is unavailable")
    try:
        created = container.ingestion.create_upload(
            filename=file.filename or "report.pdf",
            content_type=file.content_type,
            content=content,
            document_type=document_type,
            well_id=well_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=503, detail=f"Document storage is unavailable: {error}"
        ) from error
    if not created["duplicate"]:
        background_tasks.add_task(
            container.ingestion.process,
            str(created["ingestion_job_id"]),
            str(created["document_id"]),
            content,
        )
    return created


@router.get("/ingestion/{job_id}")
def get_ingestion_job(
    job_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> dict[str, Any]:
    job = container.repository.get_ingestion_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return job


@router.get("/documents")
def list_documents(
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[dict[str, Any]]:
    return container.repository.list_documents()


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> dict[str, Any]:
    document = container.repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/documents/{document_id}/chunks")
def list_document_chunks(
    document_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[dict[str, Any]]:
    if container.repository.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return container.repository.list_document_chunks(document_id)


@router.get("/documents/{document_id}/page/{page_number}")
def get_document_page(
    document_id: str,
    page_number: int,
    container: Annotated[AppContainer, Depends(get_container)],
) -> Response:
    try:
        png, document = container.evidence.render_page_png(document_id, page_number)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except IndexError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, pymupdf.FileDataError) as error:
        raise HTTPException(status_code=422, detail="Document page could not be rendered") from error
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Content-Disposition": (
                f'inline; filename="{document["filename"]}-page-{page_number}.png"'
            ),
            "Cache-Control": "private, max-age=300",
        },
    )
