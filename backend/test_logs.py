import asyncio
import sys
import os

from app.db.session import AsyncSessionLocal
from app.db.models import AuditLog
from app.db.schemas import AuditLogResponse
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(AuditLog).limit(10))
        logs = res.scalars().all()
        for log in logs:
            try:
                print(f"Log ID: {log.id}")
                resp = AuditLogResponse.model_validate(log)
            except Exception as e:
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
