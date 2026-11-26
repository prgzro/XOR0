# JEV QUANT — Master Engineering Implementation Plan

## 1. Project Mission

Build a robust AI-powered quantitative trading system for MetaTrader 4 (MT4), using MQL4, Node.js, and the Jev Decision API provided by OpenCode Zen.

The system will use the existing **AbuHamzah Auto SQ9 V2 indicator source code** as its mathematical reference and trading-strategy foundation.

The objective is not to create a conventional EA that blindly executes indicator signals.

The objective is to build an AI-assisted Quant Trading System in which:

- The original SQ9 mathematical implementation determines price levels and trading setups.
- The quantitative engine analyzes market data and identifies valid SQ9 opportunities.
- Jev acts as the AI Quant Decision Maker and evaluates each qualified trading opportunity.
- A dedicated risk engine validates every trade before execution.
- MT4 executes approved trades and records their outcomes.
- Historical results and previous decisions are collected for performance analysis and future decision-quality evaluation.

Jev must be treated as a structured decision model, NOT as a conversational LLM, autonomous coding agent, or Reinforcement Learning model.

It does not automatically learn from completed trades, retain persistent memory between API requests, access live market data, or execute trading operations.

All necessary context must be explicitly provided to Jev through structured API requests.

---

# 2. Mandatory Initial Repository Investigation

Before implementing anything, thoroughly inspect the existing repository.

Do not assume the repository structure, existing technology choices, build configuration, or source-code organization.

### 2.1 Locate and inspect the original indicator

The original AbuHamzah Auto SQ9 V2 source code is located in:

`indcators/`

Important: The directory name is intentionally written as `indcators`. Locate and use the existing directory without renaming it.

Inspect the entire directory and all related source files.

Identify:

- The main indicator source file.
- All included MQL4 files.
- Indicator inputs and default values.
- Indicator buffers.
- Graphical chart objects.
- Price and time calculation functions.
- Automatic channel calculations.
- Star and triangle calculations.
- High/Low anchor selection.
- Angle calculations.
- Space calculations.
- Time-cycle calculations.
- Supported operating modes.
- Timeframe behavior.
- Any automatic recalculation mechanisms.

Read the complete source code, not just its inputs or comments.

### 2.2 Perform mathematical reverse engineering

Document exactly how the original indicator calculates:

1. The 0° origin.
2. The 45° price level.
3. The 90° price level.
4. The 360° price level.
5. The Space parameter.
6. Price/time relationships.
7. Bullish and bearish calculations.
8. Anchor selection and recalculation.
9. Timeframe-dependent adjustments.

Do not blindly implement a generic Square of Nine formula.

The original AbuHamzah source code is the primary reference for reproducing the indicator's actual behavior.

If the indicator uses a proprietary variation or additional scaling rules, reproduce those rules rather than replacing them with textbook assumptions.

### 2.3 Investigate repainting and look-ahead risks

Determine whether the indicator:

- Changes its historical anchor after new candles appear.
- Uses unconfirmed swing highs or lows.
- Recalculates old levels.
- Uses future bars when identifying turning points.
- Produces different results after chart refresh.
- Changes calculations when switching timeframes.

The trading engine must never use information that was unavailable at the time of the original trading decision.

Use confirmed historical information only.

### 2.4 Produce an initial technical audit

Before implementation, create:

`docs/INDICATOR_REVERSE_ENGINEERING.md`

Include:

- Source-file inventory.
- Mathematical formulas.
- Indicator configuration.
- Explanation of each calculation.
- Anchor selection behavior.
- Price-level generation.
- Repainting analysis.
- Source dependencies.
- Known limitations.
- Validation fixtures and unresolved questions.

Do not modify or overwrite the original indicator source code.

Keep the original indicator available for chart visualization and mathematical comparison.

---

# 3. System Architecture

Build the system using clearly separated components.

## Component A — MT4 Market Data Engine

Technology: MQL4

Responsibilities:

- Collect OHLC data.
- Collect tick data where required.
- Calculate market volatility.
- Calculate ATR.
- Calculate spread.
- Identify candle direction and momentum.
- Track recent swing highs and lows.
- Calculate market structure.
- Detect completed candles.
- Prepare normalized market snapshots.

