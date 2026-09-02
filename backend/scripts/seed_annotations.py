import asyncio
import random
import uuid
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.db.models import Submission, Annotation, User

async def seed_annotations():
    print("🌱 Starting Annotation Seeder...")
    async with AsyncSessionLocal() as session:
        # 1. Get a user (the one provided by the user)
        res = await session.execute(select(User).where(User.email == "azhar_uddin1120@uits.edu.bd"))
        user = res.scalars().first()
        if not user:
            print("❌ User not found. Please create the user first.")
            return

        # 2. Get submissions that don't have annotations yet
        res = await session.execute(
            select(Submission)
            .where(~Submission.id.in_(select(Annotation.submission_id)))
            .limit(30)
        )
        submissions = res.scalars().all()

        if not submissions:
            print("⚠️ No unannotated submissions found. Seeding skipped.")
            # Maybe they are already annotated?
            return

        print(f"📝 Found {len(submissions)} submissions to annotate.")

        labels = ["human", "ai_generated"]
        
        count = 0
        for sub in submissions:
            # Alternate labels to ensure class balance
            label = labels[count % 2]
            
            annotation = Annotation(
                submission_id=sub.id,
                user_id=user.id,
                label=label,
                confidence=random.uniform(0.85, 1.0),
                notes=f"Auto-seeded {label} label for testing."
            )
            session.add(annotation)
            count += 1

        await session.commit()
        print(f"✅ Successfully seeded {count} annotations!")
        
        # Check readiness
        print("\n--- Training Readiness Check ---")
        res = await session.execute(select(func.count(Annotation.id)))
        total = res.scalar()
        
        res = await session.execute(
            select(Annotation.label, func.count(Annotation.id))
            .group_by(Annotation.label)
        )
        dist = dict(res.all())
        
        print(f"Total Annotations: {total}")
        for l, c in dist.items():
            print(f" - {l}: {c}")
            
        ready = total >= 20 and dist.get('human', 0) >= 5 and dist.get('ai_generated', 0) >= 5
        print(f"Ready to Train: {'✅ YES' if ready else '❌ NO (need more)'}")

if __name__ == "__main__":
    asyncio.run(seed_annotations())
