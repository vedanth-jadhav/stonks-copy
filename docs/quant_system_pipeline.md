**QUANT TRADING SYSTEM**

Full Architecture & Pipeline

**Indian Equity Markets — NSE Focus**

Portfolio: ₹10,00,000 | Mock Paper Trading | Benchmark: Nifty 50

# **0\. India Market Constraints & Why They Matter**

Every formula in this document is adapted for these hard realities of NSE/BSE trading. Ignoring them is why Western quant models fail in India.

| **Constraint** | **Impact on Strategy** | **How We Handle It** |
| --- | --- | --- |
| T+1 Settlement | Capital deployed today is locked until tomorrow. You cannot reuse proceeds same-day for delivery trades. | Always hold 35% cash. Track settlement dates per position in the execution layer. |
| Circuit Breakers (5/10/20%) | If a stock hits its circuit, you literally cannot exit. Mean reversion signals may point at a stock you physically can't sell. | Circuit risk filter: reject any stock that has hit upper/lower circuit in last 5 days from active watchlist. |
| No Short Selling (Delivery) | Stat arb pairs and mean reversion short legs are unavailable for delivery. Only futures/options allow shorting. | System is long-only delivery. All 'short' signals are treated as 'do not hold / exit existing position'. |
| ASM / GSM Lists | SEBI puts suspicious/manipulated stocks on Additional Surveillance Measure lists. Margins spike, liquidity collapses. | Hard reject: any stock on ASM/GSM list is blacklisted from the universe entirely. |
| Promoter Pledging | Pledged shares can be force-sold by lenders. Sudden supply overhang can crater price. | Reject any stock with promoter pledging > 30%. Reduce weight for 15-30% pledging. |
| Illiquidity (Mid/Small Cap) | India has the highest Amihud illiquidity ratio globally. Impact cost on small caps can exceed 0.5%. | Liquidity filter: min 50 Cr average daily volume (ADV) over 20 days. Position size capped at 2% of 20-day ADV. |
| Pre-Open Auction (9:00-9:15 AM) | Price discovery happens in auction. First 15 min post-open are noise-dominated. | Execution window: 9:30 AM to 3:00 PM only. Avoid first and last 15 min. |
| FII Flow Dominance | FII inflows/outflows move Nifty 50 systematically. Ignoring macro FII flow causes beta exposure. | Macro agent tracks daily FII net flow. Negative FII flow for 3+ days = reduce deployment to 40%. |
| India VIX | India VIX >20 = elevated fear. Momentum strategies crash in high-VIX regimes. | VIX regime filter: >20 = momentum weight halved. >28 = only quality/low-vol stocks allowed. >35 = cash-only. |
| Earnings Seasonality | Q1 results: July-Aug. Q2: Oct-Nov. Q3: Jan-Feb. Q4: Apr-May. Earnings drift is real but news is binary. | Event agent flags 15-day pre and post earnings windows. No new position entry in the 5 days before results. |

# **1\. Firm Structure — 14 Agents + BOSS**

The firm operates as a multi-agent quant pipeline. Every trade idea must survive a gauntlet of specialists before BOSS approves execution. No single agent has trade authority.

| **Agent** | **Role** | **Primary Data Source** | **Output** |
| --- | --- | --- | --- |
| BOSS | Portfolio Manager — final capital allocation, Kelly sizing, veto power | All agent outputs | Trade approval + position size |
| Agent 01 | Universe Builder & Fundamental Filter | Screener.in CLI | Clean investable watchlist |
| Agent 02 | Quality Factor Scorer | Screener.in CLI | Quality score per stock (0-100) |
| Agent 03 | Momentum Analyst | Price/volume data | Momentum signal (-1 to +1) |
| Agent 04 | Mean Reversion Analyst | Price/volume data | MR z-score + entry zone |
| Agent 05 | Pairs / StatArb Analyst | Price data (cointegrated pairs) | Spread z-score, pair signals |
| Agent 06 | Macro & Regime Filter | India VIX, FII flows, Nifty trend | Market regime (Bull/Bear/Neutral) |
| Agent 07 | Sector Rotation Analyst | Sector index returns | Hot/cold sector map |
| Agent 08 | Ownership & Flow Analyst | NSE bulk deals, FII/DII data | Smart money signal per stock |
| Agent 09 | Sentiment & News Analyst | Exa web search | Sentiment score (-1 to +1) |
| Agent 10 | Event & Catalyst Analyst | Earnings calendar, SEBI filings | Event risk flag + catalyst flag |
| Agent 11 | Backtester & IC Validator | Historical price data | Signal IC, win rate, Sharpe |
| Agent 12 | Liquidity & Microstructure | OHLCV, bid-ask estimates | Liquidity score, impact cost |
| Agent 13 | Risk Manager | Live portfolio state | VaR, MDD, beta, stop alerts |
| Agent 14 | Execution Analyst | Price + cost model | Net entry/exit price after all charges |

