from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.modules.containers.models import Container, ContainerType


def generate_container_number(
    db: Session,
    ctype: ContainerType = ContainerType.sea,
) -> str:
    prefix_map = {
        ContainerType.sea:      "CONT",
        ContainerType.air:      "AIR",
        ContainerType.groupage: "GRP",
    }
    prefix  = prefix_map.get(ctype, "CONT")
    year    = datetime.utcnow().year
    pattern = f"{prefix}-{year}-%"

    last = db.execute(
        select(Container.container_number)
        .where(Container.container_number.like(pattern))
        .order_by(Container.container_number.desc())
        .limit(1)
    ).scalar_one_or_none()

    if last:
        try:
            last_seq = int(last.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0

    return f"{prefix}-{year}-{last_seq + 1:04d}"
