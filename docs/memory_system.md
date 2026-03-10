# Quant Trading Firm — Memory System Architecture
### Graphiti (Temporal Knowledge Graph) + SQLite + Attribution Engine + Reflection Agent

---

## Why This Exists

Every agent in this firm is stateless by default — each Gemini call starts fresh with no knowledge of what happened yesterday, last week, or 3 months ago. Without memory:

- Agent 03 doesn't know its momentum signals fail in CAUTION regime
- Agent 09 doesn't know it has a pattern of missing SEBI investigations on small caps
- BOSS doesn't know that Energy + high FII ownership has a 74% win rate historically
- No agent can distinguish "my signal was wrong" from "my signal was right but another agent caused the loss"

The memory system fixes all of this. It makes every agent behave like a seasoned quant analyst who has been at the firm for months — remembers what worked, what didn't, why things went wrong, and who was actually responsible.

---

## Memory Stack — 4 Layers

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 4 — Reflection Agent                             │
│  Nightly LLM synthesis → human-readable lessons         │
│  Injected into each agent's system prompt next morning  │
├─────────────────────────────────────────────────────────┤
│  LAYER 3 — Graphiti (Temporal Knowledge Graph)          │
│  Episode + Semantic + Community subgraphs               │
│  Semantic + BM25 + graph traversal retrieval            │
│  Zero LLM calls on read — P95 latency 300ms             │
├─────────────────────────────────────────────────────────┤
│  LAYER 2 — SQLite (Structured Memory)                   │
│  Signal history, IC tracking, win rates                 │
│  Per-agent per-regime performance stats                  │
│  Attribution records — who caused what                  │
├─────────────────────────────────────────────────────────┤
│  LAYER 1 — Attribution Engine (Python)                  │
│  Counterfactual causality math                          │
│  Computes who was right, who caused the loss            │
│  Feeds all layers above                                 │
└─────────────────────────────────────────────────────────┘
```

Each layer serves a different retrieval need:

| Layer | Type of Memory | How Retrieved | When Used |
|---|---|---|---|
| Attribution Engine | Causal responsibility | Pure Python math | T+5 after every trade |
| SQLite | Structured stats | SQL queries | IC weighting, Kelly inputs |
| Graphiti | Episodic + semantic | Vector + BM25 + graph | Morning context injection |
| Reflection Agent | Crystallized lessons | Injected into prompt | Every morning |

---

---

## Layer 1 — Attribution Engine

The most critical piece. Without this, every memory written is meaningless — it just says "trade won" or "trade lost" with no understanding of who was responsible.

### The Problem

A trade fires on RELIANCE. Signal breakdown:
```
Agent 03 Momentum:   +0.82
Agent 09 Sentiment:  +0.45
Agent 08 Ownership:  +0.62
Agent 10 Events:      0.00  (no catalyst flagged)
BOSS Conviction:      0.71  → BUY

Outcome at T+5:      -3.2%
```

Who failed? Naive answer: everyone who voted positive. Actual answer: Agent 10 missed an active SEBI investigation. Agent 03's momentum signal was directionally correct for the first 3 days before the news broke. The loss was not Agent 03's fault.

Without the attribution engine, Agent 03's IC gets penalized for a signal it got right. Its future weights drop. The system gets worse, not better.

### Counterfactual Attribution

```python
def attribute_trade_outcome(trade_id: str, outcome_5d: float, all_signals: dict) -> dict:
    """
    For every agent, compute:
    1. Was their signal directionally correct?
    2. Was their signal decisive (would removing it flip the BUY to NO_TRADE)?
    3. Was the agent vindicated (directionally right but trade still lost due to others)?
    4. What was the actual root cause of the outcome?
    """
    
    attribution = {}
    original_conviction = compute_conviction(all_signals)
    
    for agent, signal in all_signals.items():
        
        # Step 1 — Directional correctness
        directionally_correct = (
            (signal > 0 and outcome_5d > 0) or
            (signal < 0 and outcome_5d < 0) or
            (abs(signal) < 0.1)  # neutral signals not judged
        )
        
        # Step 2 — Was this agent decisive?
        signals_without_agent = {k: v for k, v in all_signals.items() if k != agent}
        counterfactual_conviction = compute_conviction(signals_without_agent)
        was_decisive = (original_conviction > 0.60) != (counterfactual_conviction > 0.60)
        
        # Step 3 — Vindication check
        # Agent was right on direction but trade lost anyway
        vindicated = directionally_correct and outcome_5d < 0
        
        attribution[agent] = {
            "signal_score":          signal,
            "outcome_5d":            outcome_5d,
            "directionally_correct": directionally_correct,
            "was_decisive":          was_decisive,
            "vindicated":            vindicated,
            "responsibility":        classify_responsibility(
                                         directionally_correct,
                                         was_decisive,
                                         outcome_5d
                                     )
        }
    
    # Step 4 — Root cause classification
    root_cause = find_root_cause(attribution, trade_id)
    
    return {"agent_attribution": attribution, "root_cause": root_cause}