# **2\. Trade Approval Pipeline**

Every trade must pass through all stages sequentially. A hard STOP at any stage kills the trade. There are no exceptions.

### **Stage 1 — Universe Construction (Agent 01)**

Runs at market open. Builds the day's investable universe from screener.in.

HARD REJECTS (any one = remove from universe):

\- On ASM/GSM surveillance list

\- Market cap < 500 Cr

\- Avg daily volume (20d) < 50 Cr

\- Promoter pledging > 30%

\- Listed < 3 years (insufficient history)

\- Debt/Equity > 2.0 (except BFSI sector where D/E < 8)

\- Hit upper/lower circuit in last 5 trading days

\- Negative CFO for 2 consecutive years

### **Stage 2 — Quality + Fundamental Score (Agent 02)**

Piotroski F-Score + India-adjusted Greenblatt on the surviving universe.

Piotroski F-Score (binary, 0 or 1 each, max = 9):

Profitability:

P1 = 1 if ROA > 0

P2 = 1 if CFO > 0

P3 = 1 if delta_ROA > 0 (YoY improvement)

P4 = 1 if CFO/Total_Assets > ROA (accrual quality)

Leverage:

P5 = 1 if delta_LongTermDebt_ratio < 0 (debt going down)

P6 = 1 if delta_Current_Ratio > 0

P7 = 1 if no new equity dilution in past year

Efficiency:

P8 = 1 if delta_Gross_Margin > 0

P9 = 1 if delta_Asset_Turnover > 0

Threshold: F-Score >= 6 to remain in universe

Greenblatt Magic Formula (rank within F-Score >= 6 universe):

EY = EBIT / EV (Earnings Yield — higher is better)

ROCE = EBIT / Capital_Employed (Return on Capital — higher is better)

Magic_Rank = Rank(EY) + Rank(ROCE)

Final_Score = normalize(Magic_Rank) to 0-100

India-specific additions to quality score:

\+ 10 pts if promoter_holding > 60%

\+ 5 pts if promoter_holding increased QoQ

\- 15 pts if promoter_pledging between 15-30%

\- 10 pts if FII_holding decreased for 2 consecutive quarters

\+ 8 pts if DII_holding increased for 2 consecutive quarters

### **Stage 3 — Regime Check (Agent 06)**

If the macro environment doesn't support deployment, no new longs are initiated regardless of stock-level signals.

India VIX Regime:

VIX < 14 : Bull regime — full deployment allowed (up to 65%)

14 <= VIX < 20 : Neutral regime — deployment up to 50%

20 <= VIX < 28 : Caution regime — deployment up to 35%, momentum signals halved

28 <= VIX < 35 : Bear regime — only Quality stocks (F-Score 8-9), max 20%

VIX >= 35 : Crisis regime — 100% cash, no new positions

Nifty 50 Trend Filter (200-day SMA):

Nifty > SMA_200 : Uptrend — longs allowed

Nifty < SMA_200 : Downtrend — only high-conviction Quality plays, size halved

FII Net Flow Signal (daily NSE data):

FII_signal = sign(sum(FII_net_flow, last 5 days))

FII buying (+1) : supportive — normal sizing

FII selling (-1) : headwind — reduce new position sizes by 20%

### **Stage 4 — Signal Generation (Agents 03, 04, 05, 07, 08, 09)**

Each signal agent scores stocks from -1 (strong sell/avoid) to +1 (strong buy). These feed into the conviction aggregation.

### **Stage 5 — Event Risk Gate (Agent 10)**

