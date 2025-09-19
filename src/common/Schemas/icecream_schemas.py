from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class Client(BaseModel):
    """Модель клиента"""

    name: str = Field(description="Имя клиента")
    number: str = Field(description="Номер клиента")
    address: Optional[str] = Field(default=None, description="Адрес клиента")


class ProductSchema(BaseModel):
    """Базовая модель товара"""
    id: str = Field(description="id товара")
    name: str = Field(description="Наименование товара")
    price: str = Field(description="Цена товара")


class IceCreamProductSchema(BaseModel):
    """
    Модель позиции каталога для магазина мороженого.
    Содержит товар, цену и количество.
    """

    product: ProductSchema

    @model_validator(mode="before")
    @classmethod
    def flatten_to_nested(cls, data: Dict[str, Any]) -> Dict[str, Any]:

        # Ожидаем плоский формат: {"id": "...", "name": "...", "price": "...", "quantity"?: int}
        id = data.get("id")
        name = data.get("name")
        price = data.get("price")

        if name is None or price is None:
            raise ValueError("Fields 'name' and 'price' are required")

        return {
            "id": id,
            "name": name,
            "price": price,
        }


class ItemOrder(BaseModel):
    """Модель товара в заказе"""

    item_name: str = Field(description="Наименование товара")
    price: int = Field(description="Цена товара")
    quantity: int = Field(default=1, ge=1, description="Количество товара по умолчанию 1")

    def __repr__(self) -> str:
        return f"<ItemOrder({self.item_name=}, {self.price=}, {self.quantity=})>"


class Order(BaseModel):
    """Модель заказа."""

    delivery_address: str = Field(description="Адрес доставки или самовывоз")
    client_name: str = Field(description="Имя клиента")
    client_number: str = Field(description="Номер клиента")
    payment: str = Field(description="Метод оплаты, например наличные или kaspi")
    items: List[ItemOrder] = Field(description="Перечень всех товаров в заказе")

    def __repr__(self) -> str:
        return (
            f"<Order({self.delivery_address=}, "
            f"{self.client_name=}, "
            f"{self.client_number=}, "
            f"{self.payment=}, "
            f"{self.items=})>"
        )
