from app.repositories.interfaces import ReportRepository
from app.schemas.report import Report, ReportCreate


class DuplicateReportError(Exception):
    pass


class ReportNotFoundError(Exception):
    pass


class ReportService:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def get_all_reports(self) -> list[Report]:
        return self._repository.all()

    def get_report(self, report_id: int) -> Report:
        report = self._repository.get(report_id)
        if report is None:
            raise ReportNotFoundError(f"Zgłoszenie o id {report_id} nie zostało znalezione")
        return report

    def create_report(self, data: ReportCreate) -> Report:
        if self._repository.find_by_desc(data.description) is not None:
            raise DuplicateReportError(
                "Zgłoszenie z takim opisem już istnieje."
            )
        return self._repository.add(data)

    def delete_report(self, report_id: int) -> None:
        deleted = self._repository.delete(report_id)
        if not deleted:
            raise ReportNotFoundError(f"Zgłoszenie o id {report_id} nie zostało znalezione.")