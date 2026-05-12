import aiohttp
import asyncio
from typing import Optional
from loguru import logger
from config import PROVIDERS


class SMMProvider:
    def __init__(self, provider_key: str):
        cfg = PROVIDERS[provider_key]
        self.key = provider_key
        self.name = cfg["name"]
        self.api_url = cfg["api_url"]
        self.api_key = cfg["api_key"]

    async def _post(self, data: dict) -> Optional[dict]:
        if not self.api_url or not self.api_key:
            return None
        data["key"] = self.api_key
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(self.api_url, data=data) as resp:
                    if resp.status == 200:
                        return await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"[{self.name}] API call failed: {e}")
        return None

    async def get_balance(self) -> Optional[float]:
        res = await self._post({"action": "balance"})
        if res and "balance" in res:
            try:
                return float(res["balance"])
            except Exception:
                pass
        return None

    async def get_services(self) -> list:
        res = await self._post({"action": "services"})
        if isinstance(res, list):
            return res
        return []

    async def place_order(self, service_id: str, link: str, quantity: int) -> Optional[dict]:
        res = await self._post({
            "action": "add",
            "service": service_id,
            "link": link,
            "quantity": quantity,
        })
        if res and "order" in res:
            return {"order_id": str(res["order"]), "provider": self.key}
        if res and "error" in res:
            logger.warning(f"[{self.name}] Order error: {res['error']}")
        return None

    async def get_order_status(self, order_id: str) -> Optional[dict]:
        res = await self._post({"action": "status", "order": order_id})
        if res:
            return {
                "status": res.get("status", "Unknown"),
                "start_count": res.get("start_count"),
                "remains": res.get("remains"),
                "charge": res.get("charge"),
            }
        return None

    async def get_multi_status(self, order_ids: list) -> dict:
        ids = ",".join(str(i) for i in order_ids)
        res = await self._post({"action": "status", "orders": ids})
        if isinstance(res, dict):
            return res
        return {}


class APIRouter:
    """Intelligent multi-provider failover engine."""

    def __init__(self):
        self.providers = {
            k: SMMProvider(k)
            for k, v in sorted(PROVIDERS.items(), key=lambda x: x[1]["priority"])
            if v.get("api_url") and v.get("api_key")
        }

    def _sorted_providers(self) -> list:
        return sorted(self.providers.values(), key=lambda p: PROVIDERS[p.key]["priority"])

    async def get_all_balances(self) -> dict:
        results = {}
        tasks = {k: p.get_balance() for k, p in self.providers.items()}
        for key, coro in tasks.items():
            try:
                balance = await coro
                results[key] = balance
            except Exception:
                results[key] = None
        return results

    async def sync_all_services(self) -> dict:
        """Fetch services from all providers; returns {provider: [services]}."""
        results = {}
        for key, provider in self.providers.items():
            try:
                services = await provider.get_services()
                results[key] = services
                logger.info(f"[{provider.name}] Synced {len(services)} services")
            except Exception as e:
                logger.error(f"[{provider.name}] Sync failed: {e}")
                results[key] = []
        return results

    async def place_order_with_failover(self, service_id: str, link: str,
                                        quantity: int, preferred_provider: str = None) -> Optional[dict]:
        """
        Attempt order placement with automatic provider failover.
        Priority order: preferred → sorted by priority → skip if balance=0 or error.
        """
        providers_to_try = []
        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(self.providers[preferred_provider])
        for p in self._sorted_providers():
            if p not in providers_to_try:
                providers_to_try.append(p)

        for provider in providers_to_try:
            try:
                balance = await provider.get_balance()
                if balance is not None and balance <= 0:
                    logger.warning(f"[{provider.name}] Skipping — zero balance")
                    continue
                result = await provider.place_order(service_id, link, quantity)
                if result:
                    result["provider_name"] = provider.name
                    logger.info(f"Order placed via {provider.name}: {result}")
                    return result
                logger.warning(f"[{provider.name}] Order returned None, trying next")
            except Exception as e:
                logger.error(f"[{provider.name}] Exception during order: {e}")
                continue

        logger.error("All providers failed for order placement")
        return None

    async def get_order_status(self, provider_key: str, order_id: str) -> Optional[dict]:
        if provider_key not in self.providers:
            return None
        return await self.providers[provider_key].get_order_status(order_id)

    async def get_provider_services(self, provider_key: str) -> list:
        if provider_key not in self.providers:
            return []
        return await self.providers[provider_key].get_services()


router = APIRouter()
