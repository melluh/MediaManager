from typing import Annotated

from fastapi import Depends

from media_manager.admin.service import AdminService
from media_manager.movies.dependencies import movie_repository_dep
from media_manager.tv.dependencies import tv_repository_dep


def get_admin_service(
    movie_repository: movie_repository_dep,
    tv_repository: tv_repository_dep,
) -> AdminService:
    return AdminService(movie_repository=movie_repository, tv_repository=tv_repository)


admin_service_dep = Annotated[AdminService, Depends(get_admin_service)]