Hard blocks on entries near high-uncertainty events.

BLOCK new entry if:

\- Earnings results within 5 trading days (pre-announcement noise)

\- Board meeting for stock split / rights issue within 3 days

\- SEBI investigation news in last 30 days (via Exa search)

\- Ex-dividend date within 2 days (artificial price drop)

ALLOW (catalyst present) if:

\- Earnings beat > 10% vs estimate in last quarter (momentum continuation)

\- Management buyback announcement (bullish signal)

\- Order win / capacity expansion news (Exa)

### **Stage 6 — Backtested IC Validation (Agent 11)**

No signal fires in production unless it has demonstrated predictive power historically.

Information Coefficient:

IC = Pearson_corr(signal_score_t, forward_return_{t+n})

Threshold: IC > 0.04 over trailing 63 days (3 months)

IC < 0.04 : signal weight = 0 (dormant)

IC 0.04-0.08: signal weight = 0.5x

IC > 0.08 : signal weight = 1.0x

IC Decay (how fast the signal goes stale):

IC(lag) = IC_0 \* exp(-lambda \* lag)

lambda < 0.1 : slow decay, signal valid for days

lambda > 0.3 : fast decay, signal is same-day only

### **Stage 7 — Conviction Aggregation (BOSS)**

agent_weight_i = rolling_IC_i / sum(rolling_IC_j for all j)

Conviction = sum(agent_weight_i \* signal_score_i)

where signal_score_i in \[-1, +1\]

Trade fires ONLY if:

Conviction > 0.60 AND

Risk Manager GREEN AND

At least 6 of 9 signal agents are positive (>0)

### **Stage 8 — Kelly Position Sizing (BOSS)**

Full Kelly: f\* = (p\*b - q) / b

p = historical win rate for this signal class

q = 1 - p

b = avg_win / avg_loss (reward-to-risk ratio)

Use HALF-KELLY always: position_fraction = f\* / 2

Hard caps (override Kelly):

Max single position = 15% of portfolio

Max sector exposure = 30% of portfolio

Max total deployed = 65% of portfolio (35% minimum cash for T+1)

Shares to buy:

Risk_amount = portfolio_value \* position_fraction

Shares = floor(Risk_amount / entry_price)

(round down — never up — to avoid breaching cash limit)

### **Stage 9 — Execution & Cost (Agent 14)**

Transaction costs (Delivery — Zerodha):

STT_buy = 0.001 \* trade_value

STT_sell = 0.001 \* trade_value

Exchange = 0.0000335 \* trade_value (each side)

SEBI = 0.000001 \* trade_value (each side)

Stamp_buy = 0.00015 \* trade_value (buy only)

GST = 0.18 \* (exchange + SEBI) (each side)

Total round-trip cost function:

C(v) = v \* (0.001 + 0.001 + 2\*0.0000335 + 2\*0.000001 + 0.00015 + 2\*0.18\*(0.0000335+0.000001))

C(v) ≈ v \* 0.002285 (approximately 0.23%)

Net entry price = market_price \* (1 + 0.001 + 0.0000335 + 0.000001 + 0.00015 + 0.18\*(0.0000335+0.000001))

Net exit price = market_price \* (1 - 0.001 - 0.0000335 - 0.000001 - 0.18\*(0.0000335+0.000001))

Liquidity/impact cost (added on top):

Nifty 50 stocks : +0.05% slippage estimate

Nifty 500 stocks: +0.15% slippage estimate

Mid/Small caps : +0.30% slippage estimate

Execution window: 9:30 AM - 3:00 PM IST only

Avoid 9:15-9:30 AM (post-auction noise)

Avoid 3:00-3:30 PM (institutional window dressing)

# **3\. Signal Formulas by Agent**

## **Agent 03 — Momentum Analyst**

Cross-sectional momentum adapted for India. Skip-month is mandatory — 1-month reversal dominates in India, raw 252-day momentum without skip causes alpha cancellation.

**3.1 Cross-Sectional Momentum (Primary Signal)**

\# Skip-month momentum (12-1 month):

raw_mom(i) = (P_{t-21} - P_{t-252}) / P_{t-252}

\# Volatility-adjusted (Adaptive Momentum):

