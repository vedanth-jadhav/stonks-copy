from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from quant_trading.schemas import PriceBar, PriceData
from quant_trading.services.pairs import PairsService


class FakePairsMarketData:
    def load_price_data(self, ticker: str, period: str = "1y") -> PriceData:
        _ = period
        start = datetime(2025, 1, 1, tzinfo=UTC)
        rich_leg = [100 + (idx * 0.5) for idx in range(252)]
        cheap_leg = [102 + (idx * 0.5) + ((-1) ** idx * 0.1) for idx in range(252)]
        closes = cheap_leg if any(name in ticker for name in ("HDFCBANK", "TCS", "HINDUNILVR", "COALINDIA", "ONGC", "AXISBANK", "SUNPHARMA")) else rich_leg
        return PriceData(
            ticker=ticker,
            last_price=closes[-1],
            history=[
                PriceBar(
                    open=close - 1,
                    high=close + 1,
                    low=close - 2,
                    close=close,
                    volume=1_000_000,
                    as_of=start + timedelta(days=idx),
                )
                for idx, close in enumerate(closes)
            ],
        )


def test_pairs_service_revalidates_and_persists_json(tmp_path) -> None:
    output_path = tmp_path / "validated_pairs.json"
    service = PairsService(output_path=output_path, market_data=FakePairsMarketData())
    validations = service.revalidate()

    assert output_path.exists()
    payload = json.loads(output_path.read_text())
    assert len(validations) == len(payload["pairs"])
    assert len(validations) > 0
    assert {"cheap", "rich", "beta", "alpha", "zscore", "half_life", "valid"} <= set(payload["pairs"][0])