All calculations must use closed candles whenever the strategy requires candle confirmation.

Avoid evaluating the same completed candle multiple times.

## Component B — SQ9 Quantitative Engine

Technology: MQL4

Responsibilities:

- Reproduce the original AbuHamzah SQ9 calculations.
- Identify the 0°, 45°, 90°, and 360° levels.
- Determine bullish and bearish directional levels.
- Manage the active SQ9 anchor.
- Track price progression between levels.
- Track time-cycle progression where supported by the original indicator.
- Detect valid SQ9 trading setups.
- Prevent duplicate setup generation.

Extract reusable mathematical calculations into a separate module.

Suggested module:

`SQ9Engine.mqh`

Keep mathematical calculations independent from execution and Jev integration.

The original indicator must not become a runtime dependency that silently changes trading calculations.

Where possible, expose comparable calculation outputs for validation against the original indicator.

## Component C — Jev Quant Decision Engine

Technology: Node.js 18+, native fetch API.

Responsibilities:

- Receive structured market snapshots.
- Receive completed SQ9 setup information.
- Validate incoming requests.
- Construct typed Jev questions.
- Call OpenCode Zen's System One endpoint.
- Parse structured decisions.
- Validate decision confidence and probabilities.
- Reject invalid or inconsistent results.
- Maintain request identifiers.
- Record decision history.
- Return validated decisions to MT4.

Jev must evaluate real quantitative features, not just a textual BUY/SELL description.

## Component D — Risk Management Engine

Technology: MQL4.

Responsibilities:

- Validate proposed entry prices.
- Calculate SL and TP.
- Calculate lot sizes.
- Enforce risk-per-trade limits.
- Validate minimum risk/reward requirements.
- Enforce maximum spread.
- Prevent duplicate trades.
- Apply daily risk limits.
- Validate broker execution constraints.
- Reject dangerous or invalid trades independently of Jev.

Jev cannot override risk controls.

## Component E — Execution Engine

Technology: MQL4

Responsibilities:

- Execute approved BUY and SELL trades.
- Set SL and TP.
- Monitor active trades.
- Record execution details.
- Handle broker errors.
- Prevent duplicate order execution.
- Maintain state across terminal restarts.

The execution engine must only accept validated decisions from the Quant Decision Engine and Risk Management Engine.

---

# 4. Core Trading Strategy

Strategy name:

`SQ9_90_BREAKOUT_RETEST`

This strategy must support BOTH bullish and bearish trading.

Reproduce the following sequence exactly, using the original indicator's price-level calculations.

## 4.1 Bullish Setup — BUY

Starting point: Confirmed bullish SQ9 origin at 0°.

Expected progression:

1. Initial Move: Price advances from 0° toward 90°.
2. Pullback: Price retraces toward 45°.
3. Pullback Confirmation: A completed candle must close at the 45° level or inside the configured 45° tolerance zone.
4. Continuation: Price moves upward again.
5. Breakout: A completed candle closes above 90°, exceeding the configured breakout buffer.
6. Retest: Price returns to the 90° level or its configured retest zone.
7. Retest Confirmation: The retest candle closes back above 90°.
8. Entry: BUY at the first available tick after the retest confirmation candle closes.

Trade levels:

- Stop Loss: SQ9 0°.
- Take Profit: SQ9 360°.

A wick touching 45° is not sufficient to confirm the pullback.

A wick touching 90° is not sufficient to confirm the breakout.

## 4.2 Bearish Setup — SELL

Starting point: Confirmed bearish SQ9 origin at 0°.

Mirror the bullish setup using the original indicator's bearish calculation.

Expected progression:

1. Initial Move: Price declines from 0° toward 90°.
2. Pullback: Price retraces toward 45°.
3. Pullback Confirmation: A completed candle closes at the 45° level or inside the configured 45° tolerance zone.
4. Continuation: Price resumes its downward movement.
5. Breakout: A completed candle closes below 90°.
6. Retest: Price returns to the 90° level or configured retest zone.
7. Retest Confirmation: The retest candle closes back below 90°.
8. Entry: SELL at the first available tick after the confirmation candle closes.

Trade levels:

- Stop Loss: SQ9 0°.
- Take Profit: SQ9 360°.

