from typing import Optional, List
from datetime import datetime

from sqlalchemy import (
    Integer, String, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

# Import de la Base déclarative - Assurez-vous que le chemin est correct
# Il faudra peut-être l'ajuster pour pointer vers src.core.database.Base
# Par exemple: from src.core.database import Base
# Ou utiliser un import relatif si possible. Pour l'instant, on garde l'original.
from ...core.database import Base


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relations ---
    # Relation vers AddressDB (qui sera défini dans son propre domaine/infra)
    addresses: Mapped[List["AddressDB"]] = relationship("AddressDB", back_populates="user", cascade="all, delete-orphan")
    # Relations vers OrderDB et QuoteDB (utiliser des strings pour éviter imports circulaires)
    orders: Mapped[List["OrderDB"]] = relationship("OrderDB", back_populates="user")
    quotes: Mapped[List["QuoteDB"]] = relationship("QuoteDB", back_populates="user")


# --- Définition des autres modèles liés (SUPPRIMÉE) ---
# La classe AddressDB est retirée d'ici et sera définie dans son propre fichier infra
# class AddressDB(Base): # Supprimé
#      __tablename__ = "addresses" # Supprimé
     # ... (contenu supprimé)

# --- IMPORTANT --- (Mis à jour)
# Il faudra s'assurer que l'import de `Base` est correct.
# Les relations utilisent des strings pour référencer les classes ORM des autres domaines.
# SQLAlchemy pourra résoudre ces relations si toutes les classes sont importées
# au moment de la configuration de l'application ou via `configure_mappers()`.
