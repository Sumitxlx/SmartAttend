import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import Student, User, UserRole
from app.schemas.faces import EnrollmentOut, PhotoResultOut
from app.services import face_service
from app.services.audit import record_audit
from app.services.face_embedding import REQUIRED_PHOTOS, build_template

admin_only = require_roles(UserRole.admin)
router = APIRouter(prefix="/admin/students", tags=["admin faces"], dependencies=[Depends(admin_only)])

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png"}


@router.post("/{student_id}/face-enrollment", response_model=EnrollmentOut)
def enroll_face(
    student_id: int,
    photos: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if len(photos) != REQUIRED_PHOTOS:
        raise HTTPException(status_code=422, detail=f"Upload exactly {REQUIRED_PHOTOS} photos")

    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, upload in enumerate(photos):
            if upload.content_type not in ALLOWED_TYPES:
                raise HTTPException(status_code=422, detail=f"Photo {i + 1} must be a JPEG or PNG")
            data = upload.file.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise HTTPException(status_code=422, detail=f"Photo {i + 1} is larger than 5 MB")
            path = os.path.join(tmp, f"photo_{i}")
            with open(path, "wb") as f:
                f.write(data)
            paths.append(path)

        reports = face_service.evaluate_photos(paths)

    template, error = build_template(reports)
    photo_out = [
        PhotoResultOut(index=i + 1, accepted=r.accepted, reason=r.reason)
        for i, r in enumerate(reports)
    ]
    accepted = sum(1 for r in reports if r.accepted)

    if template is None:
        # Nothing is stored. A previous enrollment, if any, stays as it was.
        return EnrollmentOut(
            student_id=student.id,
            accepted_count=accepted,
            rejected_count=len(reports) - accepted,
            photos=photo_out,
            enrolled=False,
            message=error,
        )

    face_service.store_template(db, student, template)
    record_audit(db, admin, "face.enrolled", "student", student.id, f"accepted={accepted}")
    db.commit()
    return EnrollmentOut(
        student_id=student.id,
        accepted_count=accepted,
        rejected_count=len(reports) - accepted,
        photos=photo_out,
        enrolled=True,
        message="Face enrolled.",
    )