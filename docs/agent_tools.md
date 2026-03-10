# Agent Tool Assignments
### Every External Tool × Every Agent — Full Reference

---

## The 5 Tool Categories

| # | Tool | What It Is | Cost |
|---|---|---|---|
| 1 | **Screener CLI** | `github.com/vedanth-jadhav/screener` — your own CLI for screener.in data | Free |
| 2 | **yfinance** | Python library for NSE/BSE price, volume, OHLCV, VIX, Nifty index data | Free |
| 3 | **nseindiaapi** | Unofficial NSE endpoint wrapper — bulk deals, FII/DII flows, event calendar, circulars | Free |
| 4 | **Exa MCP** | Semantic web search tool via MCP — news, SEBI filings, corporate announcements, order wins | Free (MCP) |
| 5 | **Native Search Tool** | Built-in search — fallback for macro news, RBI policy, anything Exa MCP misses | Free |

---

---

## ORCHESTRATOR

```
Tools: NONE
```

The orchestrator is pure Python — no AI tool calls. It calls agents in sequence, passes JSON payloads, validates schemas, writes to trade log. It uses `yfinance` and `nseindiaapi` directly in Python code to fetch data before passing it into agent prompts. It does not make LLM tool calls itself.

---

---

## AGENT 01 — Universe Builder

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **Screener CLI** | Pull full stock universe with fundamental filters | `screener fetch --query "market_cap > 500 AND debt_to_equity < 2"` |
| **Screener CLI** | Promoter pledging data for all stocks | `screener fetch --field promoter_pledging` |
| **Screener CLI** | Operating cash flow (CFO) for hard reject filter | `screener fetch --field cfo` |
| **nseindiaapi** | ASM / GSM surveillance list — hard reject | `nse.get_asm_list()` + `nse.get_gsm_list()` |
| **nseindiaapi** | Circuit breaker history — stocks hitting upper/lower circuit last 5 days | `nse.get_circuit_breaker_list()` |

### Tools NOT Given
- yfinance — Agent 01 only builds the universe, no price data needed
- Exa MCP — no news needed at this stage
- Native search — not needed

---

---

## AGENT 02 — Quality Factor Scorer

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **Screener CLI** | All 9 Piotroski F-Score inputs (ROA, CFO, gross margin, asset turnover, current ratio, D/E, equity dilution) | `screener fetch --fields roa,cfo,gross_margin,asset_turnover,current_ratio,de_ratio` |
| **Screener CLI** | EBIT and Enterprise Value for Greenblatt EY | `screener fetch --fields ebit,enterprise_value` |
| **Screener CLI** | Net fixed assets + working capital for ROCE | `screener fetch --fields net_fixed_assets,working_capital` |
| **Screener CLI** | Promoter holding % current + previous quarter | `screener fetch --fields promoter_holding,promoter_holding_prev` |
| **Screener CLI** | FII holding % current + previous 2 quarters | `screener fetch --fields fii_holding,fii_holding_q1,fii_holding_q2` |
| **Screener CLI** | DII holding % current + previous 2 quarters | `screener fetch --fields dii_holding,dii_holding_q1,dii_holding_q2` |

### Tools NOT Given
- yfinance — no price data needed for pure fundamental scoring
- nseindiaapi — ownership data comes from screener
- Exa MCP — no news needed
- Native search — not needed

---

---

## AGENT 03 — Momentum Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | 252 trading days OHLCV for skip-month momentum | `yf.Ticker("X.NS").history(period="2y")` |
| **yfinance** | 63-day rolling volume for ADV comparison | Same history call, use `Volume` column |
| **yfinance** | Nifty 50 price history for relative strength | `yf.Ticker("^NSEI").history(period="3mo")` |
| **yfinance** | India VIX current value for momentum dampening | `yf.Ticker("^INDIAVIX").fast_info` |
| **yfinance** | 52-week high/low for breakout proximity signal | `.info['fiftyTwoWeekHigh']` + `.info['fiftyTwoWeekLow']` |

