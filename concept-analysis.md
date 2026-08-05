# Inference Futures Exchange — Concept Analysis

**Created:** 2026-08-03
**Status:** Brainstorming / Feasibility
**Author:** Frank Drebin for Des Martin

---

## The Concept

An exchange where:
- **Inference providers** sell future inference credits at a fixed price (forward selling capacity)
- **Investors** go long or short on inference futures (speculating on price direction)
- **Underlying asset:** AI inference tokens (not GPU hours)

This is a **two-sided marketplace** with a **derivatives layer** on top.

---

## Competitive Landscape

### Architect (architect.co)

The closest competitor. Key facts:

| Aspect | Architect | Des's Concept |
|--------|-----------|---------------|
| **Underlying** | GPU-hours (H200, B200, H100) | Inference tokens (model-agnostic) |
| **Settlement** | Cash-settled against their daily index | TBD (physical delivery or cash?) |
| **Regulation** | CFTC-regulated Designated Contract Market | TBD |
| **Structure** | Traditional exchange (NFA broker) | Onchain (proposed) |
| **Products** | GPU futures + metals + energy + power | Inference futures only |
| **Target users** | Neoclouds, hyperscalers, model labs, lenders, speculators | Same + crypto-native investors |
| **Forward curve** | Spot to 24 months | TBD |
| **Fees** | 0.15% settlement fee | TBD |
| **Live?** | Pre-onboarding, early access | Concept stage |

**Key difference:** Architect trades GPU-hours (hardware layer). Des's concept trades inference tokens (output layer). This is a meaningful distinction:
- GPU-hour futures hedge hardware costs but don't capture model efficiency gains
- Inference token futures hedge the actual cost of AI output, which is what businesses care about
- The paper argues inference tokens are the better commodity because they're what end-users actually consume

### The Paper (arXiv:2603.21690)

Yicai Xing, March 2026. Proposes the "Standard Inference Token" (SIT) framework.

**Key arguments:**
1. **Inference tokens are commodities** — fungible, standardized measurement (M tokens), large-scale trading ($10B+ market)
2. **Non-storable** — like electricity, produced and consumed simultaneously
3. **Token prices fell 40x** from 2023-2025 ($60/M to $1.50/M) but will spike when application demand explodes
4. **Electricity futures analogy** — closest analogue: non-storable, low short-term supply elasticity, time-varying demand
5. **Three-factor supply model:** energy cost, hardware efficiency, model efficiency
6. **Simulations show 62-78% reduction** in compute cost volatility for hedgers
7. **Price model:** mean-reverting jump-diffusion (prices revert to a declining trend but with sudden spikes)

**Contract design from the paper:**
- Standard Inference Token (SIT) = 1 million tokens at a standardized quality level
- Cash settlement against a daily reference index
- Margin system with initial + maintenance margins
- Market-maker regime for liquidity
- Contract months: monthly, quarterly, annual

---

## The Three Hard Questions

### 1. How to hold future sellers accountable if they renege on delivery?

**This is the hardest problem.** Options:

