from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from squad_os.api.schemas import InstalledPackageDTO, StorePackageDTO
from squad_os.api.services.store_service import store_service

router = APIRouter(prefix="/store", tags=["Agent Store"])


@router.get("/packages", response_model=list[StorePackageDTO])
async def list_packages(search: Optional[str] = Query(None)):
    return await store_service.list_packages(search=search)


@router.get("/packages/{package_id}", response_model=StorePackageDTO)
async def get_package(package_id: str):
    pkg = await store_service.get_package(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    return pkg


@router.get("/installed", response_model=list[InstalledPackageDTO])
async def list_installed():
    return await store_service.list_installed()
