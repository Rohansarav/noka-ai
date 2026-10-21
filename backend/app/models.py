"""Public evidence graph and isolated private profiles; original resumes are never stored."""
from datetime import date, datetime, timezone
from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


class Base(DeclarativeBase):
    pass


class SchemaSmoke(Base):
    """Retain the Phase 0 migration table in metadata so autogeneration never drops it."""
    __tablename__ = "schema_smoke"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text)
    file_url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(160))
    publication_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime)
    version: Mapped[str] = mapped_column(String(120))
    sha256: Mapped[str] = mapped_column(String(64))
    license: Mapped[str] = mapped_column(Text)
    license_url: Mapped[str] = mapped_column(Text)
    geography: Mapped[str] = mapped_column(String(80))
    granularity: Mapped[str] = mapped_column(String(80))
    notes: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("dataset", "sha256"),)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    occupation_code: Mapped[str] = mapped_column(String(20), unique=True)
    country: Mapped[str] = mapped_column(String(2))
    sector: Mapped[str | None] = mapped_column(String(120), index=True)
    evidence_status: Mapped[str] = mapped_column(String(50))
    crosswalk_rationale: Mapped[str] = mapped_column(Text)
    curation_status: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(160), unique=True)
    aliases: Mapped[list] = mapped_column(JSON)
    category: Mapped[str] = mapped_column(String(80))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class RoleSkill(Base):
    __tablename__ = "role_skills"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    required_importance: Mapped[float] = mapped_column(Float)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    __table_args__ = (CheckConstraint("required_importance >= 1 AND required_importance <= 5"),)


class RoleTechnology(Base):
    """Published software associations have no invented importance or proficiency threshold."""
    __tablename__ = 'role_technologies'
    role_id: Mapped[str] = mapped_column(ForeignKey('roles.id'), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey('skills.id'), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    classifications: Mapped[list] = mapped_column(JSON)
    hot_technology: Mapped[bool] = mapped_column(Boolean)
    in_demand: Mapped[bool] = mapped_column(Boolean)


class DemandObservation(Base):
    __tablename__ = "job_demand_observations"
    country: Mapped[str] = mapped_column(String(2), primary_key=True)
    sector: Mapped[str] = mapped_column(String(120), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    adjusted_flag: Mapped[bool] = mapped_column(Boolean, primary_key=True)
    indexed_value: Mapped[float] = mapped_column(Float)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    __table_args__ = (CheckConstraint("indexed_value >= 0"), Index("ix_demand_sector_date", "sector", "date"))


class SDG(Base):
    __tablename__ = "sdgs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class SDGTarget(Base):
    __tablename__ = "sdg_targets"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("sdgs.id"))
    description: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class SDGLink(Base):
    __tablename__ = "sdg_links"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("sdg_targets.id"))
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"))
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skills.id"))
    rationale: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    curation_status: Mapped[str] = mapped_column(String(50))
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    __table_args__ = (CheckConstraint("(role_id IS NOT NULL AND skill_id IS NULL) OR (role_id IS NULL AND skill_id IS NOT NULL)"),)


class StructuralDirection(Base):
    __tablename__ = "structural_directions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject: Mapped[str] = mapped_column(String(160))
    direction: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    horizon: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    curation_status: Mapped[str] = mapped_column(String(50))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(20))
    row_count: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text)


class PrivateSession(Base):
    __tablename__ = "private_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_hash: Mapped[str] = mapped_column(ForeignKey("private_sessions.token_hash"), unique=True)
    country: Mapped[str] = mapped_column(String(2), default="MY")
    interests: Mapped[list] = mapped_column(JSON, default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ProfileSkill(Base):
    __tablename__ = "profile_skills"
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[str] = mapped_column(String(16))
    years: Mapped[float | None] = mapped_column(Float)


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_hash: Mapped[str] = mapped_column(ForeignKey("private_sessions.token_hash", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    deadline: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    model: Mapped[str] = mapped_column(String(100))
    tool_count: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(40))
    result: Mapped[dict | None] = mapped_column(JSON)


class AgentEvent(Base):
    __tablename__ = "agent_events"
    execution_id: Mapped[str] = mapped_column(ForeignKey("agent_executions.id", ondelete="CASCADE"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    agent: Mapped[str] = mapped_column(String(24))
    type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24))
    message: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON)


class FutureWorkspace(Base):
    """One private, revisioned workspace; deletion follows profile ownership."""
    __tablename__ = "future_workspaces"
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    scenario: Mapped[str] = mapped_column(String(32), default="collaboration")
    role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"))
    weekly_hours: Mapped[int] = mapped_column(Integer, default=6)
    progress: Mapped[dict] = mapped_column(JSON, default=dict)
    conversation: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class IntelligenceRecord(Base):
    """Reusable public research, outlook and run records, never private profile data."""
    __tablename__ = "intelligence_records"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