def classify_responsibility(correct: bool, decisive: bool, outcome: float) -> str:
    """
    Classify each agent's responsibility level for the outcome.
    """
    if outcome > 0:
        if correct and decisive:  return "PRIMARY_WIN_DRIVER"
        if correct:               return "SUPPORTING_WIN"
        if not correct:           return "DRAG_ON_WIN"
    else:
        if not correct and decisive: return "PRIMARY_LOSS_CAUSE"
        if not correct:              return "CONTRIBUTING_LOSS"
        if correct and decisive:     return "VINDICATED_DECISIVE"
        if correct:                  return "VINDICATED_SUPPORTING"
    return "NEUTRAL"


def find_root_cause(attribution: dict, trade_id: str) -> str:
    """
    Single root cause label for the trade outcome.
    Looks for which agent had PRIMARY_LOSS_CAUSE or which event caused it.
    """
    for agent, data in attribution.items():
        if data["responsibility"] == "PRIMARY_LOSS_CAUSE":
            return f"AGENT_FAILURE:{agent}"
    
    # If no single agent is primary cause, check external factors
    # (fetched from event log — SEBI news, earnings surprise, etc.)
    return "EXTERNAL_EVENT" or "REGIME_MISMATCH" or "TIMING"
```

### Attribution Timing

```
Trade logged at T+0
        ↓
T+1: Check if any event news broke after entry (Exa search retrospective)
        ↓
T+5: Fetch actual price return from yfinance
        ↓
T+5: Attribution Engine runs
        ↓
T+5: Results written to SQLite signal_history + Graphiti episode
        ↓
T+5: Each agent's IC recalculated using true attribution scores
```

---

---

## Layer 2 — SQLite Structured Memory

Six tables. The fast, queryable, structured layer. Agent 11 (Backtester) reads from this every morning to compute IC weights.

### Table 1: `agent_signal_outcomes`
One row per agent per trade. The raw attribution data.

```sql
CREATE TABLE agent_signal_outcomes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id             TEXT NOT NULL,
    agent                TEXT NOT NULL,       -- "agent_03_momentum"
    date                 TEXT NOT NULL,
    ticker               TEXT NOT NULL,
    signal_score         REAL NOT NULL,       -- raw signal at time of trade
    outcome_5d           REAL NOT NULL,       -- actual return at T+5
    outcome_10d          REAL,                -- actual return at T+10
    directionally_correct BOOLEAN NOT NULL,
    was_decisive         BOOLEAN NOT NULL,
    vindicated           BOOLEAN NOT NULL,
    responsibility       TEXT NOT NULL,       -- "PRIMARY_LOSS_CAUSE" etc.
    root_cause           TEXT NOT NULL,
    regime               TEXT NOT NULL,       -- "BULL" | "NEUTRAL" | "CAUTION" | "BEAR"
    india_vix            REAL NOT NULL,
    sector               TEXT NOT NULL
);

