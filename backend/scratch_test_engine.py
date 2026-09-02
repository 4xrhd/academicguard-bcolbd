import asyncio
import uuid
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.engine.pdf_processor import process_batch

async def test():
    # Use the latest batch ID from our previous query
    batch_id = "f5060c3e-9220-486b-b1f4-f849f10c128b"
    print(f"Testing process_batch for {batch_id}...")
    try:
        await process_batch(batch_id)
        print("Success!")
    except Exception as e:
        print(f"Failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
