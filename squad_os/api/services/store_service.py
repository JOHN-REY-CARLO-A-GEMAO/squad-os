from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import aiosqlite

from squad_os.api.schemas import InstalledPackageDTO, StorePackageDTO
from squad_os.database.session import DB_PATH


class StoreService:
    async def list_packages(self, search: Optional[str] = None) -> List[StorePackageDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            installed_ids = set()
            icursor = await db.execute("SELECT package_id FROM installed_packages WHERE status = 'ACTIVE'")
            for r in await icursor.fetchall():
                installed_ids.add(r["package_id"])
            if search:
                cursor = await db.execute(
                    "SELECT * FROM store_packages WHERE name LIKE ? OR description LIKE ? ORDER BY name ASC",
                    (f"%{search}%", f"%{search}%")
                )
            else:
                cursor = await db.execute("SELECT * FROM store_packages ORDER BY name ASC")
            rows = await cursor.fetchall()
            return [StorePackageDTO(
                id=r["id"], name=r["name"], version=r["version"],
                author=r.get("author"), description=r.get("description"),
                tags=r.get("tags"), install_count=r.get("install_count", 0),
                rating=r.get("rating", 0.0),
                installed=r["id"] in installed_ids,
            ) for r in rows]

    async def get_package(self, package_id: str) -> Optional[StorePackageDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM store_packages WHERE id = ?", (package_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            icursor = await db.execute(
                "SELECT COUNT(*) FROM installed_packages WHERE package_id = ? AND status = 'ACTIVE'",
                (package_id,)
            )
            installed_count = (await icursor.fetchone())[0]
            return StorePackageDTO(
                id=row["id"], name=row["name"], version=row["version"],
                author=row.get("author"), description=row.get("description"),
                tags=row.get("tags"), install_count=row.get("install_count", 0),
                rating=row.get("rating", 0.0), installed=installed_count > 0,
            )

    async def list_installed(self) -> List[InstalledPackageDTO]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM installed_packages ORDER BY installed_at DESC"
            )
            rows = await cursor.fetchall()
            return [InstalledPackageDTO(
                id=r["id"], package_id=r["package_id"], version=r["version"],
                install_path=r["install_path"], status=r["status"],
                installed_at=r.get("installed_at"),
            ) for r in rows]


store_service = StoreService()
