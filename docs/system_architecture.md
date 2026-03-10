# Quant Trading System — Remaining Architecture Plan
### Database · Orchestrator Flow · Scheduler · Error Handling · Holidays · P&L Report

---

## 1. Database Schema

Single SQLite file: `quant_trading.db`
Five tables. Nothing more, nothing less.

---

### Table 1: `trades`
Every buy and sell ever logged. The source of truth for P&L.

```sql
CREATE TABLE trades (
    trade_id            TEXT PRIMARY KEY,       -- UUID e.g. "a3f1c9d2-..."
    timestamp_ist       TEXT NOT NULL,          -- "2025-03-06 09:45:32"
    ticker              TEXT NOT NULL,          -- "RELIANCE"
    action              TEXT NOT NULL,          -- "BUY" | "SELL"
    shares              INTEGER NOT NULL,
    decision_price      REAL NOT NULL,          -- price when BOSS decided
    fill_price          REAL NOT NULL,          -- decision_price * (1 + slippage)
    gross_value         REAL NOT NULL,          -- shares * fill_price
    stt                 REAL NOT NULL,
    exchange_charges    REAL NOT NULL,
    sebi_charges        REAL NOT NULL,
    stamp_duty          REAL NOT NULL,          -- buy only, 0 on sell
    gst                 REAL NOT NULL,
    total_charges       REAL NOT NULL,
    net_cost            REAL NOT NULL,          -- gross_value + charges (buy) | gross_value - charges (sell)
    net_cost_per_share  REAL NOT NULL,          -- net_cost / shares
    stop_loss_price     REAL,
    target_price        REAL,
    conviction_score    REAL NOT NULL,
    trade_type          TEXT NOT NULL,          -- "MOMENTUM" | "MEAN_REVERSION" | "PAIRS" | "EVENT_DRIVEN"
    dominant_signal     TEXT NOT NULL,          -- which agent drove the trade
    regime_at_trade     TEXT NOT NULL,          -- "BULL" | "NEUTRAL" | "CAUTION" | "BEAR"
    agents_positive     INTEGER NOT NULL,       -- how many agents agreed (out of 8)
    linked_trade_id     TEXT,                   -- for SELL: points to the original BUY trade_id
    status              TEXT NOT NULL           -- "OPEN" | "CLOSED"
);
```

---

### Table 2: `positions`
Current open positions. Updated on every BUY and SELL.

```sql
CREATE TABLE positions (
    ticker              TEXT PRIMARY KEY,
    shares              INTEGER NOT NULL,
    avg_entry_price     REAL NOT NULL,          -- weighted avg if multiple buys
    total_cost          REAL NOT NULL,          -- total capital deployed including charges
    stop_loss_price     REAL NOT NULL,
    trailing_stop_active BOOLEAN DEFAULT FALSE,
    trade_type          TEXT NOT NULL,
    entry_date          TEXT NOT NULL,
    last_updated        TEXT NOT NULL
);
```

---

### Table 3: `portfolio_state`
Single-row table. The live portfolio snapshot. Updated after every trade and every EOD run.

```sql
CREATE TABLE portfolio_state (
    id                  INTEGER PRIMARY KEY DEFAULT 1,  -- always row 1
    cash_balance        REAL NOT NULL,                  -- starts at 1000000
    total_deployed      REAL NOT NULL,                  -- sum of all open position costs
    portfolio_value     REAL NOT NULL,                  -- cash + market value of positions
    peak_value          REAL NOT NULL,                  -- for MDD calculation
    total_realized_pnl  REAL NOT NULL DEFAULT 0,
    total_charges_paid  REAL NOT NULL DEFAULT 0,
    inception_date      TEXT NOT NULL,
    last_updated        TEXT NOT NULL
);
```

---

### Table 4: `signal_history`
Every signal score from every agent for every stock, every day. Agent 11 reads this to compute IC.

