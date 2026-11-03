"""add notes, note types and tags; generic scheduler state

Card content moves from cards into notes (Anki's model): every existing card becomes a note
of a new "Basic" note type, with its front and back as the note's two fields.

Also replaces the scheduler-specific review_states.step with a generic scheduler name and a
JSON scheduler_state, allows the 'relearning' status, records answer durations, and renames
reviews.scheduler_version to reviews.scheduler.

Revision ID: 1a905d6c55e4
Revises: d2be88f1b224
Create Date: 2026-11-03 22:36:26.157594

"""
import html
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision: str = '1a905d6c55e4'
down_revision: Union[str, Sequence[str], None] = 'd2be88f1b224'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BASIC_FRONT = "{{Front}}"
BASIC_BACK = "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"


def upgrade() -> None:
    """Upgrade schema."""
    # 1. New tables
    note_types = op.create_table('note_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(length=200), nullable=False),
    sa.Column('fields', sa.Unicode(), nullable=False),
    sa.Column('anki_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', mssql.DATETIME2(), nullable=False),
    sa.CheckConstraint('ISJSON(fields) = 1', name=op.f('ck_note_types_fields_json')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_note_types')),
    sa.UniqueConstraint('name', name=op.f('uq_note_types_name'))
    )
    op.create_index('ix_note_types_anki_id', 'note_types', ['anki_id'], unique=True, mssql_where=sa.text('anki_id IS NOT NULL'))
    op.create_table('tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tags')),
    sa.UniqueConstraint('name', name=op.f('uq_tags_name'))
    )
    templates = op.create_table('note_type_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('note_type_id', sa.Integer(), nullable=False),
    sa.Column('ord', sa.SmallInteger(), nullable=False),
    sa.Column('name', sa.Unicode(length=200), nullable=False),
    sa.Column('front_template', sa.Unicode(), nullable=False),
    sa.Column('back_template', sa.Unicode(), nullable=False),
    sa.ForeignKeyConstraint(['note_type_id'], ['note_types.id'], name=op.f('fk_note_type_templates_note_type_id_note_types'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_note_type_templates')),
    sa.UniqueConstraint('note_type_id', 'ord', name=op.f('uq_note_type_templates_note_type_id_ord'))
    )
    notes = op.create_table('notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('note_type_id', sa.Integer(), nullable=False),
    sa.Column('fields', sa.Unicode(), nullable=False),
    sa.Column('kind', sa.Unicode(length=20), nullable=False),
    sa.Column('priority', sa.SmallInteger(), nullable=False),
    sa.Column('anki_guid', sa.Unicode(length=64), nullable=True),
    sa.Column('created_at', mssql.DATETIME2(), nullable=False),
    sa.Column('updated_at', mssql.DATETIME2(), nullable=False),
    sa.CheckConstraint("kind IN ('basic', 'definition', 'theorem', 'proof', 'application', 'vocab')", name=op.f('ck_notes_kind')),
    sa.CheckConstraint('ISJSON(fields) = 1', name=op.f('ck_notes_fields_json')),
    sa.CheckConstraint('priority BETWEEN 1 AND 3', name=op.f('ck_notes_priority')),
    sa.ForeignKeyConstraint(['note_type_id'], ['note_types.id'], name=op.f('fk_notes_note_type_id_note_types')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notes'))
    )
    op.create_index('ix_notes_anki_guid', 'notes', ['anki_guid'], unique=True, mssql_where=sa.text('anki_guid IS NOT NULL'))
    op.create_index(op.f('ix_notes_note_type_id'), 'notes', ['note_type_id'], unique=False)
    op.create_table('note_tags',
    sa.Column('note_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['note_id'], ['notes.id'], name=op.f('fk_note_tags_note_id_notes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], name=op.f('fk_note_tags_tag_id_tags'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('note_id', 'tag_id', name=op.f('pk_note_tags'))
    )
    op.create_index(op.f('ix_note_tags_tag_id'), 'note_tags', ['tag_id'], unique=False)

    # 2. A "Basic" note type (Front -> Back) for the existing cards and for new simple cards
    bind = op.get_bind()
    basic_id = bind.execute(
        note_types.insert()
        .values(name="Basic", fields=json.dumps(["Front", "Back"]), created_at=sa.func.sysutcdatetime())
        .returning(note_types.c.id)
    ).scalar_one()
    bind.execute(templates.insert().values(
        note_type_id=basic_id, ord=0, name="Card 1", front_template=BASIC_FRONT, back_template=BASIC_BACK
    ))

    # 3. Move each card's content into a new note (old text was plain/Markdown, so escape it as HTML)
    op.add_column('cards', sa.Column('note_id', sa.Integer(), nullable=True))
    op.add_column('cards', sa.Column('template_ord', sa.SmallInteger(), nullable=False, server_default='0'))
    op.alter_column('cards', 'template_ord', server_default=None)
    op.add_column('cards', sa.Column('anki_id', sa.BigInteger(), nullable=True))

    cards = sa.table('cards', sa.column('id'), sa.column('note_id'), sa.column('front'), sa.column('back'),
                     sa.column('kind'), sa.column('priority'), sa.column('created_at'), sa.column('updated_at'))
    for card in bind.execute(sa.select(cards)).all():
        fields = json.dumps([html.escape(card.front), html.escape(card.back)], ensure_ascii=False)
        note_id = bind.execute(
            notes.insert()
            .values(note_type_id=basic_id, fields=fields, kind=card.kind, priority=card.priority,
                    created_at=card.created_at, updated_at=card.updated_at)
            .returning(notes.c.id)
        ).scalar_one()
        bind.execute(cards.update().where(cards.c.id == card.id).values(note_id=note_id))

    op.alter_column('cards', 'note_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(op.f('fk_cards_note_id_notes'), 'cards', 'notes', ['note_id'], ['id'], ondelete='CASCADE')
    op.create_unique_constraint(op.f('uq_cards_note_id_template_ord'), 'cards', ['note_id', 'template_ord'])
    op.create_index('ix_cards_anki_id', 'cards', ['anki_id'], unique=True, mssql_where=sa.text('anki_id IS NOT NULL'))

    # SQL Server refuses to drop a column that a CHECK constraint uses, so drop those first
    op.drop_constraint(op.f('ck_cards_kind'), 'cards', type_='check')
    op.drop_constraint(op.f('ck_cards_priority'), 'cards', type_='check')
    op.drop_column('cards', 'front')
    op.drop_column('cards', 'back')
    op.drop_column('cards', 'kind')
    op.drop_column('cards', 'priority')

    # 4. Generic scheduler state; existing cards are owned by FSRS
    op.add_column('review_states', sa.Column('scheduler', sa.Unicode(length=50), nullable=False, server_default='fsrs'))
    op.alter_column('review_states', 'scheduler', server_default=None)
    op.add_column('review_states', sa.Column('scheduler_state', sa.Unicode(), nullable=True))
    op.create_check_constraint(op.f('ck_review_states_scheduler_state_json'), 'review_states', 'ISJSON(scheduler_state) = 1')
    op.drop_column('review_states', 'step')
    op.drop_constraint(op.f('ck_review_states_status'), 'review_states', type_='check')
    op.create_check_constraint(op.f('ck_review_states_status'), 'review_states',
                               "status IN ('new', 'learning', 'review', 'relearning')")

    # 5. Reviews: answer duration, and a rename that keeps the existing values
    op.add_column('reviews', sa.Column('duration_ms', sa.Integer(), nullable=True))
    op.alter_column('reviews', 'scheduler_version', new_column_name='scheduler',
                    existing_type=sa.Unicode(length=20), existing_nullable=False)
    op.alter_column('reviews', 'scheduler', type_=sa.Unicode(length=50),
                    existing_type=sa.Unicode(length=20), existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema.

    Best effort: card content is restored from the first two fields of each note. Notes with
    more fields, note types, templates and tags are lost.
    """
    op.alter_column('reviews', 'scheduler', type_=sa.Unicode(length=20),
                    existing_type=sa.Unicode(length=50), existing_nullable=False)
    op.alter_column('reviews', 'scheduler', new_column_name='scheduler_version',
                    existing_type=sa.Unicode(length=20), existing_nullable=False)
    op.drop_column('reviews', 'duration_ms')

    op.execute("UPDATE review_states SET status = 'learning' WHERE status = 'relearning'")
    op.drop_constraint(op.f('ck_review_states_status'), 'review_states', type_='check')
    op.create_check_constraint(op.f('ck_review_states_status'), 'review_states',
                               "status IN ('new', 'learning', 'review')")
    op.add_column('review_states', sa.Column('step', sa.SmallInteger(), nullable=False, server_default='0'))
    op.alter_column('review_states', 'step', server_default=None)
    op.drop_constraint(op.f('ck_review_states_scheduler_state_json'), 'review_states', type_='check')
    op.drop_column('review_states', 'scheduler_state')
    op.drop_column('review_states', 'scheduler')

    op.add_column('cards', sa.Column('front', sa.Unicode(), nullable=True))
    op.add_column('cards', sa.Column('back', sa.Unicode(), nullable=True))
    op.add_column('cards', sa.Column('kind', sa.Unicode(length=20), nullable=True))
    op.add_column('cards', sa.Column('priority', sa.SmallInteger(), nullable=True))
    op.execute("""
        UPDATE c SET
            front = COALESCE(JSON_VALUE(n.fields, '$[0]'), ''),
            back = COALESCE(JSON_VALUE(n.fields, '$[1]'), ''),
            kind = n.kind,
            priority = n.priority
        FROM cards c JOIN notes n ON n.id = c.note_id
    """)
    for column, type_ in [('front', sa.Unicode()), ('back', sa.Unicode()),
                          ('kind', sa.Unicode(length=20)), ('priority', sa.SmallInteger())]:
        op.alter_column('cards', column, existing_type=type_, nullable=False)
    op.create_check_constraint(op.f('ck_cards_kind'), 'cards',
                               "kind IN ('basic', 'definition', 'theorem', 'proof', 'application', 'vocab')")
    op.create_check_constraint(op.f('ck_cards_priority'), 'cards', 'priority BETWEEN 1 AND 3')

    op.drop_index('ix_cards_anki_id', table_name='cards', mssql_where=sa.text('anki_id IS NOT NULL'))
    op.drop_constraint(op.f('uq_cards_note_id_template_ord'), 'cards', type_='unique')
    op.drop_constraint(op.f('fk_cards_note_id_notes'), 'cards', type_='foreignkey')
    op.drop_column('cards', 'anki_id')
    op.drop_column('cards', 'template_ord')
    op.drop_column('cards', 'note_id')

    op.drop_index(op.f('ix_note_tags_tag_id'), table_name='note_tags')
    op.drop_table('note_tags')
    op.drop_index(op.f('ix_notes_note_type_id'), table_name='notes')
    op.drop_index('ix_notes_anki_guid', table_name='notes', mssql_where=sa.text('anki_guid IS NOT NULL'))
    op.drop_table('notes')
    op.drop_table('note_type_templates')
    op.drop_table('tags')
    op.drop_index('ix_note_types_anki_id', table_name='note_types', mssql_where=sa.text('anki_id IS NOT NULL'))
    op.drop_table('note_types')