### Tools NOT Given
- Screener CLI — no fundamentals needed for pure price momentum
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## AGENT 04 — Mean Reversion Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | 60-day OHLCV for z-score and Bollinger band computation | `yf.Ticker("X.NS").history(period="3mo")` |
| **yfinance** | Today's intraday open/high/low/close for Alpha#101 | `yf.Ticker("X.NS").history(period="1d", interval="1d")` |
| **yfinance** | 20-day ADV for volume confirmation of Alpha#101 | Same 3mo history, `Volume` column |

### Tools NOT Given
- Screener CLI — not needed
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## AGENT 05 — Pairs / StatArb Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | 126-day price history for both legs of every pair for OLS regression (alpha, beta) | `yf.Ticker("HDFCBANK.NS").history(period="6mo")` |
| **yfinance** | 60-day spread history for Z-score mean and std | Computed from above history |
| **yfinance** | Current price of both legs for live spread computation | `.fast_info['last_price']` |

### Tools NOT Given
- Screener CLI — pairs are price-only, no fundamentals needed
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

### Note
Cointegration revalidation (ADF test + half-life recompute) runs **every Sunday** via a separate standalone script. Agent 05 only consumes pre-validated pairs — it does not rerun cointegration tests during market hours.

---

---

## AGENT 06 — Macro & Regime Filter

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | India VIX current value + 20-day history | `yf.Ticker("^INDIAVIX").history(period="1mo")` |
| **yfinance** | Nifty 50 current price + 200-day SMA | `yf.Ticker("^NSEI").history(period="1y")` |
| **yfinance** | Nifty 500 constituent prices for breadth calculation | Batch fetch all 500 stocks `.fast_info` |
| **nseindiaapi** | FII net flow daily (last 5 trading days) | `nse.get_fii_dii_data(segment="FII")` |
| **Native Search Tool** | RBI policy announcements, macro news, rate decisions | `search("RBI repo rate decision India today")` |
| **Native Search Tool** | Any breaking macro event (budget, GDP data) | `search("India macro news today")` |

### Tools NOT Given
- Screener CLI — no stock-level data needed
- Exa MCP — native search sufficient for macro; Exa's semantic edge not needed here

---

---

## AGENT 07 — Sector Rotation Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | All 14 NSE sector index OHLCV — 126-day history | See sector tickers below |

### Sector Index Tickers (yfinance)
```
^CNXIT       → IT
^NSEBANK     → Bank Nifty (Private + PSU combined)
^CNXPSUBNK   → PSU Bank
^CNXFMCG     → FMCG
^CNXPHARMA   → Pharma
^CNXAUTO     → Auto
^CNXENERGY   → Energy
^CNXINFRA    → Infrastructure
^CNXMETAL    → Metals & Mining
^CNXREALTY   → Realty
^CNXMEDIA    → Media
^CNXCHEM     → Chemicals (Nifty Chemicals)
^CNXCAPGOODS → Capital Goods
^CNXFINANCE  → Financial Services
```

### Tools NOT Given
- Screener CLI — sector rotation is pure price-based
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## AGENT 08 — Ownership & Flow Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **Screener CLI** | FII holding % current + previous quarter (delta) | `screener fetch --fields fii_holding,fii_holding_prev` |
| **Screener CLI** | DII holding % current + previous quarter (delta) | `screener fetch --fields dii_holding,dii_holding_prev` |
| **Screener CLI** | Promoter holding % current + previous (delta + pledging change) | `screener fetch --fields promoter_holding,promoter_pledging` |
| **nseindiaapi** | Bulk deals — last 5 trading days per stock | `nse.get_bulk_deals(symbol="RELIANCE")` |
| **nseindiaapi** | Block deals — last 5 trading days | `nse.get_block_deals(symbol="RELIANCE")` |

### Tools NOT Given
- yfinance — no price data needed
- Exa MCP — not needed
- Native search — not needed

---

---

