from app.repositories.interfaces import ReportRepository
from app.schemas.report import Report, ReportCreate


class InMemoryReportRepository:
    def __init__(self) -> None:
        self._items: dict[int, Report] = {}
        self._counter = 1

    def all(self) -> list[Report]:
        return list(self._items.values())

    def get(self, report_id: int) -> Report | None:
        return self._items.get(report_id)

    def find_by_desc(self, description: str) -> Report | None:
        for report in self._items.values():
            if report.description == description:
                return report
        return None

    def add(self, data: ReportCreate) -> Report:
        report = Report(
            id=self._counter,
            department_id=data.department_id,
            reported_by=data.reported_by,
            report_type=data.report_type,
            description=data.description,
            status="unsolved",
        )
        self._items[self._counter] = report
        self._counter += 1
        return report

    def delete(self, report_id: int) -> bool:
        if report_id in self._items:
            del self._items[report_id]
            return True
        return False
