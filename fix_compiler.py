with open("backend/app/api/v1/endpoints/admin.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """@router.get("/compiler_jobs")
async def get_compiler_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompileJob).order_by(CompileJob.created_at.desc()))
    jobs = result.scalars().all()
    return jobs"""

replacement = """@router.get("/compiler_jobs")
async def get_compiler_jobs(db: AsyncSession = Depends(get_db)):
    from app.models import License
    query = (
        select(CompileJob, License.order_id)
        .outerjoin(License, CompileJob.license_id == License.id)
        .order_by(CompileJob.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    jobs = []
    for job, order_id in rows:
        job_dict = {c.name: getattr(job, c.name) for c in job.__table__.columns}
        job_dict["order_id"] = order_id
        jobs.append(job_dict)
    return jobs"""

content = content.replace(target, replacement)

with open("backend/app/api/v1/endpoints/admin.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated compiler_jobs endpoint")
