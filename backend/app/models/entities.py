from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Float, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

def utcnow(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="DEVELOPER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    technology: Mapped[str] = mapped_column(String(255), default="")
    repository_url: Mapped[str] = mapped_column(String(500), default="")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner: Mapped[User] = relationship(back_populates="projects")
    bugs: Mapped[list["Bug"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class ProjectUpload(Base):
    __tablename__ = "project_uploads"
    upload_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SourceChunk(Base):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint("upload_id", "source_name", "chunk_index"),
        Index("ix_source_chunks_owner_upload", "owner_id", "upload_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[str] = mapped_column(ForeignKey("project_uploads.upload_id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(512))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Bug(Base):
    __tablename__ = "bugs"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(220), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    reproduction_steps: Mapped[str] = mapped_column(Text, default="")
    expected_result: Mapped[str] = mapped_column(Text, default="")
    actual_result: Mapped[str] = mapped_column(Text, default="")
    module: Mapped[str] = mapped_column(String(120), default="General")
    environment: Mapped[str] = mapped_column(String(120), default="Development")
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project: Mapped[Project] = relationship(back_populates="bugs")
    analyses: Mapped[list["BugAnalysis"]] = relationship(back_populates="bug", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="bug", cascade="all, delete-orphan")
    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="bug", cascade="all, delete-orphan")

class BugAnalysis(Base):
    __tablename__ = "bug_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    bug_id: Mapped[int] = mapped_column(ForeignKey("bugs.id"), index=True)
    root_cause: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.4)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    affected_component: Mapped[str] = mapped_column(String(180), default="Unknown")
    possible_causes: Mapped[str] = mapped_column(Text, default="")
    suggested_fix: Mapped[str] = mapped_column(Text, default="")
    recommended_actions: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    bug: Mapped[Bug] = relationship(back_populates="analyses")

class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    bug_id: Mapped[int] = mapped_column(ForeignKey("bugs.id"), index=True)
    scenario: Mapped[str] = mapped_column(String(240))
    input_data: Mapped[str] = mapped_column(Text, default="")
    expected_result: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    test_type: Mapped[str] = mapped_column(String(30), default="FUNCTIONAL")
    executed: Mapped[bool] = mapped_column(default=False)
    bug: Mapped[Bug] = relationship(back_populates="test_cases")

class Attachment(Base):
    __tablename__ = "bug_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    bug_id: Mapped[int] = mapped_column(ForeignKey("bugs.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    bug: Mapped[Bug] = relationship(back_populates="attachments")
