"""Make campaign_rules.line_item_id index NON-unique (matches ORM model)

NOTE: This migration targets ctr_db (PostgreSQL), NOT scanner.db — same as 0003.
      ctr_db tables are managed by CrmBase.metadata.create_all(crm_engine) in
      main.py, which never alters an existing index. This file is kept as the
      human-readable record of the change; apply it against a live ctr_db with
      the standalone `fix_campaign_rules_index.py` script (idempotent), or via a
      ctr_db-pointed Alembic env.

WHY
---
`models.crm.CampaignRule` declares `line_item_id = Column(String, index=True)`
(non-unique). An earlier revision used a UNIQUE index, so the live database
still carries a unique `ix_campaign_rules_line_item_id`. Because the API stores
a blank Line Item ID as "", the second campaign-only rule violates that unique
index. Rebuilding it as a plain index removes the false collision while keeping
the lookup fast.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op

revision:      str              = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None

_INDEX = "ix_campaign_rules_line_item_id"
_TABLE = "campaign_rules"
_COLUMN = "line_item_id"


def upgrade() -> None:
    # Drop the stale UNIQUE index and recreate it as a non-unique index.
    op.drop_index(_INDEX, table_name=_TABLE, if_exists=True)
    op.create_index(_INDEX, _TABLE, [_COLUMN], unique=False, if_not_exists=True)


def downgrade() -> None:
    # Revert to the (problematic) unique index.
    op.drop_index(_INDEX, table_name=_TABLE, if_exists=True)
    op.create_index(_INDEX, _TABLE, [_COLUMN], unique=True, if_not_exists=True)