## AGENT 09 — Sentiment & News Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **Exa MCP** | Company-specific news — order wins, earnings beat, expansions | `exa.search("<COMPANY> order win contract 2025")` |
| **Exa MCP** | Negative signals — SEBI action, fraud, management exits | `exa.search("<COMPANY> SEBI investigation fraud resignation")` |
| **Exa MCP** | Buyback and promoter buy news | `exa.search("<COMPANY> buyback promoter purchase 2025")` |
| **Exa MCP** | Rating upgrades/downgrades | `exa.search("<COMPANY> credit rating upgrade downgrade")` |
| **Native Search Tool** | Fallback when Exa returns zero results | `search("<TICKER> NSE news")` |

### Query Discipline (token + rate limit management)
```
Run Exa queries only for top 20 stocks by quality score from Agent 02.
Skip Exa entirely for stocks with no fresh signals from Agents 03/04.
Max 4 Exa queries per stock per day.
Cache results — do not re-query same stock within 6 hours.
```

### Tools NOT Given
- Screener CLI — not needed
- yfinance — not needed
- nseindiaapi — not needed

---

---

## AGENT 10 — Event & Catalyst Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **nseindiaapi** | Earnings calendar — results date for all watchlist stocks | `nse.get_event_calendar()` |
| **nseindiaapi** | Ex-dividend dates, board meeting dates | `nse.get_corporate_actions(symbol="X")` |
| **nseindiaapi** | Latest NSE circulars — SEBI actions, trading halts | `nse.get_latest_circular()` |
| **Exa MCP** | SEBI investigation news not yet in NSE circulars | `exa.search("<COMPANY> SEBI investigation 2025")` |
| **Exa MCP** | Auditor resignation, whistleblower filings | `exa.search("<COMPANY> auditor resignation whistleblower")` |
| **Exa MCP** | Post-earnings analyst estimate for PEAD | `exa.search("<COMPANY> Q results EPS estimate actual beat miss")` |
| **Exa MCP** | Order wins, government contracts | `exa.search("<COMPANY> order win government contract 2025")` |
| **Native Search Tool** | Fallback for any blocked event Exa misses | `search("<COMPANY> board meeting announcement")` |

### Tools NOT Given
- Screener CLI — not needed
- yfinance — not needed

---

---

## AGENT 11 — Backtester & IC Validator

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | Historical OHLCV for IC computation (forward returns at t+5, t+10) | `yf.Ticker("X.NS").history(period="1y")` |

### Note
Agent 11 is the most compute-intensive agent. It reads the **trade log database** (internal, not an external tool) to get historical signal scores, then fetches realized returns from yfinance to compute IC. No news, no fundamentals — pure price math.

### Tools NOT Given
- Screener CLI — not needed
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## AGENT 12 — Liquidity & Microstructure Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | 21-day OHLCV + volume for Amihud illiquidity ratio | `yf.Ticker("X.NS").history(period="1mo")` |
| **yfinance** | Today's volume vs ADV for impact cost estimate | `.fast_info['three_month_average_volume']` |
| **yfinance** | Market cap for impact cost tier classification | `.fast_info['market_cap']` |

### Tools NOT Given
- Screener CLI — ADV and microstructure are price/volume, not fundamentals
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## AGENT 13 — Risk Manager

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | Live price of all open positions (stop-loss checks at 9:25 AM) | `yf.Ticker("X.NS").fast_info['last_price']` |
| **yfinance** | 63-day daily returns for portfolio beta calculation | `yf.Ticker("X.NS").history(period="3mo")` |
| **yfinance** | Nifty 50 63-day returns for beta denominator | `yf.Ticker("^NSEI").history(period="3mo")` |
| **yfinance** | 63-day covariance matrix for VaR | Computed from history of all open positions |

### Internal Data (not external tools)
- Trade log (SQLite) — all open positions, entry prices, stop levels
- Portfolio state (in-memory) — cash balance, deployed capital, sector exposures

### Tools NOT Given
- Screener CLI — not needed at risk check time
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## BOSS — Portfolio Manager

