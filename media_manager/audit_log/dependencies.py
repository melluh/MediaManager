from typing import Annotated

from fastapi import Depends

from media_manager.audit_log.repository import AuditLogRepository
from media_manager.audit_log.service import AuditLogService
from media_manager.database import DbSessionDependency


def get_audit_log_service(db_session: DbSessionDependency) -> AuditLogService:
    return AuditLogService(AuditLogRepository(db_session))


audit_log_service_dep = Annotated[AuditLogService, Depends(get_audit_log_service)]
