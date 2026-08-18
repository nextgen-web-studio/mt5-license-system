from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.models import EaTemplate

router = APIRouter()

class EaTemplateSummary(BaseModel):
    id: int
    version_label: Optional[str]
    filename: Optional[str]
    file_size: int
    is_active: bool
    notes: Optional[str]
    uploaded_by: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

@router.get("/admin/list", response_model=List[EaTemplateSummary])
async def list_ea_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EaTemplate)
        .order_by(EaTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return templates

@router.post("/admin/upload", response_model=EaTemplateSummary)
async def upload_ea_template(
    file: UploadFile = File(...),
    version_label: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    activate: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith('.mq5'):
        raise HTTPException(status_code=400, detail="Only .mq5 files are allowed")

    content = await file.read()
    source_code = content.decode('utf-8')
    file_size = len(content)

    if activate:
        # Deactivate all others
        await db.execute(
            update(EaTemplate).values(is_active=False)
        )

    new_template = EaTemplate(
        version_label=version_label or file.filename,
        filename=file.filename,
        file_size=file_size,
        source_code=source_code,
        is_active=activate,
        notes=notes,
        uploaded_by=uploaded_by
    )
    
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    return new_template

@router.post("/admin/{template_id}/activate", response_model=dict)
async def activate_ea_template(template_id: int, db: AsyncSession = Depends(get_db)):
    # Verify template exists
    result = await db.execute(select(EaTemplate).filter(EaTemplate.id == template_id))
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Deactivate all
    await db.execute(update(EaTemplate).values(is_active=False))
    
    # Activate selected
    template.is_active = True
    await db.commit()
    
    return {"message": f"Template {template_id} activated successfully"}

@router.get("/current", response_model=dict)
async def get_current_ea_template(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EaTemplate).filter(EaTemplate.is_active == True)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="No active EA template found")
        
    return {
        "id": template.id,
        "version_label": template.version_label,
        "filename": template.filename,
        "source_code": template.source_code
    }