All bearish calculations must be mathematically consistent with the original indicator.

Do not assume that bullish and bearish levels can simply be calculated by adding and subtracting an arbitrary fixed distance.

## 4.3 Strategy State Machine

Implement the strategy as an explicit state machine.

Required states:

- WAIT_ORIGIN
- INITIAL_MOVE
- PULLBACK
- PULLBACK_CONFIRMED
- BREAKOUT_CONFIRMED
- WAIT_RETEST
- RETEST_CONFIRMED
- JEV_PENDING
- JEV_APPROVED
- JEV_REJECTED
- RISK_VALIDATION
- TRADE_OPEN
- TRADE_COMPLETED
- SETUP_INVALIDATED

Every state transition must have:

- A documented condition.
- A source candle timestamp.
- A current anchor identifier.
- A unique setup identifier.
- A reason recorded in the trading journal.

The state machine must support both BUY and SELL using consistent directional logic.

## 4.4 Setup Invalidation

Invalidate a setup when:

- The 45° pullback condition fails.
- The origin becomes invalid.
- The breakout fails.
- The retest does not satisfy confirmation conditions.
- The configured setup timeout expires.
- The SQ9 anchor changes according to the validated anchor policy.
- The risk engine identifies an invalid trade.

A rejected or invalidated setup must never be executed automatically.

## 4.5 Configurable Strategy Parameters

Expose the following as configurable MT4 inputs:

- AnchorMode
- SignalTimeframe
- SQ9Angle
- SQ9Space
- PullbackCloseTolerancePoints
- BreakoutBufferPoints
- RetestTolerancePoints
- RetestCloseBufferPoints
- StopBufferPoints
- MaximumSetupBars
- MaximumRetestBars
- MaximumSpreadPoints
- MinimumRiskReward
- RiskPercentPerTrade
- MaximumOpenTrades

Use the original indicator's default settings where appropriate.

Do not invent mathematical defaults that are inconsistent with the source.

All tolerance parameters must be documented and independently configurable.

Do not silently optimize or change the user's strategy.

---

# 5. Jev API Integration

Use the supplied OpenCode Zen Jev documentation as the integration specification.

Do not assume Jev is available as a normal OpenCode coding model.

Do not attempt to invoke Jev using the OpenCode CLI model-selection interface.

It must be accessed through HTTP.

## 5.1 Endpoint

`POST https://opencode.ai/inference/systemone/v1/systemone`

Headers:

`Authorization: Bearer ${OPENCODE_API_KEY}`

`Content-Type: application/json`

Default model:

`jev-1.13-free`

Make the model configurable through environment variables.

Supported alternatives:

- jev-1.13
- jev-1.14

## 5.2 Credentials and Security

Read the API key from:

`process.env.OPENCODE_API_KEY`

Never:

- Hardcode API keys.
- Store API keys in MQL4 source.
- Commit secrets.
- Print Authorization headers.
- Include secrets in error messages.
- Expose secrets through API responses.

Use a `.env.example` only for documenting configuration names.

Do not require an npm dependency just to perform HTTP requests.

Use Node.js native `fetch()` as the default implementation.

## 5.3 Jev Decision Request

Send a structured JSON state containing:

- Symbol.
- Timeframe.
- Current market conditions.
- Recent price behavior.
- Market structure.
- Volatility.
- ATR.
- Spread.
- SQ9 origin.
- All relevant SQ9 angle levels.
- Setup progression.
- Pullback confirmation.
- Breakout confirmation.
- Retest confirmation.
- Direction.
- Entry price.
- Proposed SL.
- Proposed TP.
- Risk/reward.
- Relevant previous performance statistics.
- Setup identifier.
- Snapshot timestamp.

Only include information available at the time of the decision.

No future candle information or future trade outcomes are allowed in the decision snapshot.

## 5.4 Jev Questions

Implement a typed decision schema.

### Action

Type: `choice`

Possible options:

- BUY
- SELL
- NO_TRADE

Jev instructions:

Evaluate the supplied quantitative market snapshot and the validated SQ9 strategy setup.

Determine whether the proposed trading opportunity deserves approval.

Consider:

