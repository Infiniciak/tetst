from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{report_id}/department-info")
async def get_report_department(report_id: int, request: Request):
    eureka_client = request.app.state.eureka_client
    
    try:
        department_data = await eureka_client.do_service(
            app_name="DEPARTMENT-SERVICE",
            service_path=f"/departments/1",  
            return_type="json",             
            timeout=3,                       
        )
        return {
            "report_id": report_id,
            "department_info": department_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Nie udało się połączyć z DEPARTMENT-SERVICE: {str(e)}"
        )