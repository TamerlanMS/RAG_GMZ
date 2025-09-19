from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

import requests  # type: ignore
from fastapi import Depends
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import now

from src.common.Schemas.icecream_schemas import ProductSchema
from src.common.logger import logger
from src.common.vector_store import vector_store
from src.db.database import engine, get_db
from src.db.Models import Base, Product


def create_db() -> str:
    """
    Создает базу данных и таблицы, если они не существуют.
    Если база уже существует, ничего не делает.

    :return: Сообщение о результате операции
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exp:
        if "already exists" in str(exp):
            logger.info("Database already exists")
            return "Database already exists"
        else:
            logger.error("Failed to create database: %s", exp)
            raise
    else:
        return "Database created successfully"


def drop_db() -> str:
    """
    Удаляет все таблицы из базы данных.

    :return: Сообщение о результате операции
    """
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as exp:
        if "does not exist" in str(exp):
            logger.info("Database does not exist")
            return "Database does not exist"
        else:
            logger.error("Failed to drop database: %s", exp)
            raise
    else:
        return "Database dropped successfully"


def __get_json_from_url(
    address: str,
    params: Optional[Dict[Any, Any]] = None,
    headers: Optional[Dict[Any, Any]] = None,
) -> Any:
    """
    Отправляет GET-запрос по указанному URL и возвращает ответ в формате JSON.

    :param address: URL для запроса
    :param params: (опционально) параметры запроса
    :param headers: (опционально) заголовки запроса
    :return: Ответ в формате dict (JSON)
    :raises: requests.RequestException, ValueError
    """
    response = requests.get(address, params=params, headers=headers)
    response.raise_for_status()  # выбросит исключение, если код ответа не 2xx
    return response.json()


def __get_products_from_json(
    json_data: Optional[Dict[Any, Any]],
) -> List[ProductSchema]:
    """
    Получает список PharmacyProductSchema из JSON-данных.
    :param json_data: Словарь с ключом "Products", содержащим список продуктов
    :return: Список PharmacyProductSchema
    """
    if not json_data:
        raise ValueError(
            "JSON data is required. Please provide a valid JSON dictionary."
        )
    products = TypeAdapter(List[ProductSchema]).validate_python(
        json_data["Products"]
    )
    return products


def update_db(
    db: Annotated[Session, Depends(get_db)],
    json_url: str = "https://ts23.cloud1c.pro/FileGPT/GMZProducts.json",
    json_data: Optional[Dict[Any, Any]] = None,
) -> int:
    # """
    # Обновляет базу данных с bulk-операциями для ускорения массовой загрузки.
    #
    # :param json_url: URL с JSON-данными
    # :param json_data: (опционально) JSON-данные
    # :param db: SQLAlchemy session
    # :return: Количество добавленных записей
    # """
    # if not json_data:
    #     json_data = __get_json_from_url(json_url)
    # pydantic_list_of_products = __get_products_from_json(json_data)
    # counter = 0
    #
    # # Загружаем все существующие продукты и аптеки в память через scalars
    # products = db.scalars(select(Product)).all()
    # existing_products = {p.name: p.id for p in products}
    #
    # # Собираем новые продукты, исключая дубликаты внутри пачки
    # new_product_names = set()
    # new_products = []
    # for item in pydantic_list_of_products:
    #     p_name = item.product.name
    #     if p_name not in existing_products and p_name not in new_product_names:
    #         new_products.append(Product(name=p_name))
    #         new_product_names.add(p_name)
    #
    # # Bulk insert новых продуктов и аптек
    # if new_products:
    #     db.bulk_save_objects(new_products)
    # db.commit()
    #
    # # Обновим словари id через scalars
    # products = db.scalars(select(Product)).all()
    # existing_products = {p.name: p.id for p in products}

    if now.weekday() == 0 and (8 <= now.hour <= 9):
        logger.info("Starting to rebuild vector store")
        status_update = update_vector_store()
        logger.info("Vector store rebuilt status: %s", status_update)

    return counter


def get_product_price(product_name: str, pharmacy_address: str) -> Any:
    """
    Поиск цены продукта в конкретной аптеке
    :param product_name: Название продукта
    :param pharmacy_address: Адрес аптеки
    :return: Цена продукта или None, если не найдено
    """
    db = next(get_db())
    product = db.scalar(select(Product).where(Product.name.ilike(f"%{product_name}%")))
    if not product:
        return None

    return product.price


def get_products_by_name(product_name: str) -> Optional[List[str]]:
    db = next(get_db())
    products = db.scalars(
        select(Product).where(Product.name.ilike(f"%{product_name.lower()}%"))
    )
    if products:
        return [product.name for product in products]
    return None


def get_all_products() -> Optional[List[str]]:
    db = next(get_db())
    products = db.scalars(select(Product)).all()
    if products:
        return [product.name for product in products]
    return None


def update_vector_store() -> Any:
    products_names = get_all_products()
    if products_names:
        status_message = vector_store.rebuild_vector_store(
            products_names=products_names
        )
        return status_message
    return "No products found"
