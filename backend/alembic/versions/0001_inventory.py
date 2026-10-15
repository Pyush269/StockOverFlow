"""Create the product catalog and immutable stock movement ledger."""
from alembic import op
import sqlalchemy as sa

revision = "0001_inventory"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("category", sa.String(80), server_default="General", nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reorder_level", sa.Integer(), server_default="5", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("sku", name=op.f("uq_products_sku")),
        sa.CheckConstraint("quantity >= 0", name=op.f("ck_products_quantity_nonnegative")),
        sa.CheckConstraint("unit_price >= 0", name=op.f("ck_products_price_nonnegative")),
        sa.CheckConstraint("reorder_level >= 0", name=op.f("ck_products_reorder_nonnegative")),
        sa.CheckConstraint("sku = upper(btrim(sku)) AND length(sku) > 0", name=op.f("ck_products_sku_normalized")),
        sa.CheckConstraint("length(btrim(name)) > 0", name=op.f("ck_products_name_nonempty")),
        sa.CheckConstraint("length(btrim(category)) > 0", name=op.f("ck_products_category_nonempty")),
    )
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(3), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(500), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_movements")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT", name=op.f("fk_stock_movements_product_id_products")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_stock_movements_quantity_positive")),
        sa.CheckConstraint("movement_type IN ('IN', 'OUT')", name=op.f("ck_stock_movements_type_valid")),
    )
    op.create_index("ix_stock_movements_product_created", "stock_movements", ["product_id", "created_at"])


def downgrade():
    op.drop_index("ix_stock_movements_product_created", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_table("products")
