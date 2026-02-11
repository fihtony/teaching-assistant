"""
Pydantic schemas for Group and Student API.
"""

from typing import Optional, List

from pydantic import BaseModel, Field


class GroupBase(BaseModel):
    """Base group schema."""

    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    goal: Optional[str] = None


class GroupCreate(GroupBase):
    """Schema for creating a group."""

    pass


class GroupUpdate(BaseModel):
    """Schema for updating a group."""

    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    goal: Optional[str] = None


class GroupResponse(GroupBase):
    """Group response schema."""

    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class StudentBase(BaseModel):
    """Base student schema."""

    name: str = Field(..., min_length=1)
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = Field(None, pattern="^(boy|girl)$")
    vocabulary: Optional[str] = None
    grade: Optional[str] = None
    group_id: Optional[int] = None
    additional_info: Optional[str] = None


class StudentCreate(StudentBase):
    """Schema for creating a student."""

    pass


class StudentUpdate(BaseModel):
    """Schema for updating a student."""

    name: Optional[str] = Field(None, min_length=1)
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = Field(None, pattern="^(boy|girl)$")
    vocabulary: Optional[str] = None
    grade: Optional[str] = None
    group_id: Optional[int] = None
    additional_info: Optional[str] = None


class StudentResponse(StudentBase):
    """Student response schema."""

    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    group_name: Optional[str] = None

    class Config:
        from_attributes = True


class GroupWithStudentsResponse(GroupResponse):
    """Group with list of students."""

    students: List[StudentResponse] = []
