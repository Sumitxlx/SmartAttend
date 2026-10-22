from pydantic import BaseModel


class RecognizedOut(BaseModel):
    student_id: int
    roll_number: str
    full_name: str
    status: str   # present or uncertain
    score: float
    written: bool  # False when a manual mark was kept


class RecognitionOut(BaseModel):
    session_id: int
    faces_found: int
    unrecognized_faces: int
    results: list[RecognizedOut]