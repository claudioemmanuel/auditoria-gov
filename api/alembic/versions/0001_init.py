"""Initial schema — core tables

Revision ID: 0001
Revises:
Create Date: 2026-03-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # raw_run
    op.create_table(
        "raw_run",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("connector", sa.String(100), nullable=False),
        sa.Column("job", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("cursor_start", sa.String(255)),
        sa.Column("cursor_end", sa.String(255)),
        sa.Column("items_fetched", sa.Integer, server_default="0"),
        sa.Column("items_normalized", sa.Integer, server_default="0"),
        sa.Column("errors", JSONB),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # raw_source
    op.create_table(
        "raw_source",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("raw_run.id"), nullable=False),
        sa.Column("connector", sa.String(100), nullable=False),
        sa.Column("job", sa.String(100), nullable=False),
        sa.Column("raw_id", sa.String(255), nullable=False),
        sa.Column("raw_data", JSONB, nullable=False),
        sa.Column("normalized", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # entity
    op.create_table(
        "entity",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("name_normalized", sa.String(500), nullable=False),
        sa.Column("identifiers", JSONB, server_default="{}"),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("cluster_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_entity_identifiers_cnpj",
        "entity",
        [sa.text("(identifiers->>'cnpj')")],
    )

    # entity_alias
    op.create_table(
        "entity_alias",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("alias_type", sa.String(50), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # event
    op.create_table(
        "event",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("subtype", sa.String(100)),
        sa.Column("description", sa.Text),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("source_connector", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("value_brl", sa.Float),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_event_type_occurred_at", "event", ["type", "occurred_at"])

    # event_participant
    op.create_table(
        "event_participant",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("event.id"), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_event_participant_entity_role", "event_participant", ["entity_id", "role"])

    # graph_node
    op.create_table(
        "graph_node",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entity.id"), unique=True, nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # graph_edge
    op.create_table(
        "graph_edge",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("from_node_id", UUID(as_uuid=True), sa.ForeignKey("graph_node.id"), nullable=False),
        sa.Column("to_node_id", UUID(as_uuid=True), sa.ForeignKey("graph_node.id"), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("weight", sa.Float, server_default="1.0"),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_graph_edge_from", "graph_edge", ["from_node_id"])
    op.create_index("ix_graph_edge_to", "graph_edge", ["to_node_id"])
    op.create_index("ix_graph_edge_type", "graph_edge", ["type"])

    # text_corpus
    op.create_table(
        "text_corpus",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # text_embedding (pgvector)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "text_embedding",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("corpus_id", UUID(as_uuid=True), sa.ForeignKey("text_corpus.id"), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Vector column and HNSW index via raw SQL — pgvector types not supported by Alembic
    op.execute("ALTER TABLE text_embedding ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX ix_text_embedding_hnsw ON text_embedding "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    # typology
    op.create_table(
        "typology",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("required_domains", JSONB, server_default="[]"),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed typologies T01-T10
    op.execute("""
        INSERT INTO typology (id, code, name, description, required_domains) VALUES
        (gen_random_uuid(), 'T01', 'Concentração em Fornecedor', 'HHI e concentração top1%/top3% vs baseline', '["licitacao"]'),
        (gen_random_uuid(), 'T02', 'Baixa Competição', 'Participantes abaixo do p10 do baseline', '["licitacao"]'),
        (gen_random_uuid(), 'T03', 'Fracionamento de Despesa', 'Sequências temporais perto do limiar de dispensa', '["despesa", "licitacao"]'),
        (gen_random_uuid(), 'T04', 'Aditivo Outlier', 'Percentual de aditivos acima do p95 da distribuição', '["contrato"]'),
        (gen_random_uuid(), 'T05', 'Preço Outlier', 'Preço unitário acima do p95/p99 do baseline', '["licitacao", "contrato"]'),
        (gen_random_uuid(), 'T06', 'Proxy de Empresa de Fachada', 'Volume rápido + objeto incompatível + rede suspeita', '["licitacao", "empresa"]'),
        (gen_random_uuid(), 'T07', 'Rede de Cartel', 'Alternância de vencedores + co-participação + comunidades', '["licitacao"]'),
        (gen_random_uuid(), 'T08', 'Sanção x Contrato', 'Sobreposição temporal sanção vs contrato ativo', '["sancao", "contrato"]'),
        (gen_random_uuid(), 'T09', 'Proxy de Folha Fantasma', 'Itens anômalos de remuneração + checklist', '["remuneracao"]'),
        (gen_random_uuid(), 'T10', 'Terceirização Paralela', 'Terceirização longa + concentração + aditivos recorrentes', '["contrato", "remuneracao"]')
    """)

    # risk_signal
    op.create_table(
        "risk_signal",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("typology_id", UUID(as_uuid=True), sa.ForeignKey("typology.id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("explanation_md", sa.Text),
        sa.Column("factors", JSONB, server_default="{}"),
        sa.Column("evidence_refs", JSONB, server_default="[]"),
        sa.Column("entity_ids", JSONB, server_default="[]"),
        sa.Column("event_ids", JSONB, server_default="[]"),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_risk_signal_typology_severity",
        "risk_signal",
        ["typology_id", "severity", "created_at"],
    )

    # case
    op.create_table(
        "case",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # case_item
    op.create_table(
        "case_item",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("case.id"), nullable=False),
        sa.Column("signal_id", UUID(as_uuid=True), sa.ForeignKey("risk_signal.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("case_item")
    op.drop_table("case")
    op.drop_table("risk_signal")
    op.drop_table("typology")
    op.drop_index("ix_text_embedding_hnsw")
    op.drop_table("text_embedding")
    op.drop_table("text_corpus")
    op.drop_table("graph_edge")
    op.drop_table("graph_node")
    op.drop_table("event_participant")
    op.drop_table("event")
    op.drop_table("entity_alias")
    op.drop_index("ix_entity_identifiers_cnpj")
    op.drop_table("entity")
    op.drop_table("raw_source")
    op.drop_table("raw_run")
