"""Synchronize WB product cards into local listing records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from wb_ops.db.models import SkuPool, WbListing
from wb_ops.integrations.wb.client import WildberriesClient
from wb_ops.integrations.wb.config import WbIntegrationConfig
from wb_ops.integrations.wb.schemas import ProductCard, normalize_vendor_code


@dataclass(slots=True)
class StoreSyncResult:
    """Synchronization result for one WB store."""

    shop_name: str
    fetched_cards: int = 0
    matched_cards: int = 0
    created_listings: int = 0
    updated_listings: int = 0
    delisted_listings: int = 0
    skipped_cards: int = 0
    affected_skus: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ListingSyncResult:
    """Synchronization result for all configured stores."""

    stores: list[StoreSyncResult] = field(default_factory=list)

    @property
    def fetched_cards(self) -> int:
        return sum(store.fetched_cards for store in self.stores)

    @property
    def matched_cards(self) -> int:
        return sum(store.matched_cards for store in self.stores)

    @property
    def created_listings(self) -> int:
        return sum(store.created_listings for store in self.stores)

    @property
    def updated_listings(self) -> int:
        return sum(store.updated_listings for store in self.stores)


class WbListingSyncService:
    """Map WB ``vendorCode``/``nmID`` to local SKU listing status."""

    def __init__(self, db: Session, config: WbIntegrationConfig) -> None:
        self.db = db
        self.config = config

    def sync_all_stores(self) -> ListingSyncResult:
        """Synchronize product cards for every enabled store in the token config."""

        result = ListingSyncResult()
        for store in self.config.enabled_stores:
            client = WildberriesClient(
                api_token=store.api_token,
                base_url=self.config.content_api_base_url,
                timeout_seconds=self.config.request_timeout_seconds,
            )
            result.stores.append(self.sync_store(store.shop_name, client))
        return result

    def sync_store(self, shop_name: str, client: WildberriesClient) -> StoreSyncResult:
        """Synchronize one WB store and update local listing statuses."""

        sku_map = self._load_sku_map()
        result = StoreSyncResult(shop_name=shop_name)
        seen_vendor_codes: set[str] = set()

        for card in client.iter_product_cards(limit=self.config.cards_page_limit):
            result.fetched_cards += 1
            normalized_vendor_code = normalize_vendor_code(card.vendor_code)
            sku = sku_map.get(normalized_vendor_code)
            if sku is None:
                result.skipped_cards += 1
                continue
            seen_vendor_codes.add(normalized_vendor_code)
            result.matched_cards += 1
            result.affected_skus.add(sku)
            created = self._upsert_listing(shop_name=shop_name, sku=sku, card=card, vendor_code=normalized_vendor_code)
            if created:
                result.created_listings += 1
            else:
                result.updated_listings += 1

        if self.config.mark_missing_cards_as_delisted:
            result.delisted_listings = self._mark_missing_as_delisted(shop_name, seen_vendor_codes, result.affected_skus)

        self._refresh_listing_statuses(result.affected_skus)
        self.db.commit()
        return result

    def _load_sku_map(self) -> dict[str, str]:
        """Return normalized ``vendorCode`` to local SKU mapping."""

        rows = self.db.execute(select(SkuPool.sku)).scalars().all()
        return {normalize_vendor_code(sku): sku for sku in rows}

    def _upsert_listing(self, shop_name: str, sku: str, card: ProductCard, vendor_code: str) -> bool:
        """Insert or update a WB listing by ``shop_name + vendor_code``."""

        now = datetime.utcnow()
        statement: Select[tuple[WbListing]] = select(WbListing).where(
            WbListing.shop_name == shop_name,
            WbListing.vendor_code == vendor_code,
        )
        listing = self.db.execute(statement).scalar_one_or_none()
        if listing is None:
            self.db.add(
                WbListing(
                    sku=sku,
                    shop_name=shop_name,
                    nm_id=str(card.nm_id),
                    vendor_code=vendor_code,
                    listing_time=now,
                    status="已上架",
                    last_sync_time=now,
                )
            )
            return True

        listing.sku = sku
        listing.nm_id = str(card.nm_id)
        listing.status = "已上架"
        listing.last_sync_time = now
        return False

    def _mark_missing_as_delisted(self, shop_name: str, seen_vendor_codes: set[str], affected_skus: set[str]) -> int:
        """Optionally mark previously known store listings as delisted."""

        statement = select(WbListing).where(WbListing.shop_name == shop_name, WbListing.status == "已上架")
        listings = self.db.execute(statement).scalars().all()
        count = 0
        now = datetime.utcnow()
        for listing in listings:
            if normalize_vendor_code(listing.vendor_code) in seen_vendor_codes:
                continue
            listing.status = "已下架"
            listing.last_sync_time = now
            affected_skus.add(listing.sku)
            count += 1
        return count

    def _refresh_listing_statuses(self, skus: set[str]) -> None:
        """Refresh ``shop_count`` and ``listing_status`` for affected SKUs."""

        for sku in skus:
            active_shop_count = self.db.scalar(
                select(func.count()).select_from(WbListing).where(WbListing.sku == sku, WbListing.status == "已上架")
            )
            shop_count = int(active_shop_count or 0)
            self.db.execute(
                update(SkuPool)
                .where(SkuPool.sku == sku)
                .values(
                    shop_count=shop_count,
                    listing_status="已上架" if shop_count > 0 else "未上架",
                    updated_at=datetime.utcnow(),
                )
            )
