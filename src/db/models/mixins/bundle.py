from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column


class BundleMixin:    
    bundle_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))


class ResultBundleMixin:
    bundle_ref_id: Mapped[int] = mapped_column(ForeignKey("bundles.id"), index=True)
    result_ref_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
