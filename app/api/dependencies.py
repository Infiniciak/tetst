from fastapi import Request

from app.repositories.interfaces import ReportRepository
from app.services.report_service import ReportService


def get_report_repository(request: Request) -> ReportRepository:
    return request.app.state.report_repository


def get_report_service(request: Request) -> ReportService:
    return ReportService(get_report_repository(request))