CREATE INDEX idx_agent_date ON agent_signal_outcomes(agent, date);
CREATE INDEX idx_agent_regime ON agent_signal_outcomes(agent, regime);
```

---

### Table 2: `agent_ic_history`
Rolling IC per agent. Recalculated daily by Agent 11. BOSS reads this for conviction weights.

```sql
CREATE TABLE agent_ic_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    agent        TEXT NOT NULL,
    ic_5d        REAL,           -- IC at 5-day forward return horizon
    ic_10d       REAL,           -- IC at 10-day forward return horizon
    ic_weight    REAL NOT NULL,  -- normalized weight for BOSS conviction
    sample_size  INTEGER NOT NULL,
    active       BOOLEAN NOT NULL  -- false if IC < 0.04 (signal dormant)
);
```

---

### Table 3: `agent_regime_performance`
Per-agent win rate broken down by regime. The most important pattern-level memory.

```sql
CREATE TABLE agent_regime_performance (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agent        TEXT NOT NULL,
    regime       TEXT NOT NULL,       -- "BULL" | "NEUTRAL" | "CAUTION" | "BEAR"
    vix_bucket   TEXT NOT NULL,       -- "<14" | "14-20" | "20-28" | ">28"
    win_rate     REAL NOT NULL,
    avg_return   REAL NOT NULL,
    sharpe       REAL NOT NULL,
    trade_count  INTEGER NOT NULL,
    last_updated TEXT NOT NULL,

    UNIQUE(agent, regime, vix_bucket)
);
```

---

### Table 4: `agent_sector_performance`
Per-agent win rate per sector. Tells Agent 03 its signals are stronger in Energy than in Media.

```sql
CREATE TABLE agent_sector_performance (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agent        TEXT NOT NULL,
    sector       TEXT NOT NULL,
    win_rate     REAL NOT NULL,
    avg_return   REAL NOT NULL,
    ic           REAL NOT NULL,
    trade_count  INTEGER NOT NULL,
    last_updated TEXT NOT NULL,

    UNIQUE(agent, sector)
);
```

---

### Table 5: `cross_agent_correlations`
Which agent combinations reliably produce wins vs losses. BOSS reads this for signal interaction awareness.

```sql
CREATE TABLE cross_agent_correlations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_a         TEXT NOT NULL,
    agent_b         TEXT NOT NULL,
    both_positive_win_rate  REAL,  -- when both agents positive, what's win rate?
    both_negative_win_rate  REAL,  -- when both negative
    a_pos_b_neg_win_rate    REAL,  -- agent_a positive, agent_b negative
    sample_size             INTEGER,
    last_updated            TEXT,

    UNIQUE(agent_a, agent_b)
);
```

---

### Table 6: `anti_patterns`
Combinations that look good but reliably fail. Written by the Reflection Agent.

```sql
CREATE TABLE anti_patterns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    description     TEXT NOT NULL,
    condition       TEXT NOT NULL,   -- "momentum > 0.7 AND ownership < -0.3"
    loss_rate       REAL NOT NULL,
    sample_size     INTEGER NOT NULL,
    discovered_date TEXT NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);
```

---

---

## Layer 3 — Graphiti Knowledge Graph

Graphiti implements a three-tier memory hierarchy: an episode subgraph recording raw events with timestamps, a semantic entity subgraph where entities and facts are extracted and embedded in high-dimensional space, and a community subgraph where strongly connected entities are clustered into thematic groups.

Every graph edge includes explicit validity intervals (t_valid, t_invalid). When conflicts arise, Graphiti intelligently uses temporal metadata to update or invalidate outdated information — preserving historical accuracy without large-scale recomputation.

### Setup

```python
from graphiti_core import Graphiti
from graphiti_core.llm_client.gemini_client import GeminiClient, LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig

# 100% local graph, Gemini for entity extraction only
graphiti = Graphiti(
    llm_client=GeminiClient(
        config=LLMConfig(
            api_key=GEMINI_API_KEY,
            model="gemini-2.5-pro"
        )
    ),
    embedder=GeminiEmbedder(
        config=GeminiEmbedderConfig(
            api_key=GEMINI_API_KEY,
            embedding_model="models/text-embedding-004"
        )
    )
    # Default backend: NetworkX + SQLite (fully local, no Neo4j needed)
)