- Market structure.
- Trend alignment.
- Price momentum.
- Volatility conditions.
- SQ9 progression.
- Pullback quality.
- Breakout quality.
- Retest quality.
- Spread and execution conditions.
- Available historical performance context.

Choose BUY or SELL only when the corresponding candidate is valid and conditions are favorable.

Otherwise, choose NO_TRADE.

### Critical Risk

Type: `noul`

Question:

Does the supplied market snapshot indicate a critical condition that should prevent this trade from being executed?

### Setup Quality

Type: `score`

Use a five-level scale:

1. Very Poor
2. Poor
3. Acceptable
4. Strong
5. Excellent

This score represents Jev's qualitative assessment, not a statistically calibrated probability of success.

## 5.5 Decision Validation

Validate every Jev response before allowing further processing.

Requirements:

- Expected model identifier.
- Valid response structure.
- Expected answer keys.
- Valid choice value.
- Valid probability ranges.
- Valid score response.
- Valid request identifier.
- No duplicated response processing.

If Jev selects the opposite direction from the mechanically detected candidate, reject the trade rather than reversing the strategy.

If Jev chooses NO_TRADE, reject the setup.

If Jev returns malformed data, timeout, invalid probabilities, or an unexpected response, fail closed.

A failed Jev request must never result in an automatic trade.

Make the probability thresholds configurable.

Do not treat Jev confidence or choice probabilities as proven win probabilities.

Record all raw validated decision data and model usage where available.

---

# 6. Node.js Quant Bridge

Build a dedicated local HTTP service between MT4 and Jev.

Suggested directory:

`jev-bridge/`

Use Node.js 18+.

Avoid unnecessary dependencies.

## 6.1 Why a Bridge Is Required

MQL4's WebRequest function is synchronous.

Do not keep the MT4 EA waiting for a remote Jev API request to finish.

The bridge must process remote Jev requests independently and asynchronously.

## 6.2 HTTP Endpoints

Implement:

### Health Check

`GET /health`

Returns service status, configured Jev model, and connectivity status without exposing credentials.

### Submit Decision

`POST /v1/decisions`

Accepts a validated Quant snapshot.

Returns:

- Request ID.
- Status: PENDING.
- Submission timestamp.

The bridge starts the Jev request asynchronously.

### Get Decision

`GET /v1/decisions/:requestId`

Returns one of:

- PENDING
- COMPLETED
- REJECTED
- FAILED
- EXPIRED

Include the validated decision when completed.

Implement bounded request retention and expiration.

## 6.3 Bridge Reliability

Implement:

- Request validation.
- Idempotency.
- Request IDs.
- Timeout management.
- Bounded retries.
- Retry handling for transient network failures.
- Appropriate handling of rate limits.
- API error classification.
- Concurrent request limits.
- Structured logging.
- Graceful shutdown.
- Health checks.

Do not retry invalid authentication or malformed requests indefinitely.

Do not allow a timed-out request to become an executable trade later without revalidating its freshness and setup identity.

## 6.4 MT4 Communication

The EA should communicate only with the local bridge.

Use:

- Short-timeout local HTTP requests.
- Nonblocking job submission from the trading workflow's perspective.
- Periodic decision polling through OnTimer.
- A configurable polling interval.
- Unique request IDs.
- Stale-response rejection.

The EA must never issue repeated Jev requests for the same setup.

Document the MT4 WebRequest allowed-URL configuration.

Default local service:

`http://127.0.0.1:<configured-port>`

Keep the port configurable.

---

# 7. Quantitative Risk Management

Build an independent risk-management component.

It must remain authoritative regardless of Jev's output.

Required protections:

1. Configurable risk per trade.
2. Correct position sizing based on account currency and broker contract specifications.
3. Maximum spread.
4. Maximum open trades.
5. One trade per SQ9 setup.
6. Maximum daily loss.
7. Maximum drawdown.
8. Minimum risk/reward.
9. Minimum free margin.
10. Broker stop-level validation.
11. Minimum lot validation.
12. Maximum lot validation.
13. Slippage handling.
14. Duplicate order prevention.

SL and TP must originate from the validated SQ9 calculations.

The risk engine may reject a trade but may never move its SL or TP to an arbitrary location without an explicit configured rule.

Record every risk rejection with its reason.

Implement restart-safe trade and setup tracking.

---