```sql
CREATE TABLE signal_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL,                  -- "2025-03-06"
    ticker              TEXT NOT NULL,
    agent               TEXT NOT NULL,                  -- "agent_03_momentum"
    signal_score        REAL NOT NULL,                  -- raw score before IC weighting
    adj_signal_score    REAL,                           -- after IC weighting
    forward_return_5d   REAL,                           -- filled in 5 days later by orchestrator
    forward_return_10d  REAL,                           -- filled in 10 days later
    ic_contribution     REAL                            -- computed by Agent 11
);

CREATE INDEX idx_signal_date_ticker ON signal_history(date, ticker);
CREATE INDEX idx_signal_agent ON signal_history(agent, date);
```

---

### Table 5: `daily_pnl`
End-of-day portfolio snapshot. The weekly report reads from this.

```sql
CREATE TABLE daily_pnl (
    date                TEXT PRIMARY KEY,               -- "2025-03-06"
    portfolio_value     REAL NOT NULL,
    cash_balance        REAL NOT NULL,
    unrealized_pnl      REAL NOT NULL,
    realized_pnl_today  REAL NOT NULL,
    total_return_pct    REAL NOT NULL,
    nifty_close         REAL NOT NULL,
    nifty_return_pct    REAL NOT NULL,
    alpha_pct           REAL NOT NULL,                  -- total_return - nifty_return
    india_vix           REAL NOT NULL,
    regime              TEXT NOT NULL,
    open_positions      INTEGER NOT NULL,
    trades_today        INTEGER NOT NULL,
    charges_today       REAL NOT NULL,
    portfolio_beta      REAL,
    var_95_pct          REAL,
    sharpe_63d          REAL,
    mdd_current_pct     REAL
);
```

---

---

## 2. Orchestrator Data Flow

Exact JSON contract between every agent. The orchestrator assembles these and passes them downstream.

---

### Step 1 → Agent 01 output → `universe`
```json
{
  "date": "2025-03-06",
  "watchlist": [
    {
      "ticker": "RELIANCE",
      "company": "Reliance Industries Ltd",
      "sector": "Energy",
      "market_cap_cr": 1850000,
      "adv_20d_cr": 1200,
      "promoter_pledging_pct": 0.0,
      "de_ratio": 0.4
    }
  ],
  "rejected_count": 42,
  "watchlist_count": 87
}
```

---

### Step 2 → Agent 02 output → `quality_watchlist`
Appends quality scores to each ticker. Filters to F-Score >= 6 only.

```json
{
  "quality_watchlist": [
    {
      "ticker": "RELIANCE",
      "company": "Reliance Industries Ltd",
      "sector": "Energy",
      "market_cap_cr": 1850000,
      "adv_20d_cr": 1200,
      "f_score": 7,
      "quality_score": 74.5,
      "ey": 0.072,
      "roce": 0.18
    }
  ],
  "filtered_out_count": 18,
  "quality_count": 69
}
```

---

### Step 3 → Agent 06 output → `regime`
Single object. Hard gate for the entire day.

```json
{
  "regime": "NEUTRAL",
  "india_vix": 16.4,
  "final_max_deploy": 0.48,
  "nifty_above_sma200": true,
  "fii_signal": "POSITIVE",
  "fii_5d_net_cr": 3420.5,
  "breadth_pct": 0.61,
  "momentum_active": true,
  "quality_only": false,
  "hard_block": false
}
```

---

### Step 4 → Agent 10 output → `event_map`
Keyed by ticker for O(1) lookup.

```json
{
  "event_map": {
    "RELIANCE": {
      "event_block": false,
      "block_reason": "",
      "days_to_earnings": 42,
      "catalyst_score": 0.0,
      "catalyst_type": ""
    },
    "INFY": {
      "event_block": true,
      "block_reason": "earnings_in_3_days",
      "days_to_earnings": 3,
      "catalyst_score": 0.0,
      "catalyst_type": ""
    }
  }
}
```

---

### Step 5 → Agent 09 output → `sentiment_map`
Keyed by ticker.