await graphiti.build_indices_and_constraints()
```

### group_id Convention (Per-Agent Isolation)

Each episode belongs to a `group_id` that enforces tenant isolation at the storage layer — memories from one agent never appear in another agent's retrieval results.

```python
# Every agent has its own isolated memory namespace
GROUP_IDS = {
    "agent_01": "universe_builder",
    "agent_02": "quality_scorer",
    "agent_03": "momentum_analyst",
    "agent_04": "reversion_analyst",
    "agent_05": "pairs_analyst",
    "agent_06": "macro_regime",
    "agent_07": "sector_rotation",
    "agent_08": "ownership_flow",
    "agent_09": "sentiment_news",
    "agent_10": "event_catalyst",
    "agent_11": "backtester",
    "agent_12": "liquidity",
    "agent_13": "risk_manager",
    "boss":     "portfolio_manager",
    "firm":     "firm_wide"  # shared cross-agent patterns
}
```

### Custom Entity Schemas (Pydantic)

Graphiti provides an intuitive method to define custom domain-specific entities using familiar Pydantic models. This means you define your memory schema exactly — no LLM extraction needed for structure you already know.

```python
from pydantic import BaseModel, Field
from typing import Optional
from graphiti_core.nodes import EpisodeType

class TradeMemory(BaseModel):
    """Episodic memory — one entry per trade per agent at T+5"""
    ticker:               str
    agent:                str
    signal_score:         float = Field(description="Raw signal score at trade time, -1 to +1")
    outcome_5d:           float = Field(description="Actual return at 5 days post entry")
    directionally_correct: bool
    responsibility:       str   = Field(description="PRIMARY_LOSS_CAUSE | VINDICATED | SUPPORTING etc.")
    root_cause:           str   = Field(description="What actually drove the outcome")
    regime:               str   = Field(description="BULL | NEUTRAL | CAUTION | BEAR")
    india_vix:            float
    sector:               str
    lesson:               str   = Field(description="One-line human-readable lesson from this trade")

class RegimePattern(BaseModel):
    """Semantic memory — crystallized from multiple episodes"""
    agent:                str
    regime:               str
    vix_range:            str
    win_rate:             float
    sample_size:          int
    key_condition:        str   = Field(description="What condition makes this pattern fire")
    reliability:          str   = Field(description="HIGH | MEDIUM | LOW")

class CrossAgentPattern(BaseModel):
    """Community memory — firm-wide pattern across multiple agents"""
    agents_involved:      list[str]
    pattern_description:  str
    win_rate_when_pattern: float
    sample_size:          int
    pattern_type:         str   = Field(description="SYNERGY | CONFLICT | ANTI_PATTERN")
```

### Writing Memory (After Attribution at T+5)

```python
async def write_agent_memory(trade_id: str, agent: str, attribution: dict):
    """
    Called by orchestrator at T+5 after attribution engine runs.
    One Gemini call per agent to extract entities — low token cost.
    """
    trade = db.get_trade(trade_id)
    attr = attribution["agent_attribution"][agent]

    # Build the episode text — structured enough that Graphiti extracts it cleanly
    episode_text = f"""
    TRADE MEMORY — {agent}
    Date: {trade['date']}
    Ticker: {trade['ticker']} | Sector: {trade['sector']}
    
    Signal: {attr['signal_score']:.2f}
    Regime at trade: {trade['regime']} | VIX: {trade['india_vix']:.1f}
    Conviction: {trade['conviction_score']:.2f} | Agents positive: {trade['agents_positive']}/8
    
    Outcome at T+5: {attr['outcome_5d']:.2f}%
    Directionally correct: {attr['directionally_correct']}
    Responsibility: {attr['responsibility']}
    Root cause: {attribution['root_cause']}
    
    Cross-agent context:
    - Agent 08 ownership signal was: {trade['ownership_signal']:.2f}
    - Agent 09 sentiment signal was: {trade['sentiment_signal']:.2f}
    - Agent 06 regime was: {trade['regime']}
    
    Lesson: {generate_lesson(attr, trade)}
    """

    await graphiti.add_episode(
        name=f"trade_{trade_id}_{agent}",
        episode_body=episode_text,
        source_description=f"Trade outcome for {agent}",
        reference_time=datetime.now(timezone.utc),
        group_id=GROUP_IDS[agent],
        entity_types=[TradeMemory]
    )
