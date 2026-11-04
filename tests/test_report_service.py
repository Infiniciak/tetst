import pytest

from app.repositories.report_repository import InMemoryReportRepository
from app.schemas.report import ReportCreate
from app.services.report_service import (
    DuplicateReportError,
    ReportNotFoundError,
    ReportService,
)


def sample_report(description: str = "Printer is offline") -> ReportCreate:
    return ReportCreate(
        department_id=1,
        reported_by="Alice",
        report_type="Hardware",
        description=description,
    )


def test_service_creates_report() -> None:
    service = ReportService(InMemoryReportRepository())

    report = service.create_report(sample_report())

    assert report.id == 1
    assert report.description == "Printer is offline"
    assert service.get_report(report.id) == report


def test_service_rejects_duplicate_without_adding_second_report() -> None:
    repository = InMemoryReportRepository()
    service = ReportService(repository)
    service.create_report(sample_report())

    with pytest.raises(DuplicateReportError):
        service.create_report(sample_report())

    assert len(service.get_all_reports()) == 1


def test_service_raises_when_report_does_not_exist() -> None:
    service = ReportService(InMemoryReportRepository())

    with pytest.raises(ReportNotFoundError):
        service.get_report(123)

def test_service_deletes_report() -> None:
    repository = InMemoryReportRepository()
    service = ReportService(repository)
    report = service.create_report(sample_report())

    service.delete_report(report.id)
    
    with pytest.raises(ReportNotFoundError):
        service.get_report(report.id)