```json
{
  "sentiment_map": {
    "RELIANCE": {
      "sentiment_signal": 0.45,
      "confidence": "medium",
      "article_count": 4,
      "hard_override": false
    }
  }
}
```

---

### Step 6 → Agent 07 output → `sector_map`
Keyed by sector name.

```json
{
  "sector_map": {
    "Energy": { "composite_score": 78.2, "rank": 2, "weight_multiplier": 1.30 },
    "IT":     { "composite_score": 31.1, "rank": 11, "weight_multiplier": 0.50 }
  }
}
```

---

### Step 7 → Agent 08 output → `ownership_map`
Keyed by ticker.

```json
{
  "ownership_map": {
    "RELIANCE": { "ownership_signal": 0.62 },
    "TCS":      { "ownership_signal": 0.28 }
  }
}
```

---

### Step 8 → Agent 13 output (pre-open MODE A) → `risk_precheck`

```json
{
  "positions_to_close": ["WIPRO", "ONGC"],
  "close_reasons": {
    "WIPRO": "stop_loss_breach",
    "ONGC":  "trailing_stop_triggered"
  },
  "risk_metrics": {
    "var_95_pct": 1.82,
    "portfolio_beta": 0.71,
    "mdd_current": -0.043,
    "sharpe_63d": 1.84,
    "calmar_63d": 1.21,
    "cash_pct": 0.41
  }
}
```

---

### Step 9 → Agents 03, 04, 05 output → `signal_map`
All three agents run in parallel. Orchestrator merges into one map.

```json
{
  "signal_map": {
    "RELIANCE": {
      "momentum_score": 0.72,
      "reversion_score": -0.15,
      "pairs_score": 0.0,
      "pairs_with": null
    },
    "HDFCBANK": {
      "momentum_score": 0.31,
      "reversion_score": 0.68,
      "pairs_score": 0.85,
      "pairs_with": "ICICIBANK"
    }
  }
}
```

---

### Step 10 → Agent 12 output → `liquidity_map`
Keyed by ticker.

```json
{
  "liquidity_map": {
    "RELIANCE": {
      "liquidity_multiplier": 1.00,
      "impact_cost_pct": 0.05,
      "max_position_from_adv_cr": 24.0
    }
  }
}
```

---

### Step 11 → Agent 11 output → `ic_stats`

```json
{
  "ic_stats": {
    "momentum": 0.071,
    "reversion": 0.058,
    "pairs": 0.083
  },
  "ic_weights": {
    "momentum": 0.33,
    "reversion": 0.27,
    "pairs": 0.40
  },
  "win_rates": {
    "momentum": 0.58,
    "reversion": 0.54
  },
  "avg_rr": {
    "momentum": 2.1,
    "reversion": 1.8
  },
  "adjusted_signals": [
    {
      "ticker": "RELIANCE",
      "adj_momentum": 0.52,
      "adj_reversion": -0.11,
      "adj_pairs": 0.0
    }
  ]
}
```

---

### Step 12 → BOSS full payload (assembled by orchestrator)
This is the single object BOSS receives. Everything it needs, nothing extra.

```json
{
  "date": "2025-03-06",
  "time_ist": "09:40:00",
  "portfolio_state": {
    "portfolio_value": 1048200,
    "cash_balance": 524100,
    "cash_pct": 0.50,
    "open_positions": 4
  },
  "regime": { ... },
  "ic_stats": { ... },
  "candidates": [
    {
      "ticker": "RELIANCE",
      "sector": "Energy",
      "quality_score": 74.5,
      "f_score": 7,
      "event_block": false,
      "catalyst_score": 0.0,
      "sentiment_signal": 0.45,
      "ownership_signal": 0.62,
      "adj_momentum": 0.52,
      "adj_reversion": -0.11,
      "adj_pairs": 0.0,
      "sector_multiplier": 1.30,
      "liquidity_multiplier": 1.00,
      "impact_cost_pct": 0.05,
      "max_position_from_adv_cr": 24.0,
      "current_price": 1284.50,
      "win_rate_dominant": 0.58,
      "avg_rr_dominant": 2.1
    }
  ]
}
```