mom_adj(i) = raw_mom(i) / rolling_std(returns, 63)

\# Cross-sectional rank across universe:

mom_rank(i) = percentile_rank(mom_adj(i)) in \[0, 1\]

\# Signal output (mapped to -1 to +1):

mom_signal(i) = 2 \* mom_rank(i) - 1

\# Momentum crash protection (critical for India):

if VIX > 20: mom_signal = mom_signal \* 0.5

if VIX > 28: mom_signal = 0 (switch off momentum entirely)

**3.2 Relative Strength vs Nifty (India-specific)**

RS(i) = (P_i / P_i_{t-63}) / (Nifty / Nifty_{t-63})

RS_signal(i) = 1 if RS > 1.10 else (-1 if RS < 0.90 else 0)

**3.3 WorldQuant Alpha#1 (Volume-Momentum, adapted)**

\# Rank by volume-adjusted price change:

alpha1(i) = -1 \* correlation(rank(delta(log(volume), 1)), rank((close - open) / open), 6)

\# Negatively ranked: stocks with volume surge on up-days rank lower (mean reversion view)

**3.4 52-Week High Proximity Signal**

proximity_52w(i) = (P_t - P_52w_low) / (P_52w_high - P_52w_low)

\# Breakout signal: stock at > 90% of 52w range with volume > 1.5x 20d avg

breakout(i) = 1 if proximity_52w > 0.90 AND volume > 1.5 \* adv20 else 0

## **Agent 04 — Mean Reversion Analyst**

**4.1 Z-Score Mean Reversion**

Z(i, t) = (P_t - EMA(P, 20)) / rolling_std(P, 20)

Entry long: Z &lt; -2.0 AND Z &gt; -3.5 (oversold but not broken)

Exit long: Z > -0.3 OR Z > 1.5 (reverted to mean)

Hard stop: Z < -3.5 (trending down, not mean-reverting — exit)

**4.2 Bollinger Band Width (Volatility Contraction Signal)**

BB_upper = SMA(20) + 2 \* std(20)

BB_lower = SMA(20) - 2 \* std(20)

BB_width = (BB_upper - BB_lower) / SMA(20)

\# Low BB_width = compression = impending breakout

compression_signal = 1 if BB_width < percentile(BB_width_60d, 10) else 0

**4.3 WorldQuant Alpha#4 (Rank-based Mean Reversion)**

alpha4(i) = -1 \* Ts_Rank(rank(low), 9)

\# Stocks ranked low on recent low prices are expected to revert upward

**4.4 WorldQuant Alpha#101 (Delay-1 Intraday Momentum)**

alpha101(i) = (close - open) / ((high - low) + 0.001)

\# If stock ran up intraday strongly: go long next day (continuation)

\# India adaptation: use only when volume > 1.3x ADV20 to confirm conviction

## **Agent 05 — Pairs / Statistical Arbitrage Analyst**

Long-only constraint means we can only exploit the LONG leg of pairs. When spread is extreme and our stock is the cheap leg, we enter long. We do not short the expensive leg.

**5.1 Cointegration Test (Engle-Granger)**

Step 1: OLS regression

Y_t = alpha + beta \* X_t + epsilon_t

Step 2: ADF test on residuals

H0: residuals are non-stationary (no cointegration)

ACCEPT pair if ADF p-value < 0.05

Step 3: Half-life of mean reversion

delta_epsilon_t = phi \* epsilon_{t-1} + noise

half_life = -log(2) / log(1 + phi)

ACCEPT pair if 3 <= half_life <= 20 days

(too short = noise, too long = capital tied up)

**5.2 Spread Z-Score**

spread_t = log(P_Y) - beta \* log(P_X) - alpha

Z_spread = (spread_t - mean(spread, 60)) / std(spread, 60)

Entry (long the cheap leg): Z_spread < -2.0

Exit: Z_spread > -0.3

Stop: Z_spread < -3.5 (cointegration breaking)

**5.3 Validated India Pairs (sector-constrained)**

