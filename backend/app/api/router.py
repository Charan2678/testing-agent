from fastapi import APIRouter
from backend.app.api.routes.applications import router as applications_router
from backend.app.api.routes.explorations import router as explorations_router
from backend.app.api.routes.pages import router as pages_router
from backend.app.api.routes.analysis import router as analysis_router
from backend.app.api.routes.executions import router as executions_router
from backend.app.api.routes.bugs import router as bugs_router
from backend.app.api.routes.database_qa import router as database_qa_router

api_router = APIRouter()

api_router.include_router(applications_router)
api_router.include_router(explorations_router)
api_router.include_router(pages_router)
api_router.include_router(analysis_router)
api_router.include_router(executions_router)
api_router.include_router(bugs_router)
api_router.include_router(database_qa_router)