**Option A: Cash settlement only (Architect's approach)**
- No physical delivery. Futures settle against a daily index price.
- Sellers don't actually deliver inference. They post margin and settle in cash.
- Pro: Simpler, no delivery logistics, no reneging risk
- Con: Disconnect from physical reality. Doesn't help providers who actually want to sell future capacity.

**Option B: Physical delivery with escrow + slashing**
- Provider deposits collateral (stablecoin or SOL) into a smart contract when selling forward credits.
- If they deliver the inference credits by expiry, collateral is returned.
- If they fail to deliver, collateral is slashed and distributed to buyers.
- Delivery verification: buyer redeems credits via API call. Provider signs off on delivery. If buyer claims non-delivery, dispute resolution mechanism kicks in.
- Pro: Real accountability. Creates trust.
- Con: Complex. Hard to define "delivery" precisely (quality, latency, uptime requirements).

**Option C: Credit-based with reputation system (recommended)**
- Providers stake reputation/collateral proportional to their forward sales.
- Each provider has a public delivery track record onchain.
- Buyers can see historical delivery rates before purchasing.
- Failed deliveries slash collateral AND reduce reputation score.
- After enough failures, provider is delisted.
- Pro: Flexible, scalable, creates a trust signal
- Con: Needs bootstrapping the reputation system

**My recommendation: Start with cash settlement (Option A), add physical delivery (Option B) as a Phase 2 feature for providers who want it.** Cash settlement gets the market running. Physical delivery adds complexity that can be built once there's liquidity.

### 2. How does someone buy a future with confidence?

**The confidence problem has three layers:**

**Layer 1: Confidence in the counterparty (credit risk)**
- Onchain collateral/margin system — both sides post margin
- Smart contract auto-liquidates if margin falls below maintenance level
- Mark-to-market daily (like traditional futures)
- Exchange acts as central counterparty (CCP) — eliminates bilateral credit risk

**Layer 2: Confidence in the price (price discovery)**
- Need a transparent reference index for inference token prices
- The paper proposes a "Standard Inference Token" — define quality level, measurement method
- Index could be built from: actual API prices across major providers (OpenAI, Anthropic, Google, DeepSeek), weighted by market share
- Published daily, verifiable onchain
- Architect has their own "AI Exchange daily index" — this is the moat

**Layer 3: Confidence in the contract (legal/regulatory)**
- Traditional futures: CFTC regulation, NFA membership, clearinghouse guarantee
- Onchain futures: smart contract code IS the contract. But legal enforceability is unclear.
- Hybrid: CFTC-regulated entity + onchain settlement (Architect's model)
- Pure onchain: DAO/governance model, no regulatory backing. Riskier but more accessible.

**My recommendation:** The index is the real product. Whoever builds the most trusted inference price index wins. The exchange is just plumbing around the index.

### 3. Two-sided marketplace: how to get started?

**The cold start problem is the biggest risk.** Futures markets need:
1. Liquidity on both sides (buyers AND sellers)
2. Market makers willing to provide continuous quotes
3. Enough volume for price discovery to work

**Bootstrapping strategies:**

**Strategy A: Provider-first (supply-side)**
- Sign up 3-5 inference providers who want to forward-sell capacity
- These providers list forward contracts at their desired prices
- Investors come to buy because there's real supply at real prices
- Problem: investors won't come until there's liquidity, and liquidity needs investors

**Strategy B: Investor-first (demand-side)**
- Build the trading platform first
- Onboard crypto-native speculators who want AI exposure
- Use their demand to attract providers who see there are buyers
- Problem: without real providers, the market is pure speculation. No grounding in reality.

**Strategy C: Index-first (recommended)**
- Start by publishing a daily inference price index (free, transparent)
- Build trust in the index over 3-6 months
- Once the index is cited and used, launch futures that settle against it
- Providers and investors both come because the index is the reference point
- This is how oil futures (WTI index), electricity futures (PJM index), and carbon futures all developed

**Strategy D: Seed liquidity with market makers**
- Pay market makers to provide continuous bid/ask spreads
- Seed the order book with provider inventory
- Incentivize early adopters with fee rebates
- Standard crypto exchange playbook (what dYdX, Hyperliquid did)

**My recommendation: Strategy C (index-first) + Strategy D (seed liquidity).** Publish the index first. Then launch with seeded market maker liquidity and provider inventory.

---

## Onchain vs Offchain

### Why onchain?
- **Transparency:** All trades, positions, and settlement visible onchain
- **Global access:** Anyone can trade, no geographic restrictions (regulatory questions aside)
- **Programmatic settlement:** Smart contracts auto-settle, no counterparty risk
- **Composability:** Inference futures could be used as collateral for lending, insurance, etc.
- **Crypto-native audience:** Des's network and audience are crypto-native

### Why NOT onchain?
- **Regulation:** CFTC-regulated markets have legal enforceability. Onchain markets don't (yet).
- **Institutional adoption:** Traditional players (hedge funds, model labs) want regulated venues.
- **Latency:** Onchain settlement is slower than centralized matching. Solana is fast (~400ms finality) but traditional exchanges match in microseconds.

### Chain selection

| Chain | Speed | Ecosystem | Verdict |
|------|-------|-----------|---------|
| **Solana** | ~400ms finality, 65K TPS | Strong crypto trading ecosystem (Jupiter, Raydium) | Good for consumer-facing trading |
| **Base** | ~2s blocks, L2 on Ethereum | Coinbase-backed, growing DeFi | Good for institutional access |
| **Arbitrum** | ~250ms, L2 on Ethereum | Largest L2 DeFi ecosystem | Established infrastructure |
| **Aptos/Sui** | <1s finality, high throughput | Newer, less liquidity | Interesting tech, less ecosystem |

**My recommendation: Solana for the trading layer, Base or Arbitrum for institutional settlement.** But honestly, the chain matters less than the index and liquidity. Don't over-index on chain choice at this stage.

---

## Des's Concept vs Architect vs The Paper

| Dimension | Des's Concept | Architect | Paper (Xing 2026) |
|-----------|--------------|-----------|-------------------|
| **Underlying** | Inference credits (provider-issued) | GPU-hours (hardware) | Standard Inference Token (abstracted) |
| **Delivery** | Physical (credits) or cash | Cash-settled | Cash-settled (proposed) |
| **Infrastructure** | Onchain (Solana proposed) | Offchain (CFTC-regulated) | Theoretical |
| **Regulation** | TBD | CFTC Designated Contract Market | Discussed but not implemented |
| **Index** | TBD | Proprietary AI Exchange Index | Proposed SIT index |
| **Providers** | Direct sellers (forward selling) | Not directly involved | Theoretical market participants |
| **Investors** | Long/short speculators | CTAs, hedge funds, prop desks | Application-layer enterprises |
| **Live?** | Concept | Early access, pre-onboarding | Paper only |

---

## Honest Assessment

### What's strong about this idea:
1. **Inference tokens are a better underlying than GPU-hours.** Businesses care about the cost of inference output, not GPU rental. A GPT-4 token from an H100 and a GPT-4 token from a B200 are the same product to the consumer.
2. **The timing is right.** Inference costs are exploding as AI deployment scales. The paper's 62-78% volatility reduction for hedgers is compelling.
3. **Crypto-native angle differentiates from Architect.** Architect is going the traditional CFTC route. An onchain version captures a different audience (crypto traders, DeFi users, global access).
4. **Des's network.** Agentic CMO audience + crypto trading experience = right person to build this for the crypto-native segment.

### What's hard:
1. **Architect has a 12-18 month head start.** They're CFTC-regulated, have a live UI with forward curves, and are pre-onboarding. Catching up is expensive.
2. **The index is the moat, not the exchange.** Whoever builds the trusted inference price index wins. Building an exchange without owning the index means Architect (or someone else) can cut you off.
3. **Liquidity cold start is brutal.** Futures markets die without liquidity. Getting both sides trading simultaneously is the hardest problem in market microstructure.
4. **Physical delivery of inference is genuinely hard.** What does "delivery" mean? At what quality? What latency? What if the model is updated? These questions don't have easy answers.
5. **Regulatory risk.** Onchain derivatives face increasing scrutiny. The CFTC has been relatively crypto-friendly, but offering unregistered futures to US persons is illegal.

### What I'd actually do:

**Phase 1 (0-3 months): Build the index.**
- Publish a daily inference price index across major providers
- Track: OpenAI, Anthropic, Google, DeepSeek, Mistral, open-source hosting
- Weight by estimated market share
- Make it free, transparent, citable
- This is the asset that compounds in value over time

**Phase 2 (3-6 months): Build the exchange.**
- Onchain (Solana) for the crypto-native audience
- Cash-settled futures settling against the index
- Seed with market maker liquidity
- Target: crypto traders who want AI exposure

**Phase 3 (6-12 months): Add physical delivery.**
- Provider-forward contracts with collateralized delivery
- Reputation system for providers
- This is where the real differentiation from Architect happens

**Phase 4 (12+ months): Institutional bridge.**
- Apply for regulatory status (if the market has proven demand)
- Offer institutional access via a regulated entity
- Bridge onchain and offchain liquidity

---

## Open Questions

- [ ] Is this a hedge fund play (trade inference futures yourself) or an exchange play (build the marketplace)?
- [ ] Cash settlement or physical delivery first?
- [ ] Regulated or unregulated (onchain only)?
- [ ] What's the index methodology? Who calculates it?
- [ ] How to attract the first 5 inference providers?
- [ ] What's the relationship to Des's existing Agentic CMO / AI consultancy work?
- [ ] Does Warren Bluffet connect to this? (Warren tracks AI tokens on Solana, this trades AI inference)