| **Pair** | **Sector** | **Typical Half-Life** | **Notes** |
| --- | --- | --- | --- |
| HDFCBANK / ICICIBANK | Private Banking | 4-8 days | Most liquid pair on NSE, tight bid-ask |
| TCS / INFY | IT Services | 5-10 days | Both USD-revenue dependent, macro correlated |
| HINDUNILVR / DABUR | FMCG | 7-15 days | Rural consumption proxy pair |
| COALINDIA / NTPC | Energy | 5-12 days | Power sector input-output pair |
| ONGC / BPCL | Oil & Gas | 4-9 days | Upstream/downstream oil pair |
| AXISBANK / KOTAKBANK | Private Banking | 4-8 days | Mid-large private bank pair |
| SUNPHARMA / DRREDDY | Pharma | 6-14 days | Export pharma pair, USD correlated |

## **Agent 06 — Macro & Regime Filter**

**6.1 India VIX Regime Model**

Regime classification (computed at 9:20 AM daily):

if VIX < 14: regime = BULL | max_deploy = 0.65

elif VIX < 20: regime = NEUTRAL | max_deploy = 0.50

elif VIX < 28: regime = CAUTION | max_deploy = 0.35

elif VIX < 35: regime = BEAR | max_deploy = 0.20

else: regime = CRISIS | max_deploy = 0.00

**6.2 Hidden Markov Model for Regime Detection (Advanced)**

\# Two-state HMM on Nifty daily returns

State 0 = Low-vol trending (Bull)

State 1 = High-vol mean-reverting (Bear/Sideways)

Features: \[daily_return, abs(daily_return), log(volume_ratio)\]

Transition matrix updated weekly on rolling 252-day window

P(state | data) used to blend momentum vs mean-reversion weights:

momentum_weight = P(State 0)

reversion_weight = P(State 1)

**6.3 Nifty Breadth Indicator**

\# Percentage of Nifty 500 stocks above their 50-day SMA

breadth = count(P_i > SMA50_i) / 500

breadth > 0.70 : strong market — full deployment

breadth 0.50-0.70 : moderate — 80% deployment

breadth 0.35-0.50 : weak — 50% deployment

breadth < 0.35 : distribution — 25% deployment

## **Agent 07 — Sector Rotation Analyst**

**7.1 Relative Sector Momentum**

\# Rolling returns for each NSE sector index

sector_return(s, n) = (Sector_Index_t / Sector_Index_{t-n}) - 1

\# Rank sectors on 1M, 3M, 6M rolling windows

sector_rank(s) = 0.2 \* rank_30d(s) + 0.4 \* rank_63d(s) + 0.4 \* rank_126d(s)

\# Hot sectors (top 3 by rank) get +10% weight boost in portfolio

\# Cold sectors (bottom 3) get -50% weight cap

NSE Sectors tracked: IT, Banking, FMCG, Pharma, Auto, Energy,

Capital Goods, Metals, Realty, Infrastructure, Media, Chemicals

## **Agent 08 — Ownership & Flow Analyst**

**8.1 Smart Money Score**

\# FII change signal

fii_delta(i) = FII_holding_Q_now - FII_holding_Q_prev (in %)

fii_score(i) = clip(fii_delta \* 10, -1, 1)

\# DII (mutual fund) change signal

dii_delta(i) = DII_holding_Q_now - DII_holding_Q_prev

dii_score(i) = clip(dii_delta \* 10, -1, 1)

\# Promoter buying signal (very bullish when promoters buy open market)

promoter_buy = 1 if promoter_delta > 0.5% AND no pledging change

promoter_sell = -1 if promoter_delta < -1.0%

\# Bulk/Block deal signal (NSE data)

bulk_score = +0.5 if large buy bulk deal in last 5 days

bulk_score = -0.5 if large sell bulk deal in last 5 days

\# Composite smart money score

ownership_signal = 0.4\*fii_score + 0.3\*dii_score + 0.2\*promoter_signal + 0.1\*bulk_score

## **Agent 09 — Sentiment & News Analyst**

**9.1 Exa Search Sentiment**

Queries per stock (run daily for watchlist top 20):

\- '&lt;TICKER&gt; news site:economictimes.com OR moneycontrol.com'

\- '&lt;COMPANY&gt; order win contract announcement'

\- '&lt;COMPANY&gt; SEBI investigation fraud'

\- '&lt;COMPANY&gt; management resignation'

Sentiment classification:

