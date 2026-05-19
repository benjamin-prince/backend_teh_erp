"""create personal life tables

Revision ID: b7e3a1f92c08
Revises: cae57c24e7f5
Create Date: 2025-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e3a1f92c08'
down_revision = 'a9f3b2c1d4e5'   # ✅ pointe vers la vraie head
branch_labels = None
depends_on = None


def upgrade():
    # Personal Expenses
    op.create_table(
        'personal_expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('category', sa.Enum(
            'food', 'transport', 'health', 'entertainment',
            'shopping', 'bills', 'education', 'sport', 'travel', 'other',
            name='expensecategory'
        ), nullable=False, server_default='other'),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('payment_method', sa.Enum(
            'cash', 'card', 'mobile_money', 'transfer', 'other',
            name='paymentmethod'
        ), server_default='cash'),
        sa.Column('is_recurring', sa.Boolean(), server_default='false'),
        sa.Column('tags', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_personal_expenses_date', 'personal_expenses', ['date'])

    # Personal Income
    op.create_table(
        'personal_income',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('source', sa.Enum(
            'salary', 'freelance', 'investment', 'gift', 'bonus', 'rental', 'other',
            name='incomesource'
        ), nullable=False, server_default='other'),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_personal_income_date', 'personal_income', ['date'])

    # Sport Activities
    op.create_table(
        'sport_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('activity_type', sa.String(100), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('calories_burned', sa.Integer(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('intensity', sa.Enum(
            'low', 'medium', 'high', 'extreme',
            name='sportintensity'
        ), server_default='medium'),
        sa.Column('heart_rate_avg', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sport_activities_date', 'sport_activities', ['date'])

    # Meals
    op.create_table(
        'personal_meals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.Enum(
            'breakfast', 'lunch', 'dinner', 'snack',
            name='mealtype'
        ), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('proteins_g', sa.Float(), nullable=True),
        sa.Column('carbs_g', sa.Float(), nullable=True),
        sa.Column('fats_g', sa.Float(), nullable=True),
        sa.Column('water_ml', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_personal_meals_date', 'personal_meals', ['date'])

    # Goals
    op.create_table(
        'personal_goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('goal_type', sa.Enum(
            'weight', 'savings', 'sport', 'nutrition', 'custom',
            name='goaltype'
        ), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('current_value', sa.Float(), server_default='0'),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum(
            'active', 'completed', 'abandoned',
            name='goalstatus'
        ), server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Daily Summary
    op.create_table(
        'personal_daily_summary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False, unique=True),
        sa.Column('mood', sa.Integer(), nullable=True),
        sa.Column('energy_level', sa.Integer(), nullable=True),
        sa.Column('sleep_hours', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date'),
    )


def downgrade():
    op.drop_table('personal_daily_summary')
    op.drop_table('personal_goals')
    op.drop_table('personal_meals')
    op.drop_table('sport_activities')
    op.drop_table('personal_income')
    op.drop_table('personal_expenses')
    # Drop enums
    for enum_name in ['expensecategory', 'paymentmethod', 'incomesource',
                      'sportintensity', 'mealtype', 'goaltype', 'goalstatus']:
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