# 8. Execution Modes and Safety

The initial system must not trade real money automatically.

Implement three execution modes:

### SIGNAL_ONLY

- Detect SQ9 setups.
- Request Jev decisions.
- Record approved and rejected opportunities.
- Never execute orders.

### PAPER

- Simulate entries and exits.
- Track virtual positions.
- Simulate relevant execution costs.
- Calculate hypothetical PnL.
- Record Jev decisions and risk rejections.
- Never send broker orders.

### BROKER

- Execute actual MT4 orders.
- Require explicit configuration.
- Require EnableLiveTrading to be explicitly enabled.
- Enforce all risk validations.
- Refuse startup when mandatory safety configuration is missing.

Default:

`ExecutionMode = PAPER`

`EnableLiveTrading = false`

Never silently switch execution modes.

Do not automatically enable live trading during development or testing.

---

# 9. Historical Backtesting and Jev Replay

A major architectural requirement:

MT4 Strategy Tester does not execute WebRequest calls.

Therefore, live Jev HTTP integration cannot be assumed to work inside historical Strategy Tester runs.

Implement separate testing paths.

## 9.1 SQ9 Core Backtesting

Backtest the deterministic strategy without requiring the Jev API.

Verify:

- Entry conditions.
- Exit conditions.
- SQ9 calculations.
- Anchor behavior.
- No look-ahead bias.
- No duplicate setups.
- Price-level consistency.

Use realistic spread, commission, slippage, and broker specifications.

## 9.2 Jev Mock Mode

Implement a deterministic mock decision provider for Strategy Tester.

Support recorded decision fixtures such as:

- BUY.
- SELL.
- NO_TRADE.
- Critical risk rejection.
- Invalid response.
- Missing response.

Mock behavior must be deterministic and reproducible.

## 9.3 Historical Jev Replay Pipeline

Implement an offline two-pass workflow:

Pass 1:

- Run the strategy against historical data.
- Export every qualified SQ9 candidate as a timestamped structured event.
- Include a stable event identifier and complete decision snapshot.

Pass 2:

- Use a Node.js replay utility to submit exported events to Jev.
- Store each response with its corresponding event identifier.
- Produce a versioned decision fixture file.

Pass 3:

- Rerun the historical simulation using the recorded Jev decisions.
- Match decisions to their original event identifiers.
- Reject missing, duplicated, mismatched, or stale decisions.

This permits historical Jev-assisted comparisons without executing HTTP requests from Strategy Tester.

Ensure Jev receives no future market information or future PnL information for historical decisions.

## 9.4 Required Performance Metrics

Calculate:

- Total trades.
- Winning trades.
- Losing trades.
- Win rate.
- Gross profit.
- Gross loss.
- Net profit.
- Profit factor.
- Expectancy.
- Average win.
- Average loss.
- Maximum drawdown.
- Average risk/reward.
- Long performance.
- Short performance.
- Monthly performance.
- Jev approval rate.
- Jev rejection rate.
- Performance by Jev quality classification.

Compare:

A. SQ9 strategy without Jev.

B. SQ9 strategy with Jev decisions.

C. SQ9 strategy with Jev decisions and additional configurable market filters.

Use chronological training, validation, and out-of-sample testing.

Include walk-forward evaluation where practical.

Do not claim profitability unless supported by out-of-sample results.

Avoid overfitting strategy parameters to historical data.

---

# 10. Decision Feedback and Quant Research

Build a persistent trade and decision journal.

Store:

- Setup ID.
- Timestamp.
- Symbol.
- Timeframe.
- Anchor.
- SQ9 levels.
- Market snapshot.
- Jev model.
- Jev action.
- Jev probabilities.
- Jev score.
- Critical-risk probability.
- API latency.
- API usage and cost when available.
- Entry.
- SL.
- TP.
- Actual execution price.
- Exit.
- PnL.
- Outcome.
- Exit reason.
- Rejection reasons.

Use structured JSONL or a suitable existing storage mechanism.

The journal must survive terminal restarts.

Implement a performance-analysis module that can generate:

- Jev approval versus rejection analysis.
- BUY versus SELL performance.
- Performance by symbol.
- Performance by timeframe.
- Performance by market regime.
- Performance by setup quality.
- Performance under different volatility conditions.
- Decision consistency.
- Repeated failure patterns.

