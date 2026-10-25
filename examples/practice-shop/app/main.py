"""商品练习：同一份程序支持 SQLite 和 MySQL，缓存可以按需接入。"""

import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from redis import Redis
from sqlalchemy import Boolean, Integer, String, create_engine, func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
logger = logging.getLogger("practice-shop")
DB_KIND = os.getenv("DB_KIND", "sqlite").lower()
ADMIN_KEY = os.getenv("ADMIN_KEY", "")
data_dir = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
if not data_dir.is_absolute():
    data_dir = ROOT / data_dir
data_dir.mkdir(parents=True, exist_ok=True)

if DB_KIND == "sqlite":
    database_url = URL.create("sqlite", database=str(data_dir / "shop.db"))
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
elif DB_KIND == "mysql":
    database_url = URL.create(
        "mysql+pymysql", username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"], host=os.getenv("MYSQL_HOST", "mysql"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "practice_shop"),
        query={"charset": "utf8mb4"},
    )
    engine = create_engine(database_url, pool_pre_ping=True)
else:
    raise RuntimeError("DB_KIND 只支持 sqlite 或 mysql。")

redis_url = os.getenv("REDIS_URL", "").strip()
cache = Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1) if redis_url else None
VERSION_KEY = "practice-shop:v1:products-version"


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80))
    price_cents: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=80, examples=["练习用水杯"])
    price_cents: int = Field(ge=0, le=100_000_000, examples=[2990])
    stock: int = Field(ge=0, le=1_000_000, examples=[50])
    is_published: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("商品名称不能为空白。")
        return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    # 只为全新空表加入练习记录，已有记录不会被覆盖。
    with Session(engine) as session:
        if session.scalar(select(func.count()).select_from(Product)) == 0:
            session.add_all([
                Product(name="练习用水杯", price_cents=2990, stock=50, is_published=True),
                Product(name="A5 笔记本", price_cents=1200, stock=100, is_published=False),
            ])
            session.commit()
    yield
    engine.dispose()


app = FastAPI(title="商品管理练习 API", version="1.0", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=ROOT / "app" / "static"), name="assets")
key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin(key: str | None = Depends(key_header)) -> None:
    if not ADMIN_KEY:
        raise HTTPException(503, "尚未配置管理员口令，请先运行初始化脚本并重新启动。")
    if not key or not hmac.compare_digest(key, ADMIN_KEY):
        raise HTTPException(401, "管理员口令不正确。请查看本项目 .env 中的 ADMIN_KEY。")


def to_dict(product: Product) -> dict:
    return {"id": product.id, "name": product.name, "price_cents": product.price_cents,
            "stock": product.stock, "is_published": product.is_published}


def invalidate_cache() -> None:
    if cache:
        try:
            # 使用本项目专属版本号，不清空 Redis 中的其他业务数据。
            cache.incr(VERSION_KEY)
        except Exception:
            logger.warning("缓存暂不可用，本次操作仍已写入数据库。")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/health", summary="检查数据库与可选缓存")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    cache_state = "未启用"
    if cache:
        try:
            cache.ping()
            cache_state = "连接正常"
        except Exception:
            cache_state = "暂不可用，已回退到数据库"
    return {"status": "ok", "database": DB_KIND, "redis": cache_state}


@app.get("/api/products", summary="分页查询商品，观察真实返回数据")
def list_products(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
                  search: str = Query("", max_length=80)):
    search = search.strip()
    cache_key = None
    if cache:
        try:
            version = cache.get(VERSION_KEY) or "0"
            digest = hashlib.sha256(json.dumps([page, page_size, search]).encode()).hexdigest()[:20]
            cache_key = f"practice-shop:v1:list:{version}:{digest}"
            saved = cache.get(cache_key)
            if saved:
                result = json.loads(saved)
                result["source"] = "redis"
                return result
        except Exception:
            logger.warning("缓存读取失败，已查询数据库。")
    with Session(engine) as session:
        statement = select(Product)
        count_statement = select(func.count()).select_from(Product)
        if search:
            condition = Product.name.contains(search, autoescape=True)
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        total = session.scalar(count_statement)
        products = session.scalars(statement.order_by(Product.id).offset((page - 1) * page_size).limit(page_size)).all()
        result = {"code": 0, "message": "OK", "source": DB_KIND,
                  "data": {"items": [to_dict(p) for p in products], "total": total,
                           "page": page, "page_size": page_size}}
    if cache_key:
        try:
            cache.setex(cache_key, 30, json.dumps(result, ensure_ascii=False))
        except Exception:
            logger.warning("缓存写入失败，已正常返回数据库结果。")
    return result


@app.post("/api/products", status_code=201, dependencies=[Depends(require_admin)], summary="新增商品，需要管理员口令")
def create_product(value: ProductInput):
    with Session(engine) as session:
        product = Product(**value.model_dump())
        session.add(product)
        session.commit()
        session.refresh(product)
        result = {"code": 0, "message": "商品已保存", "data": to_dict(product)}
    invalidate_cache()
    return result


@app.put("/api/products/{product_id}", dependencies=[Depends(require_admin)], summary="修改商品，需要管理员口令")
def update_product(product_id: int, value: ProductInput):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(404, "没有找到该商品。")
        for name, field_value in value.model_dump().items():
            setattr(product, name, field_value)
        session.commit()
        session.refresh(product)
        result = {"code": 0, "message": "商品已修改", "data": to_dict(product)}
    invalidate_cache()
    return result
