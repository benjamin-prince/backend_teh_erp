"""TEHTEK — Insurance Seeds. Default plans seeded on first launch."""
from sqlalchemy.orm import Session
from app.modules.insurance.models import InsurancePlan


DEFAULT_PLANS = [
    {
        "name": "Basic Coverage",
        "name_fr": "Couverture de base",
        "description": "Covers total loss of package only. Ideal for low-value shipments.",
        "description_fr": "Couvre uniquement la perte totale du colis. Idéal pour les envois de faible valeur.",
        "rate_pct": 1.5,
        "min_premium": 2000,
        "max_coverage": None,
        "covers_loss": True,
        "covers_damage": False,
        "covers_theft": False,
        "covers_delay": False,
        "covers_customs": False,
        "covers_all_risks": False,
        "exclusions": "Does not cover partial loss, damage, theft, or customs seizure.",
        "exclusions_fr": "Ne couvre pas la perte partielle, les dommages, le vol ou la saisie douanière.",
        "sort_order": 1,
    },
    {
        "name": "Standard Coverage",
        "name_fr": "Couverture standard",
        "description": "Covers loss and physical damage to your package. Recommended for most shipments.",
        "description_fr": "Couvre la perte et les dommages physiques. Recommandé pour la plupart des envois.",
        "rate_pct": 2.5,
        "min_premium": 3500,
        "max_coverage": None,
        "covers_loss": True,
        "covers_damage": True,
        "covers_theft": False,
        "covers_delay": False,
        "covers_customs": False,
        "covers_all_risks": False,
        "exclusions": "Does not cover theft, delay, or customs seizure.",
        "exclusions_fr": "Ne couvre pas le vol, les retards ou la saisie douanière.",
        "sort_order": 2,
    },
    {
        "name": "Premium Coverage",
        "name_fr": "Couverture premium",
        "description": "Covers loss, damage, and theft. Best for electronics and high-value goods.",
        "description_fr": "Couvre la perte, les dommages et le vol. Idéal pour l'électronique et les biens de valeur.",
        "rate_pct": 3.5,
        "min_premium": 5000,
        "max_coverage": None,
        "covers_loss": True,
        "covers_damage": True,
        "covers_theft": True,
        "covers_delay": False,
        "covers_customs": False,
        "covers_all_risks": False,
        "exclusions": "Does not cover customs seizure or shipping delays.",
        "exclusions_fr": "Ne couvre pas la saisie douanière ni les retards de livraison.",
        "sort_order": 3,
    },
    {
        "name": "All-Risk Coverage",
        "name_fr": "Couverture tous risques",
        "description": "Complete protection — loss, damage, theft, delays, and customs seizure. Maximum peace of mind.",
        "description_fr": "Protection totale — perte, dommages, vol, retards et saisie douanière. Tranquillité d'esprit maximale.",
        "rate_pct": 5.0,
        "min_premium": 8000,
        "max_coverage": None,
        "covers_loss": True,
        "covers_damage": True,
        "covers_theft": True,
        "covers_delay": True,
        "covers_customs": True,
        "covers_all_risks": True,
        "exclusions": "Intentional damage by shipper or prohibited items not covered.",
        "exclusions_fr": "Les dommages intentionnels et les articles prohibés ne sont pas couverts.",
        "sort_order": 4,
    },
]


def seed_insurance_plans(db: Session, company_id: int) -> None:
    """Seed default insurance plans. Idempotent — skips if already seeded."""
    existing = db.query(InsurancePlan).filter_by(company_id=company_id).count()
    if existing > 0:
        return

    for plan_data in DEFAULT_PLANS:
        db.add(InsurancePlan(
            company_id=company_id,
            **plan_data,
        ))
    db.commit()
