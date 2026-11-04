from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    department_id: int = Field(gt=0)
    reported_by: str = Field(min_length=1, strip_whitespace=True)
    report_type: str = Field(min_length=1, strip_whitespace=True)
    description: str = Field(min_length=1, strip_whitespace=True)


class Report(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    reported_by: str
    report_type: str
    description: str
    status: str = "unsolved"
