"""
API routes for groups (CRUD).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Group
from app.schemas.group_student import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupWithStudentsResponse,
)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("", response_model=List[GroupResponse])
def list_groups(db: Session = Depends(get_db)):
    """List all groups."""
    return db.query(Group).order_by(Group.name).all()


@router.get("/{group_id}", response_model=GroupWithStudentsResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    """Get a group by ID with its students."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    from app.schemas.group_student import StudentResponse
    students_data = [
        StudentResponse(
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
            group_name=group.name,
        )
        for s in group.students
    ]
    return GroupWithStudentsResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        goal=group.goal,
        created_at=group.created_at,
        updated_at=group.updated_at,
        students=students_data,
    )


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    """Create a new group."""
    group = Group(
        name=payload.name,
        description=payload.description,
        goal=payload.goal,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(group_id: int, payload: GroupUpdate, db: Session = Depends(get_db)):
    """Update a group."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if payload.name is not None:
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    if payload.goal is not None:
        group.goal = payload.goal
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """Delete a group. Students in the group will have group_id set to null."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for s in group.students:
        s.group_id = None
    db.delete(group)
    db.commit()
    return None
