"""Add product_categories table with seeded data

Revision ID: a1b2c3d4e5f6
Revises: e9f0a1b2c3d4
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'e9f0a1b2c3d4'
branch_labels = None
depends_on = None


CATEGORIES = [
    # key, label_fr, label_en, icon, description_fr, description_en, sort_order, show_in_shop
    ("electronics",        "Téléphones & Tablettes",    "Phones & Tablets",      "📱", "Smartphones, tablettes, montres connectées",       "Smartphones, tablets, smartwatches",          1,  True),
    ("it_equipment",       "Ordinateurs & Informatique","Computers & IT",        "💻", "Laptops, desktops, All-in-One, serveurs",          "Laptops, desktops, All-in-One, servers",      2,  True),
    ("printer",            "Imprimantes & Scanners",    "Printers & Scanners",   "🖨️", "Imprimantes jet d'encre, laser, scanners",        "Inkjet, laser printers, scanners",            3,  True),
    ("network_equipment",  "Réseau & Wi-Fi",            "Network & Wi-Fi",       "📡", "Routeurs, switches, points d'accès",              "Routers, switches, access points",            4,  True),
    ("security_equipment", "Sécurité & Biométrie",      "Security & Biometrics", "🔒", "Caméras IP, NVR, contrôle d'accès",               "IP cameras, NVR, access control",             5,  True),
    ("solar_equipment",    "Solaire & Onduleurs",       "Solar & UPS",           "☀️", "Panneaux, batteries, onduleurs, régulateurs",     "Panels, batteries, inverters, regulators",    6,  True),
    ("storage",            "Stockage & NAS",            "Storage & NAS",         "💾", "Disques durs, SSD, NAS, clés USB",                "Hard drives, SSD, NAS, USB drives",           7,  True),
    ("telecom",            "Télécom & VoIP",            "Telecom & VoIP",        "☎️", "Téléphonie fixe, PABX, interphones",              "Fixed telephony, PABX, intercoms",            8,  True),
    ("tv_av",              "TV & Électroménager",       "TV & Electronics",      "📺", "Téléviseurs, audio, électroménager",              "TVs, audio, home electronics",                9,  True),
    ("accessories",        "Accessoires",               "Accessories",           "🎧", "Câbles, chargeurs, coques, casques",               "Cables, chargers, cases, headsets",           10, True),
    ("consumable",         "Consommables",              "Consumables",           "🔋", "Encres, toners, piles, câbles divers",            "Inks, toners, batteries, misc cables",        11, True),
    ("office_supplies",    "Bureautique",               "Office Supplies",       "🗂️", "Papeterie, fournitures, mobilier tech",           "Stationery, supplies, tech furniture",        12, True),
    ("pc_peripherals",     "Périphériques PC",          "PC Peripherals",        "🖥️", "Écrans, claviers, souris, webcams",               "Monitors, keyboards, mice, webcams",          13, True),
    ("pc_components",      "Composants PC",             "PC Components",         "🔩", "CPU, RAM, GPU, carte mère, alimentation",         "CPU, RAM, GPU, motherboard, PSU",             14, True),
    ("spare_part",         "Pièces détachées",          "Spare Parts",           "🔧", "Pièces de rechange et composants",                "Replacement parts and components",            15, False),
    ("packaging",          "Emballage",                 "Packaging",             "📦", "Boîtes, rubans, protections",                     "Boxes, tapes, protective materials",          16, False),
    ("other",              "Autre",                     "Other",                 "⚙️", "Divers",                                          "Miscellaneous",                               17, False),
]


def upgrade():
    op.create_table(
        "product_categories",
        sa.Column("id",             sa.Integer,     primary_key=True),
        sa.Column("key",            sa.String(64),  nullable=False, unique=True),
        sa.Column("label_fr",       sa.String(128), nullable=False),
        sa.Column("label_en",       sa.String(128), nullable=False),
        sa.Column("icon",           sa.String(8),   nullable=True),
        sa.Column("description_fr", sa.String(256), nullable=True),
        sa.Column("description_en", sa.String(256), nullable=True),
        sa.Column("sort_order",     sa.Integer,     server_default="0"),
        sa.Column("show_in_shop",   sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("is_active",      sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("created_at",     sa.DateTime,    server_default=sa.func.now()),
        sa.Column("deleted_at",     sa.DateTime,    nullable=True),
    )

    cat_table = sa.table("product_categories",
        sa.column("key"), sa.column("label_fr"), sa.column("label_en"),
        sa.column("icon"), sa.column("description_fr"), sa.column("description_en"),
        sa.column("sort_order"), sa.column("show_in_shop"),
    )
    op.bulk_insert(cat_table, [
        {"key": k, "label_fr": lfr, "label_en": len_, "icon": icon,
         "description_fr": dfr, "description_en": den,
         "sort_order": so, "show_in_shop": shop}
        for k, lfr, len_, icon, dfr, den, so, shop in CATEGORIES
    ])


def downgrade():
    op.drop_table("product_categories")