### Tools Assigned
```
NONE — BOSS receives pre-computed data only
```

BOSS does **not** call any external tools directly. It receives the fully assembled payload from the orchestrator containing all 12 agent outputs as structured JSON, runs conviction aggregation and Kelly sizing on that data, and outputs a trade decision.

This is intentional — BOSS must be **deterministic and fast**. No tool calls in BOSS's context means no latency, no API failures, no hallucinated lookups at the most critical decision point.

All data BOSS needs is already computed and passed in by the orchestrator.

---

---

## AGENT 14 — Execution Analyst

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | Current market price for simulated fill price | `yf.Ticker("X.NS").fast_info['last_price']` |
| **yfinance** | Check if market is open (trading hours validation) | `yf.Ticker("^NSEI").fast_info['exchange']` — cross-check time |

### Tools NOT Given
- Screener CLI — not needed
- nseindiaapi — not needed
- Exa MCP — not needed
- Native search — not needed

---

---

## P&L Tracking Agent (End of Day)

### Tools Assigned
| Tool | Used For | Specific Call |
|---|---|---|
| **yfinance** | Current price of all open positions for unrealized P&L | `yf.Ticker("X.NS").fast_info['last_price']` |
| **yfinance** | Nifty 50 current value for benchmark comparison | `yf.Ticker("^NSEI").fast_info['last_price']` |

### Internal Data
- Trade log (SQLite) — all buy/sell records with charges and fill prices
- Portfolio state — cash balance, all open positions

---

---

## Tool Assignment Matrix — One View

| Agent | Screener CLI | yfinance | nseindiaapi | Exa MCP | Native Search |
|---|:---:|:---:|:---:|:---:|:---:|
| Agent 01 — Universe Builder | ✅ | ❌ | ✅ | ❌ | ❌ |
| Agent 02 — Quality Scorer | ✅ | ❌ | ❌ | ❌ | ❌ |
| Agent 03 — Momentum | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent 04 — Mean Reversion | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent 05 — Pairs / StatArb | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent 06 — Macro & Regime | ❌ | ✅ | ✅ | ❌ | ✅ |
| Agent 07 — Sector Rotation | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent 08 — Ownership & Flow | ✅ | ❌ | ✅ | ❌ | ❌ |
| Agent 09 — Sentiment & News | ❌ | ❌ | ❌ | ✅ | ✅ |
| Agent 10 — Event & Catalyst | ❌ | ❌ | ✅ | ✅ | ✅ |
| Agent 11 — Backtester & IC | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent 12 — Liquidity | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent 13 — Risk Manager | ❌ | ✅ | ❌ | ❌ | ❌ |
| BOSS | ❌ | ❌ | ❌ | ❌ | ❌ |
| Agent 14 — Execution | ❌ | ✅ | ❌ | ❌ | ❌ |
| P&L Tracking Agent | ❌ | ✅ | ❌ | ❌ | ❌ |

---

---

## Installation

```bash
# 1. Your screener CLI
# Already installed — github.com/vedanth-jadhav/screener

# 2. yfinance
pip install yfinance

# 3. nseindiaapi
pip install nseindiaapi

# 4. Exa MCP
# Configured via MCP settings — no pip install needed

# 5. Native search tool
# Built-in — no install needed
```

---

## Key Principles Applied

**Minimal tool access per agent** — every agent only has the tools it actually needs. An agent with 5 tools it doesn't use is a hallucination risk and a latency cost.

**BOSS has zero tools** — the most important decision point in the system is kept pure. No live lookups, no API failures, no surprises at conviction aggregation time.

**Exa MCP is only for Agents 09 and 10** — the two agents that need semantic news search. Every other agent works with structured data from Screener CLI, yfinance, or nseindiaapi — no natural language search needed.

**nseindiaapi for NSE-native data only** — bulk deals, FII flows, event calendar, ASM lists. These are not available anywhere else for free with this reliability.

**yfinance covers the entire price layer** — 10 out of 16 agents use it. It is the backbone of the system.
