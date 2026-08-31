# AdTV Business Model

## 1. Executive Summary

AdTV is a verified-attention advertising network and settlement platform.

The core idea is simple:

- Advertisers pay for verified ad exposure.
- Users complete verified viewing blocks and earn value from the revenue pool.
- The platform verifies blocks, records revenue events, and settles earnings daily.

The current operating model in this repository uses a 55/45 revenue split:

- 55% of verified revenue is allocated to the user pool.
- 45% of verified revenue is retained by the platform.

The product is not just an ad server. It is a full control system for:

- block verification
- revenue accounting
- user settlement
- fraud reduction
- ops visibility
- payout reconciliation

## 2. Problem

Traditional ad models have four structural problems:

1. Attention is treated as an unverified impression instead of a validated event.
2. Users are not directly compensated in a transparent way.
3. Settlement is opaque and difficult to audit.
4. Fraud, duplicates, and replayed events distort revenue and payout integrity.

AdTV is designed to solve those problems by making verification and settlement first-class product features.

## 3. Product

AdTV consists of three layers:

1. Verification layer
- Confirms a completed block.
- Converts an observed user action into a verified revenue event.

2. Accounting layer
- Records block, revenue, CU, and settlement data.
- Keeps a durable record of what was verified and when.

3. Mission control layer
- Gives operators a live dashboard for summary metrics, block status, and settlement runs.
- Provides manual control for verifying blocks and running daily close.

## 4. Customers

### Primary customer: advertisers

Advertisers need:

- qualified user attention
- predictable pricing
- fraud-resistant delivery
- performance reporting
- access to a controlled inventory system

### Secondary customer: platform operators

Operators need:

- a way to verify blocks
- visibility into revenue and settlement status
- a daily close process
- auditability and error handling
- a control surface for operations

### End user: participants

Users are not the paying customer, but they are economically central.

They need:

- a transparent way to earn CU
- clear attribution of verified blocks
- reliable settlement
- confidence that payout logic is consistent and auditable

## 5. Value Proposition

### For advertisers

- Verified exposure instead of raw impression spam.
- Revenue tied to validated blocks.
- Cleaner attribution and less waste.
- More trust in spend quality.

### For users

- Visible compensation model.
- Daily or periodic settlement.
- Clear earning mechanics.
- A transparent unit of account in CU.

### For operators

- A simple operational workflow.
- A single source of truth for blocks, revenue, and settlements.
- A production control plane that can be audited.

## 6. Revenue Model

### Core revenue stream: platform share

The platform retains 45% of verified revenue.

Formula:

- `gross_verified_revenue = sum(cpv)`
- `platform_revenue = gross_verified_revenue * 0.45`
- `user_pool = gross_verified_revenue * 0.55`

This is the current live economic rule in the settlement logic.

### Secondary revenue streams

The platform can also add:

- enterprise reporting fees
- premium campaign placement fees
- managed service fees
- API access fees
- settlement acceleration fees
- verification SLA fees
- white-label licensing

These secondary streams are optional and can be introduced without changing the core settlement engine.

## 7. Unit Economics

### Current settlement economics

In the current model:

- verified revenue is the top-line economic event
- users are paid from a 55% pool
- the platform keeps 45%

### CU accounting

CU is the internal settlement unit.

In the current implementation:

- each verified block creates CU transactions
- settlement converts CU into USD allocation using the daily CU rate

Daily CU rate formula:

- `cu_rate = user_pool / total_cu`

Per-user allocation:

- `usd_allocated = user_cu_earned * cu_rate`

This gives the system a deterministic, auditable payout path.

### Margin profile

The platform margin is the 45% share before operating costs.

From that margin, the platform covers:

- infrastructure
- fraud prevention
- verification operations
- customer acquisition
- support
- compliance
- product and engineering

The model is economically viable if gross verified revenue scales faster than fixed overhead.

## 8. Cost Structure

### Fixed costs

- engineering
- product operations
- database and hosting
- logging and observability
- legal and compliance baseline
- admin and support tooling

### Variable costs

- payment or payout processing
- fraud review
- verification work
- customer support load
- cloud usage tied to traffic and settlement volume

### Strategic cost center

The main economic risk is not compute. It is verification integrity.

If verification quality fails, revenue quality fails.
If revenue quality fails, the payout pool becomes untrustworthy.

## 9. Go-To-Market

### Phase 1: controlled pilot

Target:

- a small number of advertisers
- a limited operator group
- a constrained user cohort

Goal:

- prove verified completion
- prove settlement correctness
- prove auditability
- prove advertiser willingness to spend

### Phase 2: repeatable supply

Target:

- recurring advertisers
- more blocks per day
- more users per settlement window