---

### Step 13 → BOSS output → `trade_decisions`

```json
{
  "trade_decisions": [
    {
      "decision": "BUY",
      "ticker": "RELIANCE",
      "trade_type": "MOMENTUM",
      "conviction_score": 0.71,
      "agents_positive": 6,
      "shares": 38,
      "entry_price": 1284.50,
      "final_position_inr": 48811,
      "position_pct_of_portfolio": 0.0466,
      "stop_loss_price": 1194.59,
      "target_price": 1393.60,
      "half_kelly_f": 0.052,
      "dominant_signal": "momentum",
      "rejection_reason": ""
    }
  ],
  "no_trade_count": 4,
  "watchlist_count": 2
}
```

---

### Step 14 → Agent 14 output → written to `trades` table

```json
{
  "execution_status": "LOGGED",
  "trade_id": "a3f1c9d2-7e4b-4a1c-b2d9-1f8e3c7a5b6d",
  "timestamp_ist": "2025-03-06 09:45:12",
  "ticker": "RELIANCE",
  "action": "BUY",
  "shares": 38,
  "decision_price": 1284.50,
  "fill_price": 1285.14,
  "slippage_pct": 0.0005,
  "gross_value": 48835.32,
  "stt": 48.84,
  "exchange_charges": 1.64,
  "sebi_charges": 0.05,
  "stamp_duty": 7.33,
  "gst": 0.30,
  "total_charges": 58.16,
  "net_cost": 48893.48,
  "net_cost_per_share": 1286.67,
  "stop_loss_price": 1194.59,
  "target_price": 1393.60,
  "conviction_score": 0.71,
  "trade_type": "MOMENTUM",
  "regime_at_trade": "NEUTRAL"
}
```

---

---

## 3. Scheduler Design

**Library:** `APScheduler` (not cron — handles market holidays, dynamic rescheduling, and missed job recovery natively)

```bash
pip install apscheduler
```

---

### Schedule Definition

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

# Morning pipeline — full run
scheduler.add_job(run_morning_pipeline,   CronTrigger(hour=8,  minute=45, day_of_week="mon-fri"))

# Mid-session checks
scheduler.add_job(run_midday_reversion,   CronTrigger(hour=11, minute=30, day_of_week="mon-fri"))
scheduler.add_job(run_afternoon_refresh,  CronTrigger(hour=13, minute=0,  day_of_week="mon-fri"))
scheduler.add_job(run_risk_final_check,   CronTrigger(hour=14, minute=30, day_of_week="mon-fri"))

# End of day
scheduler.add_job(run_eod_pnl,            CronTrigger(hour=15, minute=35, day_of_week="mon-fri"))
scheduler.add_job(run_signal_backfill,    CronTrigger(hour=16, minute=0,  day_of_week="mon-fri"))

# Weekly jobs
scheduler.add_job(run_cointegration_revalidation, CronTrigger(day_of_week="sun", hour=8, minute=0))
scheduler.add_job(run_weekly_pnl_report,           CronTrigger(day_of_week="fri", hour=16, minute=30))
```

---

### Holiday Handling

```python
from jugaad_trader.nse import NSELive  # or maintain a static list

NSE_HOLIDAYS_2025 = [
    "2025-01-26",  # Republic Day
    "2025-03-14",  # Holi
    "2025-04-14",  # Dr. Ambedkar Jayanti
    "2025-04-18",  # Good Friday
    "2025-05-01",  # Maharashtra Day
    "2025-08-15",  # Independence Day
    "2025-10-02",  # Gandhi Jayanti
    "2025-10-21",  # Diwali Laxmi Puja (tentative)
    "2025-10-22",  # Diwali Balipratipada (tentative)
    "2025-11-05",  # Guru Nanak Jayanti (tentative)
    "2025-12-25",  # Christmas
]

def is_market_open() -> bool:
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if today in NSE_HOLIDAYS_2025:
        return False
    now = datetime.now(IST).time()
    return time(9, 15) <= now <= time(15, 30)

