"""
API routes for students (CRUD and list by group).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Student, Group
from app.schemas.group_student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
)

router = APIRouter(prefix="/students", tags=["Students"])


def _student_to_response(s: Student, db: Session) -> StudentResponse:
    group_name = None
    if s.group_id:
        g = db.query(Group).filter(Group.id == s.group_id).first()
        group_name = g.name if g else None
    return StudentResponse(
        id=s.id,
        name=s.name,
        age=s.age,
        gender=s.gender.value if s.gender else None,
        vocabulary=s.vocabulary,
        grade=s.grade,
        group_id=s.group_id,
        additional_info=s.additional_info,
        created_at=s.created_at,
        updated_at=s.updated_at,
        group_name=group_name,
    )


@router.get("", response_model=List[StudentResponse])
def list_students(
    group_id: Optional[int] = Query(None, description="Filter by group ID"),
    db: Session = Depends(get_db),
):
    """List all students, optionally filtered by group."""
    q = db.query(Student).order_by(Student.name)
    if group_id is not None:
        q = q.filter(Student.group_id == group_id)
    return [_student_to_response(s, db) for s in q.all()]


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Get a student by ID."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _student_to_response(student, db)


@router.post("", response_model=StudentResponse, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    """Create a new student."""
    from app.models import Gender
    gender = None
    if payload.gender:
        gender = Gender(payload.gender)
    student = Student(
        name=payload.name,
        age=payload.age,
        gender=gender,
        vocabulary=payload.vocabulary,
        grade=payload.grade,
        group_id=payload.group_id,
        additional_info=payload.additional_info,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return _student_to_response(student, db)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)):
    """Update a student."""
    from app.models import Gender
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if payload.name is not None:
        student.name = payload.name
    if payload.age is not None:
        student.age = payload.age
    if payload.gender is not None:
        student.gender = Gender(payload.gender) if payload.gender else None
    if payload.vocabulary is not None:
        student.vocabulary = payload.vocabulary
    if payload.grade is not None:
        student.grade = payload.grade
    if payload.group_id is not None:
        student.group_id = payload.group_id
    if payload.additional_info is not None:
        student.additional_info = payload.additional_info
    db.commit()
    db.refresh(student)
    return _student_to_response(student, db)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    """Delete a student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return None
