from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.models_db import ReportRow
from app.schemas.report import Report, ReportCreate


class ReportRepositorySql:

    def __init__(self, sessions: sessionmaker) -> None:
        self.sessions = sessions

    def all(self) -> list[Report]:
        with self.sessions() as db:
            rows = db.scalars(select(ReportRow)).all()
            return [Report.model_validate(row) for row in rows]

    def get(self, report_id: int) -> Report | None:
        with self.sessions() as db:
            row = db.get(ReportRow, report_id)
            if row is None:
                return None
            return Report.model_validate(row)

    def find_by_desc(self, description: str) -> Report | None:
        with self.sessions() as db:
            stmt = select(ReportRow).where(ReportRow.description == description)
            row = db.scalars(stmt).first()
            if row is None:
                return None
            return Report.model_validate(row)

    def add(self, data: ReportCreate) -> Report:
        try:
            with self.sessions.begin() as db:
                row = ReportRow(
                    department_id=data.department_id,
                    reported_by=data.reported_by,
                    report_type=data.report_type,
                    description=data.description,
                    status="unsolved",
                )
                db.add(row)
                db.flush()
                result = Report.model_validate(row)
            return result
        except IntegrityError as exc:
            raise ValueError("Zgłoszenie z takim opisem już istnieje.") from exc

    def delete(self, report_id: int) -> bool:
        with self.sessions.begin() as db:
            row = db.get(ReportRow, report_id)
            if row is None:
                return False
            db.delete(row)
            return True