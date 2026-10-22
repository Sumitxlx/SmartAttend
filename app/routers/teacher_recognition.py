import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User, UserRole
from app.schemas.recognition import RecognitionOut
from app.services import recognition_service
from app.services.attendance_service import get_teacher_profile

teacher_only = require_roles(UserRole.teacher)
router = APIRouter(prefix="/teacher", tags=["teacher recognition"], dependencies=[Depends(teacher_only)])

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png"}


@router.post("/sessions/{session_id}/recognize", response_model=RecognitionOut)
def recognize(
    session_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(teacher_only),
):
    if photo.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="The frame must be a JPEG or PNG")
    data = photo.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=422, detail="The frame is larger than 5 MB")

    teacher = get_teacher_profile(db, user)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "frame")
        with open(path, "wb") as f:
            f.write(data)
        return recognition_service.recognize_frame(db, user, teacher, session_id, path)