Positive keywords: order, wins, beats, record, expansion, buyback

Negative keywords: fraud, investigation, SEBI, resignation, default, debt

Count(pos) - Count(neg) normalized to \[-1, +1\]

\# Only act on sentiment if news is < 3 days old (decay quickly)

sentiment_decay = exp(-0.5 \* days_since_news)

sentiment_signal = raw_sentiment \* sentiment_decay

## **Agent 10 — Event Analyst**

**10.1 Earnings Surprise Model**

\# Post-earnings drift (PEAD) — strong in India

earnings_surprise = (actual_EPS - estimated_EPS) / abs(estimated_EPS)

PEAD_signal:

surprise > +10% : +0.8 signal (buy the drift, valid 10-20 days post earnings)

surprise > +5% : +0.4 signal

surprise < -10% : -0.8 signal (avoid / exit)

surprise < -5% : -0.4 signal

\# Earnings window blocks:

5 days pre-results : BLOCK new entry (uncertainty too high)

1 day post-results : BLOCK entry (price gapping/settling)

2-20 days post-results: drift window, PEAD signal active

## **Agent 13 — Risk Manager**

**13.1 Value at Risk (Parametric)**

\# Daily portfolio VaR at 95% confidence

portfolio_return = sum(w_i \* r_i)

portfolio_vol = sqrt(w^T \* Sigma \* w) (covariance matrix, 63-day rolling)

VaR_95 = portfolio_mean - 1.645 \* portfolio_vol \* portfolio_value

VaR_99 = portfolio_mean - 2.326 \* portfolio_vol \* portfolio_value

Alert if: daily VaR_95 > 2.5% of portfolio value

**13.2 Portfolio Beta**

beta_i = Cov(r_i, r_nifty) / Var(r_nifty) (63-day rolling)

portfolio_beta = sum(w_i \* beta_i)

Target: portfolio_beta < 0.8 (we want stock alpha, not market beta)

Alert: portfolio_beta > 1.2 (too much market risk, reduce high-beta positions)

**13.3 Max Drawdown Monitor**

peak_value = max(portfolio_value, since inception)

MDD_current = (portfolio_value - peak_value) / peak_value

MDD < -10% : WARNING — reduce deployment by 20%

MDD < -15% : ALERT — liquidate all momentum positions, keep only quality

MDD < -20% : CRITICAL — full liquidation to cash, halt trading

**13.4 Per-Position Stop Loss**

\# Hard stop loss: -7% from entry price

\# Trailing stop: once position is +5%, trail stop at entry

\# Once position is +10%, trail stop at +5%

stop_price = entry_price \* (1 - 0.07)

trailing_stop: if P_t > entry \* 1.05: stop = entry

if P_t > entry \* 1.10: stop = entry \* 1.05

**13.5 Sharpe Ratio (Weekly Tracking)**

R_f = 0.065 / 252 (RBI repo rate proxy, daily)

Sharpe = (mean(daily_portfolio_returns) - R_f) / std(daily_portfolio_returns)

\* sqrt(252) (annualized)

Target Sharpe > 1.5 over rolling 63 days

Calmar Ratio = Annualized_Return / |Max_Drawdown| — target > 1.0

# **4\. P&L Tracking & Performance System**

Every buy/sell is logged with full metadata. P&L is computed using real market prices fetched via yfinance (NSE suffix: .NS).

## **4.1 Trade Log Schema**

| **Field** | **Type** | **Description** |
| --- | --- | --- |
| trade_id | UUID | Unique trade identifier |
| timestamp | datetime IST | Exact time of decision (not execution) |
| ticker | string | NSE symbol e.g. RELIANCE.NS |
| action | BUY / SELL | Direction |
| quantity | int | Number of shares |
| decision_price | float | Price at time of agent decision |
| execution_price | float | Simulated fill = decision_price \* (1 + slippage) |
| gross_value | float | quantity \* execution_price |
| charges | float | Full transaction cost from cost model |
| net_value | float | gross_value + charges (buy) or gross_value - charges (sell) |
| conviction_score | float | BOSS conviction at time of trade (0-1) |
| triggering_agents | list | Which agents voted positive |
| regime_at_trade | string | VIX regime at time of trade |
| stop_loss_price | float | Hard stop price set at entry |
| target_price | float | Agent 03/04 target at entry |
| status | OPEN / CLOSED | Position status |