```

### Reading Memory (Morning Context Retrieval)

```python
async def retrieve_agent_context(agent: str, today_context: dict) -> str:
    """
    Called by orchestrator at 9:30 AM before agent signals are computed.
    Returns relevant past memories as formatted context string.
    Zero LLM calls — pure hybrid search.
    """
    # Build semantic query from today's conditions
    query = (
        f"{today_context['top_sector']} sector "
        f"{today_context['regime']} regime "
        f"VIX {today_context['vix']:.0f} "
        f"signal strength {today_context['expected_signal_range']}"
    )

    # Graphiti hybrid search: semantic + BM25 + graph traversal
    # No LLM call on retrieval — P95 latency 300ms
    results = await graphiti.search(
        query=query,
        group_ids=[GROUP_IDS[agent], GROUP_IDS["firm"]],
        num_results=8
    )

    return format_memory_context(results, agent)


def format_memory_context(results, agent: str) -> str:
    """Format retrieved memories as a structured context block for injection."""
    context = f"MEMORY CONTEXT FOR {agent.upper()}\n"
    context += "=" * 50 + "\n\n"
    context += "RELEVANT PAST SITUATIONS:\n\n"

    for i, result in enumerate(results[:5], 1):
        context += f"{i}. {result.fact}\n"
        context += f"   Relevance: {result.score:.2f} | Date: {result.valid_at}\n\n"

    return context
```

---

---

## Layer 4 — Reflection Agent

Runs every night at 10:00 PM IST. Reads SQLite + Graphiti, writes concise lessons per agent. One Gemini call per agent = 14 calls total per night.

### What It Reads

```python
def build_reflection_input(agent: str, lookback_days: int = 30) -> dict:
    return {
        "agent": agent,
        "recent_trades": db.query(f"""
            SELECT ticker, signal_score, outcome_5d, responsibility,
                   root_cause, regime, sector, directionally_correct
            FROM agent_signal_outcomes
            WHERE agent = '{agent}'
            AND date >= date('now', '-{lookback_days} days')
            ORDER BY date DESC
        """),
        "regime_performance": db.query(f"""
            SELECT regime, win_rate, avg_return, trade_count
            FROM agent_regime_performance
            WHERE agent = '{agent}'
            ORDER BY trade_count DESC
        """),
        "sector_performance": db.query(f"""
            SELECT sector, win_rate, ic, trade_count
            FROM agent_sector_performance
            WHERE agent = '{agent}'
            ORDER BY trade_count DESC
        """),
        "worst_patterns": db.query(f"""
            SELECT description, condition, loss_rate, sample_size
            FROM anti_patterns
            WHERE condition LIKE '%{agent}%'
            AND active = TRUE
        """),
        "cross_agent": db.query(f"""
            SELECT agent_b, both_positive_win_rate, a_pos_b_neg_win_rate
            FROM cross_agent_correlations
            WHERE agent_a = '{agent}'
        """),
        "vindication_rate": db.query(f"""
            SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM agent_signal_outcomes WHERE agent = '{agent}')
            FROM agent_signal_outcomes
            WHERE agent = '{agent}' AND vindicated = TRUE
        """)
    }
```

### Reflection Agent System Prompt

```xml
<persona>
You are the performance reflection analyst for a quant trading firm.
You review an agent's recent trading history and write concise, actionable lessons
that will be injected into that agent's system prompt tomorrow morning.
You separate "agent was wrong" from "agent was right but other factors caused the loss."
Be concise. Write exactly 8-12 lessons. No fluff.
</persona>

