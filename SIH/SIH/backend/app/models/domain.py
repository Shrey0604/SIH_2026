from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Well(Base):
    __tablename__ = "wells"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    max_md_m: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    well_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL_OFFSET")


class Formation(Base):
    __tablename__ = "formations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)


class WellFormationInterval(Base):
    __tablename__ = "well_formation_intervals"
    __table_args__ = (UniqueConstraint("well_id", "formation_id"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    well_id: Mapped[str] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    formation_id: Mapped[str] = mapped_column(
        ForeignKey("formations.id"), nullable=False, index=True
    )
    top_md_m: Mapped[float] = mapped_column(Float, nullable=False)
    base_md_m: Mapped[float] = mapped_column(Float, nullable=False)
    top_tvd_m: Mapped[float | None] = mapped_column(Float)
    base_tvd_m: Mapped[float | None] = mapped_column(Float)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    well_id: Mapped[str | None] = mapped_column(ForeignKey("wells.id"), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    document_type: Mapped[str] = mapped_column(String(24), nullable=False)
    filename: Mapped[str] = mapped_column(String(180), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(300), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "page_number", "chunk_index"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str | None] = mapped_column(Text)
    embedding_provider: Mapped[str | None] = mapped_column(String(32))
    embedding_model: Mapped[str | None] = mapped_column(String(96))
    embedding_dimension: Mapped[int | None] = mapped_column(Integer)


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    recovered_text: Mapped[str | None] = mapped_column(Text)
    text_quality: Mapped[float] = mapped_column(Float, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(24), nullable=False)
    width_pt: Mapped[float] = mapped_column(Float, nullable=False)
    height_pt: Mapped[float] = mapped_column(Float, nullable=False)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    stages_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    cached_verified_extraction: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    well_id: Mapped[str] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    formation_id: Mapped[str | None] = mapped_column(ForeignKey("formations.id"), index=True)
    hazard_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    start_md_m: Mapped[float] = mapped_column(Float, nullable=False)
    end_md_m: Mapped[float | None] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    historical_response: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EventEvidence(Base):
    __tablename__ = "event_evidence"
    __table_args__ = (UniqueConstraint("event_id", "document_id", "page_number"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    bbox_json: Mapped[str | None] = mapped_column(Text)


class TelemetrySample(Base):
    __tablename__ = "telemetry_samples"
    __table_args__ = (UniqueConstraint("well_id", "seq"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    well_id: Mapped[str] = mapped_column(ForeignKey("wells.id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_offset_s: Mapped[int] = mapped_column(Integer, nullable=False)
    md_m: Mapped[float] = mapped_column(Float, nullable=False)
    tvd_m: Mapped[float | None] = mapped_column(Float)
    rop_mph: Mapped[float] = mapped_column(Float, nullable=False)
    wob_kn: Mapped[float] = mapped_column(Float, nullable=False)
    rpm: Mapped[float] = mapped_column(Float, nullable=False)
    torque_knm: Mapped[float] = mapped_column(Float, nullable=False)
    spp_bar: Mapped[float] = mapped_column(Float, nullable=False)
    flow_in_lpm: Mapped[float] = mapped_column(Float, nullable=False)
    flow_out_lpm: Mapped[float] = mapped_column(Float, nullable=False)
    pit_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    mud_weight_sg: Mapped[float] = mapped_column(Float, nullable=False)
    gas_units: Mapped[float] = mapped_column(Float, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    active_well_id: Mapped[str] = mapped_column(ForeignKey("wells.id"), nullable=False)
    hazard_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    current_md_m: Mapped[float] = mapped_column(Float, nullable=False)
    projected_hazard_md_m: Mapped[float] = mapped_column(Float, nullable=False)
    lookahead_m: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    analog_support: Mapped[float] = mapped_column(Float, nullable=False)
    recurrence_score: Mapped[float] = mapped_column(Float, nullable=False)
    telemetry_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