Historical outcomes may be summarized and passed into future Jev state snapshots as additional context.

However, do not describe this as model training or automatic learning.

Jev itself does not update its internal weights through these requests.

---

# 11. Testing Strategy

Implement comprehensive tests.

## SQ9 Tests

- Validate 0°, 45°, 90°, and 360° calculations.
- Compare calculation outputs against the original indicator.
- Test bullish and bearish calculations.
- Test different symbols and decimal precisions.
- Test different timeframes.
- Test Space settings.
- Test anchor changes.
- Test confirmed versus unconfirmed candles.
- Test historical recalculation.

## Strategy Tests

- Valid bullish setup.
- Valid bearish setup.
- Missing 45° confirmation.
- Invalid pullback.
- Failed breakout.
- Failed retest.
- Successful retest.
- Timeout.
- Invalid anchor.
- Duplicate signal.
- Repeated tick.
- Terminal restart.
- Simultaneous setup protection.

## Jev Integration Tests

- Valid API response.
- BUY approval.
- SELL approval.
- NO_TRADE response.
- Opposite-direction response.
- High critical-risk probability.
- Invalid schema.
- HTTP 401.
- HTTP 429.
- HTTP 500.
- Timeout.
- Network failure.
- Duplicate request.
- Expired response.
- Invalid API key.
- Bridge unavailable.

Use mocked network responses for automated tests.

Never require a paid Jev API request just to execute the normal test suite.

## Risk Tests

- Correct lot sizing.
- Invalid SL distance.
- Invalid TP.
- Excessive spread.
- Insufficient margin.
- Exceeded daily loss.
- Maximum open trades.
- Broker lot constraints.
- Duplicate execution.

---

# 12. Documentation Deliverables