# Wrap every scheduled job
def run_morning_pipeline():
    if not is_market_open():
        logger.info("Market closed today — skipping pipeline")
        return
    orchestrator.run()
```

---

### What Happens if a Job Fails Mid-Pipeline

```
Pipeline failure policy:

Agent 01 fails    → ABORT entire day. Log error. No trading.
Agent 02 fails    → ABORT. Quality filter is mandatory.
Agent 06 fails    → ABORT. Cannot trade without regime.
Agent 10 fails    → ABORT. Event blocks are safety-critical.
Agent 03/04/05 fail → SKIP that signal only. Others continue. Reduce conviction threshold to 0.70.
Agent 08/09 fail  → SKIP that signal. Reduce weight of missing agent to 0. Others reweighted.
Agent 11 fails    → USE last known IC weights. Log warning.
Agent 12 fails    → USE conservative liquidity multiplier of 0.60 for all stocks.
Agent 13 fails    → ABORT. Risk manager failure = no trading.
BOSS fails        → ABORT. Log full context for debugging.
Agent 14 fails    → ABORT. Trade decision cannot be logged — orphaned trade risk.
```

---

---

## 4. Error Handling & Retry Logic

### Per-Tool Failure Policy

```python
# yfinance — stale or missing data
def fetch_with_fallback(ticker: str, period: str) -> pd.DataFrame:
    for attempt in range(3):
        try:
            df = yf.Ticker(ticker).history(period=period)
            if df.empty:
                raise ValueError(f"Empty data for {ticker}")
            if (datetime.now() - df.index[-1].to_pydatetime()).days > 3:
                raise ValueError(f"Stale data for {ticker} — last date {df.index[-1]}")
            return df
        except Exception as e:
            logger.warning(f"yfinance attempt {attempt+1} failed for {ticker}: {e}")
            time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s
    logger.error(f"yfinance permanently failed for {ticker} — removing from watchlist today")
    return pd.DataFrame()  # empty = agent skips this ticker

# Screener CLI — timeout or parse error
def run_screener(query: str, timeout: int = 30) -> dict:
    for attempt in range(2):
        try:
            result = subprocess.run(["screener", "fetch", "--query", query],
                                     capture_output=True, timeout=timeout)
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning(f"Screener CLI timed out on attempt {attempt+1}")
            time.sleep(5)
    raise RuntimeError("Screener CLI failed after 2 attempts — aborting pipeline")

# Gemini API — malformed JSON response
def call_agent(system_prompt: str, user_input: str, schema: dict) -> dict:
    for attempt in range(3):
        try:
            response = gemini_client.generate_content(
                contents=user_input,
                system_instruction=system_prompt,
                generation_config={"response_mime_type": "application/json",
                                   "response_schema": schema,
                                   "temperature": 0.1}
            )
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.warning(f"Gemini returned invalid JSON on attempt {attempt+1}: {e}")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            time.sleep(5)
    raise RuntimeError(f"Gemini agent failed after 3 attempts")

# nseindiaapi — rate limit or NSE server down
def fetch_nse_data(fn, *args, **kwargs):
    for attempt in range(3):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"NSE API attempt {attempt+1} failed: {e}")
            time.sleep(10 * (attempt + 1))  # NSE blocks on rapid retry
    logger.error("NSE API permanently failed — using cached data from yesterday")
    return load_cached_nse_data()
```

---

### Data Validation Before Passing to Agents

```python
# Before any data goes into an agent prompt, validate it
def validate_price_data(df: pd.DataFrame, ticker: str) -> bool:
    if df.empty: return False
    if len(df) < 21: return False               # need at least 21 days for z-score
    if df['Close'].isnull().sum() > 5: return False   # too many missing prices
    if (df['Volume'] == 0).sum() > 3: return False    # suspicious zero volume days
    return True