## **4.2 Real-Time P&L Formula**

\# For open positions:

unrealized_PnL = (current_price - execution_price_buy) \* quantity

\- sell_charges_estimate (for when we eventually sell)

\# For closed positions:

realized_PnL = (execution_price_sell - execution_price_buy) \* quantity

\- buy_charges - sell_charges

\# Portfolio total:

total_PnL = sum(realized_PnL) + sum(unrealized_PnL)

portfolio_value = initial_capital + total_PnL

\# Return vs benchmark:

portfolio_return = (portfolio_value / initial_capital) - 1

nifty_return = (Nifty_t / Nifty_entry_date) - 1

alpha_generated = portfolio_return - nifty_return

## **4.3 Weekly P&L Report Fields**

| **Metric** | **Formula** | **Target** |
| --- | --- | --- |
| Total Return | (portfolio_value / 10,00,000) - 1 | \> Nifty return |
| Alpha vs Nifty 50 | portfolio_return - nifty_return | \> +2% per month |
| Sharpe Ratio | annualized (return - Rf) / vol | \> 1.5 |
| Calmar Ratio | annualized_return / \|MDD\| | \> 1.0 |
| Win Rate | count(profitable trades) / total trades | \> 55% |
| Avg Win / Avg Loss | mean(win_PnL) / abs(mean(loss_PnL)) | \> 1.8 |
| Max Drawdown | (trough - peak) / peak | \> -15% hard limit |
| Portfolio Beta | sum(w_i \* beta_i) | < 0.8 |
| Turnover | sum(\|trades\|) / avg_portfolio_value | < 40% per week |
| Cost Drag | total_charges / initial_capital | Track weekly |
| Total Charges Paid | sum(all buy/sell charges) | Minimize |

# **5\. Agent Decision Schedule (IST)**

The system is fully autonomous. This is the schedule it follows every market day.

| **Time (IST)** | **Agent(s)** | **Task** |
| --- | --- | --- |
| 8:45 AM | Agent 01 | Pull screener.in data via CLI. Build today's investable universe. |
| 8:55 AM | Agent 02 | Run Piotroski + Greenblatt on universe. Filter to quality watchlist. |
| 9:00 AM | Agent 06 | Check India VIX, Nifty futures, FII provisional data. Set regime. |
| 9:05 AM | Agent 10 | Check earnings calendar, ex-dates, SEBI filings for next 5 days. |
| 9:10 AM | Agent 09 | Exa search for top 20 watchlist stocks. Compute sentiment scores. |
| 9:15 AM | Agent 07 | Compute sector momentum rankings. Update hot/cold sector map. |
| 9:20 AM | Agent 08 | Update ownership scores from latest quarterly data + bulk deals. |
| 9:25 AM | Agent 13 | Check open positions for stop-loss breaches at pre-open price. |
| 9:30 AM | Agent 03, 04, 05 | Generate momentum, mean reversion, pairs signals on watchlist. |
| 9:35 AM | Agent 11 | Validate IC for each signal type. Apply IC weights. |
| 9:40 AM | BOSS | Run conviction aggregation. Compute Kelly sizes. Approve/reject trades. |
| 9:45 AM | Agent 14 | Log approved trades with full cost model. Simulate execution. |
| 11:30 AM | Agent 13 | Mid-session risk check. VaR, beta, MDD update. |
| 1:00 PM | Agents 03, 04 | Intraday z-score refresh. Flag any new mean reversion entries. |
| 2:30 PM | Agent 13 | Final risk check. Flag any stop-loss approaching positions. |
| 3:00 PM | Agent 14 | Last execution window closes. No new entries after 3:00 PM. |
| 3:35 PM | All Agents | End-of-day data collection. Update rolling factors. Log P&L. |
| After market | Agent 11 | Run backtesting on today's signals. Update IC estimates. |
| Sunday | Agent 05 | Re-run cointegration tests on all pairs. Recalibrate hedge ratios. |

# **6\. Agent Conviction Weight Summary**

