"""
recalculate_marks.py — Recalculate marks for batches that have marking config
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import async_session
from app.db.models import Batch, Submission, RiskScore
from app.engine.marking_calculator import calculate_marks


async def recalculate_batch_marks(batch_id: str = None):
    """Recalculate marks for a specific batch or all batches with marking config."""
    async with async_session() as db:
        # Get batches with marking config
        if batch_id:
            query = select(Batch).where(
                Batch.id == batch_id,
                Batch.total_marks.isnot(None),
                Batch.marking_config.isnot(None)
            )
        else:
            query = select(Batch).where(
                Batch.total_marks.isnot(None),
                Batch.marking_config.isnot(None)
            )
        
        result = await db.execute(query)
        batches = result.scalars().all()
        
        if not batches:
            print("No batches found with marking configuration.")
            return
        
        print(f"Found {len(batches)} batch(es) with marking configuration.")
        
        for batch in batches:
            print(f"\nProcessing batch: {batch.name} ({batch.id})")
            print(f"  Total marks: {batch.total_marks}")
            
            # Get all submissions with risk scores
            submissions_result = await db.execute(
                select(Submission, RiskScore)
                .join(RiskScore, RiskScore.submission_id == Submission.id)
                .where(Submission.batch_id == batch.id)
            )
            
            submissions = submissions_result.all()
            print(f"  Found {len(submissions)} submissions")
            
            updated_count = 0
            for sub, rs in submissions:
                # Calculate marks
                marks_obtained, marks_breakdown = calculate_marks(
                    total_marks=batch.total_marks,
                    marking_config=batch.marking_config,
                    ai_prob=rs.ai_prob,
                    text_sim_max=rs.text_sim_max,
                    code_sim_max=rs.code_sim_max,
                    weighted_score=rs.weighted_score,
                )
                
                # Update submission
                sub.marks_obtained = marks_obtained
                sub.marks_breakdown = marks_breakdown
                updated_count += 1
            
            await db.commit()
            print(f"  ✅ Updated {updated_count} submissions with marks")
        
        print(f"\n✅ Recalculation complete!")


if __name__ == "__main__":
    batch_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if batch_id:
        print(f"Recalculating marks for batch: {batch_id}")
    else:
        print("Recalculating marks for all batches with marking config")
    
    asyncio.run(recalculate_batch_marks(batch_id))
