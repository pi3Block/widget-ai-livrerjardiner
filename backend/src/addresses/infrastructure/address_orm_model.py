from typing import Optional, List
from datetime import datetime

from sqlalchemy import (
    Integer, String, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

# Import de la Base déclarative
# Assurez-vous que le chemin est correct (ex: backend.src.core.database.Base)
from ...core.database import Base # Temporaire, à ajuster

class AddressDB(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # La clé étrangère pointe vers users.id, qui est défini dans UserDB
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers UserDB (défini dans users/infrastructure)
    # Utilisation d'une string pour éviter l'import circulaire direct
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="addresses")

    # Relations vers OrderDB (pour livraison/facturation)
    # Ces relations seront définies plus précisément dans le modèle OrderDB
    # Utilisation de strings ici également.
    delivery_orders: Mapped[List["OrderDB"]] = relationship("OrderDB", back_populates="delivery_address", foreign_keys="[OrderDB.delivery_address_id]")
    billing_orders: Mapped[List["OrderDB"]] = relationship("OrderDB", back_populates="billing_address", foreign_keys="[OrderDB.billing_address_id]") 