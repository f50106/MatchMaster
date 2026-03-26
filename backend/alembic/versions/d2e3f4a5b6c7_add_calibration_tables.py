"""Add calibration & continuous improvement tables.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-03-23

Tables added:
  - eval_benchmarks: cross-model evaluation storage
  - eval_comparisons: side-by-side comparison records
  - scoring_versions: pipeline config snapshots
  - calibration_feedback: human/expert accuracy feedback
  - authenticity_signals: AI resume detection pattern tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── eval_benchmarks ──
    op.create_table(
        "eval_benchmarks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("jd_id", sa.String(32), nullable=True, index=True),
        sa.Column("resume_id", sa.String(32), nullable=True, index=True),
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("source_version", sa.String(100), nullable=False, server_default=""),
        sa.Column("scoring_version_id", sa.String(32), nullable=True),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("tier", sa.String(5), nullable=False, server_default=""),
        sa.Column("dimension_scores", JSONB, nullable=True),
        sa.Column("analysis_text", sa.Text, nullable=False, server_default=""),
        sa.Column("strengths", JSONB, nullable=True),
        sa.Column("weaknesses", JSONB, nullable=True),
        sa.Column("interview_questions", JSONB, nullable=True),
        sa.Column("candidate_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("jd_title", sa.String(500), nullable=False, server_default=""),
        sa.Column("jd_file_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("resume_file_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("raw_data", JSONB, nullable=True),
        sa.Column("extra_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── eval_comparisons ──
    op.create_table(
        "eval_comparisons",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("benchmark_a_id", sa.String(32), nullable=False, index=True),
        sa.Column("benchmark_b_id", sa.String(32), nullable=False, index=True),
        sa.Column("comparison_text", sa.Text, nullable=False, server_default=""),
        sa.Column("key_differences", JSONB, nullable=True),
        sa.Column("preferred_source", sa.String(50), nullable=False, server_default=""),
        sa.Column("accuracy_notes", sa.Text, nullable=False, server_default=""),
        sa.Column("compared_by", sa.String(100), nullable=False, server_default=""),
        sa.Column("extra_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── scoring_versions ──
    op.create_table(
        "scoring_versions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("version_name", sa.String(100), nullable=False, unique=True),
        sa.Column("deterministic_weights", JSONB, nullable=True),
        sa.Column("llm_weights", JSONB, nullable=True),
        sa.Column("fusion_config", JSONB, nullable=True),
        sa.Column("prompt_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("changes_description", sa.Text, nullable=False, server_default=""),
        sa.Column("active_from", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("active_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── calibration_feedback ──
    op.create_table(
        "calibration_feedback",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("benchmark_id", sa.String(32), nullable=True, index=True),
        sa.Column("scoring_version_id", sa.String(32), nullable=True),
        sa.Column("human_score", sa.Float, nullable=True),
        sa.Column("human_tier", sa.String(5), nullable=False, server_default=""),
        sa.Column("accuracy_rating", sa.Integer, nullable=True),
        sa.Column("feedback_text", sa.Text, nullable=False, server_default=""),
        sa.Column("dimension_adjustments", JSONB, nullable=True),
        sa.Column("action_taken", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── authenticity_signals ──
    op.create_table(
        "authenticity_signals",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("resume_id", sa.String(32), nullable=True, index=True),
        sa.Column("benchmark_id", sa.String(32), nullable=True, index=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence", JSONB, nullable=True),
        sa.Column("verified_outcome", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("verification_notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("authenticity_signals")
    op.drop_table("calibration_feedback")
    op.drop_table("scoring_versions")
    op.drop_table("eval_comparisons")
    op.drop_table("eval_benchmarks")
