from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import get_report_service
from app.schemas.report import Report, ReportCreate
from app.services.report_service import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportService,
)

router = APIRouter(prefix="/reports", tags=["Reports"])
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


@router.get("", response_model=list[Report])
def get_reports(service: ReportServiceDep) -> list[Report]:
    return service.get_all_reports()


@router.post("", response_model=Report, status_code=status.HTTP_201_CREATED)
def create_report(
    report: ReportCreate,
    service: ReportServiceDep,
) -> Report:
    try:
        return service.create_report(report)
    except DuplicateReportError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: int, request: Request, response: Response, service: ReportServiceDep) -> dict:
    cache = request.app.state.cache

    cached, source = cache.get(report_id)
    if cached is not None:
        response.headers["X-Cache"] = source
        return cached

    try:
        report_obj = service.get_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono zgłoszenia.",
        ) from exc

    payload = report_obj.model_dump(mode="json")

    if source != "BYPASS" and not cache.put(report_id, payload):
        source = "BYPASS"

    response.headers["X-Cache"] = source
    return payload


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, request: Request, service: ReportServiceDep) -> None:
    try:
        service.delete_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono zgłoszenia.",
        ) from exc

    cache = request.app.state.cache
    cache.delete(report_id)