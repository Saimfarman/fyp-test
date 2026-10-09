from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    plan: Mapped[str] = mapped_column(String(20), default="free")
    company_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_color: Mapped[str] = mapped_column(String(7), default="#ff7548")
    default_city: Mapped[str] = mapped_column(String(80), default="Karachi")
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), default="sales")
    workspace: Mapped[Workspace] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(20), default="sales")
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(96), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True)
    balance: Mapped[int] = mapped_column(Integer, default=100)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider_place_id: Mapped[str] = mapped_column(String(180))
    name: Mapped[str] = mapped_column(String(240))
    category: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(80))
    website_url: Mapped[str | None] = mapped_column(Text)
    website_status: Mapped[str] = mapped_column(String(20), default="NO_WEBSITE")
    severity: Mapped[str] = mapped_column(String(20), default="UNSCANNED")
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0)
    lead_value_tier: Mapped[str] = mapped_column(String(20), default="LOW")
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    category_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditIssue(Base):
    __tablename__ = "audit_issues"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    audit_id: Mapped[UUID] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    affected_url: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    fix_recommendation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)


class ServiceCatalogItem(Base):
    __tablename__ = "service_catalog"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    unit_price: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    active: Mapped[bool] = mapped_column(default=True)


class ServicePackage(Base):
    __tablename__ = "service_packages"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    service_ids: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(default=True)


class PitchDocument(Base):
    __tablename__ = "pitch_documents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10), default="both")
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    selected_service_ids: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PitchRecommendation(Base):
    __tablename__ = "pitch_recommendations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pitch_id: Mapped[UUID] = mapped_column(ForeignKey("pitch_documents.id", ondelete="CASCADE"), index=True)
    phase: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    source_issue_ids: Mapped[list] = mapped_column(JSONB, default=list)


class ShareLink(Base):
    __tablename__ = "share_links"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    pitch_id: Mapped[UUID] = mapped_column(ForeignKey("pitch_documents.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShareView(Base):
    __tablename__ = "share_views"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    share_link_id: Mapped[UUID] = mapped_column(ForeignKey("share_links.id", ondelete="CASCADE"), index=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Prototype(Base):
    __tablename__ = "prototypes"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(String(80))
    template_version: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PrototypeVersion(Base):
    __tablename__ = "prototype_versions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    prototype_id: Mapped[UUID] = mapped_column(ForeignKey("prototypes.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrototypeExport(Base):
    __tablename__ = "prototype_exports"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    prototype_id: Mapped[UUID] = mapped_column(ForeignKey("prototypes.id", ondelete="CASCADE"), index=True)
    framework: Mapped[str] = mapped_column(String(20), default="html")
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PipelineCard(Base):
    __tablename__ = "pipeline_cards"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), unique=True)
    stage: Mapped[str] = mapped_column(String(20), default="NEW")
    notes: Mapped[str] = mapped_column(Text, default="")
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PipelineActivity(Base):
    __tablename__ = "pipeline_activities"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[UUID] = mapped_column(ForeignKey("pipeline_cards.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80))
    event_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16))
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    secret_hash: Mapped[str] = mapped_column(String(128))
    events: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    webhook_id: Mapped[UUID] = mapped_column(ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("outbox_events.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    event_name: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FollowUp(Base):
    __tablename__ = "follow_ups"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OptOutRequest(Base):
    __tablename__ = "opt_out_requests"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"))
    business_name: Mapped[str] = mapped_column(String(240))
    website_url: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(320))
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
