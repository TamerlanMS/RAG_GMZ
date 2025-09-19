from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric


Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Важно: имя индексируем — у вас поиск по ilike
    name: Mapped[str] = mapped_column(String(512), index=True, nullable=False, unique=True)
    # Цена — целое (как в JSON). Если понадобится копейки/дробные — поменяем на Numeric(12,2)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)