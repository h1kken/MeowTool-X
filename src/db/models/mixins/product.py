from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


class ProductMixin:
    product_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))


class ResultProductMixin:
    product_ref_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    result_ref_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