# Context window size guard (Gemini 2.5 Pro: 1M tokens but keep agent payloads lean)
def check_payload_size(payload: dict, agent_name: str, max_chars: int = 50000):
    payload_str = json.dumps(payload)
    if len(payload_str) > max_chars:
        logger.warning(f"{agent_name} payload is {len(payload_str)} chars — trimming watchlist")
        # Trim to top 50 stocks by quality score if watchlist is huge
        payload['candidates'] = sorted(payload['candidates'],
                                        key=lambda x: x['quality_score'],
                                        reverse=True)[:50]
    return payload
```

---

### Logging Strategy

```
logs/
  pipeline_YYYY-MM-DD.log     # full run log per day
  errors_YYYY-MM-DD.log       # errors only
  trades_YYYY-MM-DD.log       # every trade decision (approved + rejected)
  agent_outputs/
    agent_01_YYYY-MM-DD.json  # raw output of each agent saved for debugging
    agent_02_YYYY-MM-DD.json
    boss_YYYY-MM-DD.json
    ...
```

Every agent's raw JSON output is saved to disk before being passed downstream. If BOSS makes a bad decision, you can replay any day by reading the saved agent outputs — no re-running needed.

---

---

## 5. Weekly P&L Report Format

Generated every Friday at 4:30 PM IST. Saved as `reports/week_YYYY-MM-DD.md`.

```markdown
# Weekly P&L Report — Week Ending 2025-03-07

## Portfolio Summary
| Metric | Value |
|---|---|
| Portfolio Value | ₹10,84,320 |
| Starting Value (Monday) | ₹10,61,200 |
| Week Return | +2.18% |
| Nifty 50 Week Return | +0.94% |
| Alpha Generated | +1.24% |
| Cash Balance | ₹4,92,100 (45.4%) |
| Open Positions | 5 |

## Cumulative Performance (Since Inception)
| Metric | Value | Target |
|---|---|---|
| Total Return | +8.43% | > Nifty |
| Nifty Return | +4.21% | — |
| Alpha | +4.22% | > +2%/month |
| Sharpe Ratio (63d) | 1.84 | > 1.5 |
| Calmar Ratio (63d) | 1.21 | > 1.0 |
| Max Drawdown | -3.8% | > -15% |
| Portfolio Beta | 0.68 | < 0.8 |

## Trade Activity This Week
| Metric | Value |
|---|---|
| Total Trades | 8 (5 buy, 3 sell) |
| Win Rate | 67% (4 of 6 closed) |
| Avg Win | +₹2,840 |
| Avg Loss | -₹1,120 |
| Win/Loss Ratio | 2.54 |
| Total Charges Paid | ₹892 |
| Charge Drag | 0.085% |

## Open Positions
| Ticker | Type | Entry Date | Entry Price | Current Price | Unrealized P&L | Weight |
|---|---|---|---|---|---|---|
| RELIANCE | MOMENTUM | 2025-03-03 | ₹1,286.67 | ₹1,318.40 | +₹1,206 (+2.47%) | 4.7% |
| HDFCBANK | PAIRS | 2025-03-04 | ₹1,642.10 | ₹1,671.80 | +₹1,188 (+1.81%) | 4.6% |
| TCS | EVENT_DRIVEN | 2025-03-05 | ₹3,812.45 | ₹3,869.20 | +₹1,135 (+1.49%) | 5.3% |
| SUNPHARMA | MOMENTUM | 2025-03-05 | ₹1,724.30 | ₹1,698.10 | -₹786 (-1.52%) | 4.7% |
| NESTLEIND | QUALITY | 2025-03-06 | ₹2,241.80 | ₹2,261.50 | +₹394 (+0.88%) | 3.2% |