Goal:

- stabilize daily revenue
- reduce manual intervention
- improve conversion from verified block to repeat spend

### Phase 3: scale distribution

Target:

- agency buyers
- affiliate partners
- enterprise customers
- API or embedded integrations

Goal:

- move from manual ops to managed growth
- reduce dependency on direct founder sales
- increase repeatable revenue

## 10. Distribution Channels

Primary channels:

- direct sales
- partner relationships
- managed onboarding
- operator-led campaigns

Secondary channels:

- referral loops from advertisers
- user incentives tied to verified activity
- API and integration partners

## 11. Retention Model

### Advertiser retention

Advertisers stay if:

- verified inventory performs
- reporting is trusted
- pricing is predictable
- fraud is low
- settlement and delivery are stable

### User retention

Users stay if:

- earning is clear
- settlement is reliable
- interface friction is low
- payouts are predictable

### Operator retention

Operators stay if:

- mission control is useful
- daily close is simple
- exceptions are visible
- audits are easy

## 12. Competitive Moat

AdTV’s moat is not generic ad inventory. It is the combination of:

- verified block logic
- settlement accounting
- payout transparency
- operator control surface
- an internal attention unit (CU)
- historical settlement data

That creates switching cost because the system is both:

- operational
- financial

If a customer adopts the verification and settlement workflow, moving away means losing continuity in records and payout logic.

## 13. Risks

### Fraud and abuse

Risk:

- fake blocks
- replayed events
- duplicate settlements

Mitigation:

- verification controls
- unique settlement keys
- idempotent close
- audit logging

### Compliance risk

Risk:

- payout, tax, or advertising compliance issues
- privacy and consumer-protection concerns

Mitigation:

- legal review
- data minimization
- clear terms and disclosures
- payout record retention

### Unit economics risk

Risk:

- user pool exceeds usable margin after costs
- spend quality declines

Mitigation:

- keep platform share sufficient for overhead
- monitor gross margin per verified block
- enforce campaign quality thresholds

### Operational risk

Risk:

- manual verification becomes a bottleneck
- settlement errors

Mitigation:

- automation
- observability
- test coverage
- strict readiness checks

## 14. Key Metrics

### Revenue metrics

- verified revenue per day
- platform share per day
- user pool per day
- average CPV
- revenue per advertiser

### Operations metrics

- open blocks
- verified blocks
- settlement success rate
- settlement re-run count
- error rate

### Product metrics

- time to verify
- time to settle
- blocks per user
- advertiser repeat rate
- user retention

## 15. Operational Workflow

1. An advertiser campaign is loaded into the system.
2. A block of ads is served or tracked.
3. The block is verified.
4. Revenue events are recorded.
5. CU transactions are issued.
6. Daily settlement calculates the pool.
7. User settlements are written.
8. Mission control displays the result.
9. Operators audit exceptions if needed.

## 16. Technical-to-Business Mapping

The codebase maps directly to the business model:

- `blocks` represent verified attention sessions.
- `revenue_events` represent monetized exposure.
- `cu_transactions` represent internal earning allocation.
- `daily_revenue_pools` represent the platform/user split.
- `user_settlements` represent the payout record.
- mission control represents the operator workflow.

This is important because the business model is embedded in the data model, not just in a pitch deck.

## 17. Financial Assumptions

These are reasonable initial assumptions for the current model:

- verified revenue is the primary source of truth
- 45% platform share funds the business
- 55% user pool funds participant earnings
- settlement is daily
- revenue quality improves with verification controls

If the business scales, the platform may later rebalance:

- platform share
- payout frequency
- premium service pricing
- enterprise fees

## 18. Expansion Paths

### Path A: SaaS control plane

License the mission-control and settlement workflow to other verified-attention businesses.

### Path B: managed marketplace

Run the ad network directly and retain platform share plus service fees.

### Path C: enterprise verification engine

Sell the verification, accounting, and settlement system as infrastructure.

### Path D: hybrid marketplace + software

Operate the network while offering the control plane as a productized layer.

## 19. Strategic Recommendation

The strongest path is the hybrid model:

- operate the network to generate first-party data and revenue
- productize the control plane for enterprise expansion
- keep settlement and verification logic as the core moat

That gives the business both:

- immediate cash-flow from marketplace economics
- long-term software defensibility

## 20. Bottom Line

AdTV is a verified-attention business with a built-in accounting engine.

The business works if it can consistently prove three things:

1. Advertisers will pay for verified attention.
2. Users will participate when settlement is transparent.
3. The platform can keep verification and payout logic trustworthy at scale.

If those hold, the model can scale as both:

- a managed ad marketplace
- a software/control-plane business