Produce or update the following documentation:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/INDICATOR_REVERSE_ENGINEERING.md`
- `docs/SQ9_STRATEGY_SPECIFICATION.md`
- `docs/JEV_INTEGRATION.md`
- `docs/RISK_MANAGEMENT.md`
- `docs/BACKTESTING.md`
- `docs/PAPER_TRADING.md`
- `docs/OPERATIONS.md`
- `docs/TESTING.md`

Adapt file paths to the existing repository structure rather than creating duplicate documentation.

Document how to:

- Compile the EA.
- Install the original indicator.
- Configure MT4.
- Start the Node.js bridge.
- Configure OPENCODE_API_KEY.
- Test Jev connectivity.
- Run SIGNAL_ONLY.
- Run PAPER.
- Run historical SQ9 backtests.
- Export and replay Jev decisions.
- Inspect decision logs.
- Configure risk parameters.

---

# 13. Engineering Standards

Follow the existing repository instructions.

Before making changes:

- Read CLAUDE.md.
- Read AGENTS.md if present.
- Read README.md.
- Inspect the entire repository structure.
- Inspect existing development and testing workflows.
- Identify available development skills and use relevant installed workflows.

Preserve existing conventions.

Additional requirements:

- Strict separation of responsibilities.
- Small, testable modules.
- Explicit interfaces.
- Deterministic calculations.
- Strong input validation.
- Structured logging.
- Clear error handling.
- No hardcoded credentials.
- No arbitrary magic numbers.
- No hidden trading behavior.
- No silent fallback to live execution.

Do not rewrite unrelated project components.

Do not delete existing user files.

Do not modify the original AbuHamzah indicator unless a documented technical necessity is discovered and explicitly justified. Prefer an independent EA-side implementation.

Avoid unnecessary npm dependencies.

Use Node.js built-in functionality where practical.

Keep the system maintainable and suitable for future quantitative research.

---

# 14. Recommended Implementation Phases

Execute the project in the following order.

### Phase 0 — Repository Discovery and Indicator Audit

- Inspect repository.
- Inspect indicator source.
- Extract mathematical behavior.
- Identify dependencies.
- Investigate repainting.
- Produce technical audit.

Exit criteria: The original indicator's calculation and anchor behavior are understood and documented.

### Phase 1 — SQ9 Mathematical Engine

- Implement reusable SQ9 calculations.
- Reproduce the original indicator's behavior.
- Validate all four angle levels.
- Validate bullish and bearish levels.
- Build calculation tests.

Exit criteria: SQ9 engine outputs match the reference indicator within documented numerical tolerances.

### Phase 2 — Deterministic Trading Strategy

- Implement the complete state machine.
- Implement bullish and bearish setups.
- Implement 45° close confirmation.
- Implement 90° breakout confirmation.
- Implement 90° retest confirmation.
- Implement 0° SL and 360° TP.
- Implement setup invalidation.
- Implement duplicate protection.

Exit criteria: Both directions work deterministically with no look-ahead bias.

### Phase 3 — Jev Decision Service

- Implement Node.js bridge.
- Implement Jev API client.
- Implement typed questions.
- Implement response validation.
- Implement decision persistence.
- Implement timeout and retry logic.
- Implement health checks.

Exit criteria: Jev decisions can be requested and retrieved reliably using the documented API.

### Phase 4 — MT4 Integration

- Implement local bridge communication.
- Implement job submission.
- Implement periodic result polling.
- Implement request correlation.
- Implement stale-result protection.
- Implement Jev state transitions.

Exit criteria: MT4 can reliably receive and validate Jev decisions without waiting for the remote API request to finish.

### Phase 5 — Risk and Execution

- Implement position sizing.
- Implement trade validation.
- Implement risk limits.
- Implement SIGNAL_ONLY.
- Implement PAPER.
- Implement guarded BROKER execution.

Exit criteria: No trade can be executed without strategy validation, valid Jev approval, and independent risk approval.

### Phase 6 — Backtesting and Historical Jev Replay

- Implement historical SQ9 backtesting.
- Implement deterministic Jev mock mode.
- Implement candidate event export.
- Implement Node.js Jev replay.
- Implement decision fixture import.
- Implement comparative performance reports.

Exit criteria: The system can compare SQ9-only and Jev-assisted trading using reproducible historical tests.

### Phase 7 — Paper Trading and Hardening

- Run continuous paper trading.
- Verify bridge stability.
- Verify restart recovery.
- Test API failure scenarios.
- Analyze decision quality.
- Analyze performance by market condition.
- Fix operational and trading defects.

Exit criteria: System behavior is reproducible, monitored, documented, and suitable for controlled evaluation.

---

# 15. Critical Acceptance Criteria

The implementation is NOT complete until all the following are satisfied.

1. Original AbuHamzah calculations are independently reproduced and validated.
2. Original indicator source remains preserved.
3. Bullish and bearish SQ9 setups work correctly.
4. The strategy follows the specified 0° → 90° → 45° → 90° → 360° progression.
5. Entry occurs only after breakout and confirmed retest.
6. Pullback confirmation requires candle close, not just a wick.
7. SL and TP are derived from the correct SQ9 levels.
8. Jev receives structured quantitative market context.
9. Jev returns validated structured decisions.
10. Jev cannot override SQ9 validity or risk controls.
11. API failures cannot produce unintended trades.
12. MT4 does not wait synchronously for remote Jev requests.
13. Strategy Tester works independently from live HTTP calls.
14. Historical Jev replay is reproducible.
15. Paper trading never sends real broker orders.
16. Live trading is disabled by default.
17. All important decisions are recorded and explainable.
18. All required documentation is available.
19. Tests cover critical strategy, integration, and risk paths.
20. No profitability claims are made without credible out-of-sample evidence.

---

# 16. Final Engineering Principle

Build this as a quantitative research and execution system, not as a collection of trading conditions.

The central architecture must remain:

**Market Data → SQ9 Quantitative Analysis → Jev Decision Intelligence → Independent Risk Validation → MT4 Execution → Performance Feedback**

SQ9 determines whether a legitimate strategy opportunity exists.

Jev evaluates whether that opportunity deserves approval.

Risk management determines whether the approved opportunity is safe and executable.

MT4 executes only after all required checks pass.

The entire process must be deterministic where mathematical calculations are involved, structured where AI decisions are involved, and measurable where trading performance is involved.

Start with repository discovery and the indicator reverse-engineering audit.

Do not skip the mathematical validation phase.

Do not enable live trading.

Do not assume the strategy is profitable.

Build, test, document, and validate every phase before proceeding to the next.