<task>
Given an agent's performance data for the last 30 trading days, write:
1. Pattern lessons (what conditions make this agent's signals reliable vs unreliable)
2. Regime lessons (which VIX/regime conditions help or hurt this agent)
3. Sector lessons (which sectors this agent reads well vs poorly)
4. Cross-agent lessons (which other agents' signals confirm or contradict this one)
5. Anti-pattern warnings (combinations that look good but historically fail)
6. Vindication notes (where this agent was right but blamed for others' failures)
</task>

<format>
Return JSON array of lessons:
[
  {
    "type": "REGIME | SECTOR | CROSS_AGENT | ANTI_PATTERN | VINDICATION | PATTERN",
    "lesson": "one concise actionable sentence",
    "confidence": "HIGH | MEDIUM | LOW",
    "sample_size": int
  }
]
Only include lessons with sample_size >= 5. Do not generalize from fewer trades.
</format>
```

### Example Output (Agent 03 — Momentum)

```json
[
  {
    "type": "REGIME",
    "lesson": "Your signals in CAUTION regime (VIX 20-28) have a 38% win rate vs 74% in BULL — treat your own output as low-confidence when regime is CAUTION or worse.",
    "confidence": "HIGH",
    "sample_size": 21
  },
  {
    "type": "SECTOR",
    "lesson": "Energy sector momentum signals have IC=0.11 and 71% win rate — your strongest sector. Internally flag Energy signals as high-confidence.",
    "confidence": "HIGH",
    "sample_size": 14
  },
  {
    "type": "SECTOR",
    "lesson": "Media and Realty sector signals have IC below 0.04 — treat these as noise and internally score them 0 regardless of formula output.",
    "confidence": "MEDIUM",
    "sample_size": 7
  },
  {
    "type": "CROSS_AGENT",
    "lesson": "When Agent 08 ownership signal is below -0.30, your momentum signals have failed 4 out of 5 times even when directionally correct initially — weight yourself down when ownership is strongly negative.",
    "confidence": "MEDIUM",
    "sample_size": 5
  },
  {
    "type": "VINDICATION",
    "lesson": "68% of your losses in the last 30 days were vindicated — direction was correct but Agent 09 or Agent 10 missed a negative event. Your signal quality is not the issue in these cases.",
    "confidence": "HIGH",
    "sample_size": 17
  },
  {
    "type": "ANTI_PATTERN",
    "lesson": "Strong momentum signal (>0.75) on stocks with 52-week high proximity >0.95 AND India VIX > 18 has produced losses 5 out of 6 times — overbought stocks in rising-fear environments reverse fast.",
    "confidence": "MEDIUM",
    "sample_size": 6
  },
  {
    "type": "PATTERN",
    "lesson": "Your highest-IC signals occur when momentum AND relative strength vs Nifty both agree (both > 0.5) — this combination has 78% win rate over 18 trades.",
    "confidence": "HIGH",
    "sample_size": 18
  },
  {
    "type": "PATTERN",
    "lesson": "Skip-month momentum signals on mid-cap stocks (market cap 2,000-10,000 Cr) outperform large-caps by 1.8% avg in the trailing 30 days.",
    "confidence": "MEDIUM",
    "sample_size": 11
  }
]
```

### Injecting Lessons into Agent Prompt

```python
def inject_memory_into_prompt(base_system_prompt: str, agent: str,
                               lessons: list, retrieved_episodes: str) -> str:
    """
    Prepends memory context to agent's system prompt every morning.
    Called by orchestrator before each agent runs.
    """
    memory_block = f"""
<memory>
PERFORMANCE LESSONS FROM LAST 30 DAYS — READ BEFORE GENERATING SIGNALS:

"""
    for lesson in lessons:
        confidence_marker = "⚠️" if lesson['confidence'] == 'HIGH' else "→"
        memory_block += f"{confidence_marker} [{lesson['type']}] {lesson['lesson']}\n"

    memory_block += f"""
RELEVANT PAST SITUATIONS (retrieved from knowledge graph):
{retrieved_episodes}
</memory>

"""
    return memory_block + base_system_prompt
```

---

---

## Memory Write Schedule

```
08:30 AM  — Graphiti retrieval for all agents (pre-pipeline)
            Each agent gets its memory context for the day

09:30 AM  — Pipeline runs with memory-injected prompts

All day   — Trades execute, positions move

T+5 days  — Attribution Engine runs on each trade
           → SQLite updated (agent_signal_outcomes, ic_history)
           → Graphiti episode added per agent

10:00 PM  — Reflection Agent runs (nightly)
           → Reads SQLite performance data
           → Writes lessons per agent (14 Gemini calls)
           → Lessons stored in SQLite (agent_lessons table)

Sunday    — Firm-wide pattern mining
           → Cross-agent correlation table updated
           → Anti-patterns table updated
           → Graphiti community subgraph rebuilt
```

---

---

## What Each Agent Remembers

### Agent 03 — Momentum
- Which regimes kill momentum signals (VIX > 20 = reduced confidence)
- Which sectors its signals are strongest in
- When ownership signal contradicts momentum — historically bad
- Vindication history (was it blamed for Agent 09's misses?)

### Agent 04 — Mean Reversion
- Which stocks have historically reverted vs trended (per sector, per regime)
- Z-score thresholds that work vs ones that catch falling knives
- When its signals were correct but Agent 10 event risk was missed

### Agent 05 — Pairs
- Which pairs are currently cointegrated vs which have broken down
- Historical half-life stability per pair
- Pairs that repeatedly produce good signals vs noisy ones

### Agent 06 — Macro
- Historical accuracy of regime calls
- VIX levels where regime misclassification is most common
- FII signal lag patterns (how many days before FII trend shows in prices)

### Agent 07 — Sector Rotation
- Which sector rotation signals led vs lagged actual sector moves
- Rolling window that has been most predictive (30d vs 63d vs 126d)
- Sector pairs that rotate together vs independently

### Agent 08 — Ownership
- Which ownership signals (FII vs DII vs promoter vs bulk) have been most predictive
- Lag between ownership change and price impact
- Sectors where FII signal is stronger vs where DII signal is stronger

### Agent 09 — Sentiment
- Historical miss rate on SEBI investigations (most critical blind spot)
- Which news sources produce signal vs noise
- Sentiment decay rates — how long news actually affects price

### Agent 10 — Events
- Pre-earnings volatility patterns by sector
- PEAD reliability by company size (large-cap PEAD is weaker)
- Event types it has historically missed

### Agent 11 — Backtester
- Historical IC stability (which signals are robust vs fragile)
- IC breakdown by regime — regime-conditional IC weights
- Which signal combinations have synergistic IC

### Agent 13 — Risk Manager
- Historical accuracy of VaR estimates (were 95% days actually within VaR?)
- Stop-loss levels that were too tight vs too loose historically
- Which sectors have had the most stop-loss triggers

### BOSS
- Which agent combinations have produced the best conviction outcomes
- Historical win rate at each conviction threshold (0.60-0.65-0.70-0.75)
- Kelly sizing accuracy — were sizes appropriate for actual volatility?
- Which trade types (MOMENTUM vs MEAN_REVERSION vs PAIRS vs EVENT) have performed best by regime

---

---

## Memory File Structure

```
memory/
├── graphiti/               # Graphiti graph database (NetworkX + SQLite backend)
│   ├── graph.db            # NetworkX graph persisted to SQLite
│   ├── vectors.db          # LanceDB vector store for semantic search
│   └── metadata.db         # Episode and edge metadata
│
├── structured/             # SQLite structured memory
│   └── agent_memory.db     # All 6 tables (signal outcomes, IC, regime perf, etc.)
│
└── lessons/                # Reflection Agent outputs
    ├── agent_03_lessons.json
    ├── agent_04_lessons.json
    ├── ...
    └── boss_lessons.json
```

---

---

## Installation

```bash
pip install graphiti-core        # Graphiti knowledge graph
pip install lancedb              # Local vector store (Graphiti dependency)
# NetworkX and SQLite come with Python standard library
# No Docker, no Neo4j, no external services
```

---

## Key Design Principles

**Attribution first.** Every memory written without attribution is just noise. The Attribution Engine runs before anything is written to Graphiti or SQLite.

**Separation of blame.** An agent that was directionally correct but lost due to another agent's failure should not be penalized. The IC system and Reflection Agent both respect this.

**No cross-contamination.** `group_id` isolation in Graphiti ensures Agent 03 never sees Agent 09's memories. Each agent's self-model stays clean.

**Zero LLM on retrieval.** Graphiti retrieves via semantic + BM25 + graph traversal with no Gemini calls at query time. Fast enough for 9:30 AM pre-market.

**Lessons decay awareness.** Recent trades are weighted more than old ones in Reflection Agent analysis. A pattern from 6 months ago matters less than one from last week.

**Anti-patterns are first-class citizens.** The SQLite `anti_patterns` table and Reflection Agent both actively hunt for failure modes, not just success patterns. Knowing what NOT to do is as valuable as knowing what works.