## Closed Trades This Week
| Ticker | Type | Entry | Exit | P&L | Hold Days |
|---|---|---|---|---|---|
| INFY | PAIRS | ₹1,812.30 | ₹1,858.90 | +₹2,330 (+2.57%) | 4 |
| AXISBANK | MOMENTUM | ₹1,124.50 | ₹1,156.20 | +₹3,170 (+2.82%) | 6 |
| WIPRO | MEAN_REVERSION | ₹542.80 | ₹531.60 | -₹1,120 (-2.06%) | 2 |
| LT | EVENT_DRIVEN | ₹3,621.00 | ₹3,695.40 | +₹2,976 (+2.05%) | 5 |
| ONGC | MOMENTUM | ₹271.40 | ₹268.90 | -₹750 (-0.92%) | 3 |
| HDFC | QUALITY | ₹1,682.10 | ₹1,741.30 | +₹2,958 (+3.52%) | 8 |

## Regime History This Week
| Date | Regime | VIX | FII Flow |
|---|---|---|---|
| Mon 2025-03-03 | NEUTRAL | 15.8 | POSITIVE |
| Tue 2025-03-04 | NEUTRAL | 16.2 | POSITIVE |
| Wed 2025-03-05 | NEUTRAL | 17.1 | NEUTRAL |
| Thu 2025-03-06 | CAUTION | 21.4 | NEGATIVE |
| Fri 2025-03-07 | NEUTRAL | 18.9 | NEUTRAL |

## Agent IC Performance (Trailing 63d)
| Agent | IC | Weight | Status |
|---|---|---|---|
| Agent 03 Momentum | 0.071 | 33% | ACTIVE |
| Agent 04 Mean Reversion | 0.058 | 27% | ACTIVE |
| Agent 05 Pairs | 0.083 | 40% | ACTIVE |

## Next Week Watch
Stocks on BOSS watchlist (conviction 0.40–0.60 — waiting for confirmation):
- BAJFINANCE (conviction 0.54) — momentum building, event block clears Mon
- MARUTI (conviction 0.48) — sector rotation into auto improving
- BHARTIARTL (conviction 0.43) — FII accumulation, waiting for breakout volume
```

---

---

## 6. File & Folder Structure

```
quant_trading/
│
├── main.py                     # entry point — starts APScheduler
├── orchestrator.py             # pipeline runner — calls agents in order
├── config.py                   # constants: portfolio size, thresholds, tickers
│
├── agents/
│   ├── agent_01_universe.py
│   ├── agent_02_quality.py
│   ├── agent_03_momentum.py
│   ├── agent_04_reversion.py
│   ├── agent_05_pairs.py
│   ├── agent_06_macro.py
│   ├── agent_07_sector.py
│   ├── agent_08_ownership.py
│   ├── agent_09_sentiment.py
│   ├── agent_10_events.py
│   ├── agent_11_backtester.py
│   ├── agent_12_liquidity.py
│   ├── agent_13_risk.py
│   ├── agent_14_execution.py
│   └── boss.py
│
├── data/
│   ├── quant_trading.db        # SQLite — all 5 tables
│   ├── nse_holidays_2025.json
│   └── validated_pairs.json    # cointegration results, revalidated Sunday
│
├── tools/
│   ├── yfinance_wrapper.py     # fetch with retry + validation
│   ├── screener_wrapper.py     # CLI subprocess wrapper
│   ├── nse_wrapper.py          # nseindiaapi wrapper with cache
│   └── gemini_wrapper.py       # API call with schema enforcement + retry
│
├── logs/
│   ├── pipeline_YYYY-MM-DD.log
│   ├── errors_YYYY-MM-DD.log
│   └── agent_outputs/          # raw JSON per agent per day
│
└── reports/
    └── week_YYYY-MM-DD.md      # weekly P&L reports
```

---

---

## Ready to Code

All six missing pieces are now planned:

| # | Piece | Status |
|---|---|---|
| 1 | Database schema | ✅ 5 tables defined |
| 2 | Orchestrator data flow | ✅ Full JSON contract per step |
| 3 | Scheduler design | ✅ APScheduler + holiday list |
| 4 | Error handling & retry | ✅ Per-tool policy + validation |
| 5 | Market holiday handling | ✅ 2025 NSE holiday list + `is_market_open()` |
| 6 | Weekly P&L report | ✅ Full format with all metrics |