| **Agent** | **Signal Range** | **IC Weight (initial)** | **Key Formula Used** |
| --- | --- | --- | --- |
| Agent 03 — Momentum | \-1 to +1 | 15% | Skip-month XS momentum + RS vs Nifty |
| Agent 04 — Mean Reversion | \-1 to +1 | 15% | Z-score, Bollinger width, Alpha#101 |
| Agent 05 — Pairs | \-1 to +1 | 10% | Cointegration spread Z-score |
| Agent 07 — Sector Rotation | \-1 to +1 | 10% | Rolling 30/63/126d sector rank |
| Agent 08 — Ownership | \-1 to +1 | 15% | FII/DII delta + promoter + bulk deal |
| Agent 09 — Sentiment | \-1 to +1 | 10% | Exa search NLP, decay-weighted |
| Agent 10 — Event/PEAD | \-1 to +1 | 10% | Earnings surprise, catalyst scan |
| Agent 02 — Quality | 0 to +1 (no short) | 10% | Piotroski F-Score + Greenblatt |
| Agent 06 — Macro | Regime gate | 5%  | VIX + Nifty trend + FII flow |
| Agent 12 — Liquidity | Multiplier 0-1 | 5%  | Amihud ratio, ADV filter, impact cost |

IC weights above are initial. They are recalibrated weekly by Agent 11 based on rolling 63-day IC performance. Agents with IC < 0.04 are temporarily zeroed out until their signal recovers.

# **7\. Quant Formula Reference**

| **Term** | **Formula / Definition** |
| --- | --- |
| Information Coefficient (IC) | Pearson corr(signal_t, return_{t+n}). Measures signal predictiveness. Target > 0.04. |
| IC Decay (lambda) | IC(lag) = IC_0 \* exp(-lambda \* lag). Higher lambda = faster signal stale. |
| Amihud Illiquidity | ILLIQ = (1/T) \* sum(\|R_t\| / Volume_t). Higher = more illiquid. |
| Piotroski F-Score | 9-point binary score on profitability, leverage, efficiency. Score >= 6 = quality. |
| Greenblatt EY | EBIT / Enterprise Value. Higher = more earnings per rupee of price paid. |
| Greenblatt ROCE | EBIT / (Net Fixed Assets + Working Capital). Higher = better capital efficiency. |
| Kelly Criterion | f\* = (p\*b - q) / b. Use f\*/2 (Half-Kelly) always. |
| Cross-Sectional Momentum | Rank stocks by risk-adjusted 12-1 month return. Long top quintile. |
| Skip-Month | Exclude last 1 month from momentum calculation. Fixes 1-month reversal bias in India. |
| Pairs Half-Life | half_life = -log(2) / log(1 + phi) from AR(1) on spread. Target: 3-20 days. |
| ADF Test | Augmented Dickey-Fuller. Tests if residuals are stationary (p < 0.05 = cointegrated). |
| Portfolio Beta | sum(w_i \* beta_i). Measures market exposure. Target < 0.8. |
| VaR 95% | portfolio_mean - 1.645 \* portfolio_vol \* portfolio_value. Daily max loss (95% CI). |
| Sharpe Ratio | (R_p - R_f) / sigma_p \* sqrt(252). R_f = 6.5% for India. |
| Calmar Ratio | CAGR / \|Max Drawdown\|. Measures return per unit of drawdown risk. |
| PEAD | Post-Earnings Announcement Drift. Stocks drift in the direction of earnings surprise for 10-20 days. |
| Implementation Shortfall | (execution_price - decision_price) / decision_price. Measures execution quality. |
| Regime Filter | VIX-based state machine. Controls maximum portfolio deployment. |
| Breadth | % of Nifty 500 stocks above SMA_50. Measures market health. |
| Alpha (WQ#101) | (close - open) / ((high - low) + epsilon). Intraday price position signal. |
| Round-trip Cost | ~0.23% for delivery. Includes STT (0.2%), exchange, SEBI, stamp, GST. |
| T+1 Settlement | Funds from sell not available until next trading day. Maintain 35% cash buffer. |
| ASM List | SEBI Additional Surveillance Measure. Stocks on this list are hard-rejected from universe. |

**END OF SYSTEM PIPELINE DOCUMENT**

This is a paper trading simulation. No real money is involved.