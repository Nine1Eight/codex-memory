# AdTV Investor One-Pager

## What AdTV Is

AdTV is a verified-attention advertising network and settlement platform.

It turns ad viewing blocks into auditable revenue events, allocates a user earnings pool, and settles value daily through a production control plane.

## The Problem

Traditional ad systems have three recurring failures:

- attention is treated as an unverified impression
- user compensation is opaque or absent
- settlement is hard to audit and easy to manipulate

That creates waste for advertisers, weak incentives for users, and poor visibility for operators.

## The Solution

AdTV combines:

- verification of completed blocks
- revenue accounting
- CU-based user settlement
- mission-control operations UI

The system is designed to make attention verifiable, revenue traceable, and payout logic deterministic.

## How It Makes Money

AdTV uses a 55/45 split on verified revenue:

- 55% goes to the user pool
- 45% is retained by the platform

Additional revenue can come from:

- enterprise reporting
- managed service fees
- premium placement
- API access
- verification SLAs
- white-label licensing

## Why It Wins

The moat is operational and financial, not just technical:

- verified blocks create durable records
- settlement is auditable and rerunnable
- CU accounting creates a stable internal unit of value
- operators get a live control surface instead of spreadsheet-based close

## Customer Segments

### Advertisers

They buy qualified attention, fraud-resistant delivery, and clearer reporting.

### Users

They earn from verified viewing activity with a transparent settlement path.

### Operators

They run verification, monitor revenue, and execute daily close from one console.

## Product State

The current codebase includes:

- authenticated mission-control dashboard
- block verification endpoint
- summary, block, and settlement APIs
- PostgreSQL schema
- daily settlement logic
- containerized deployment path

## Economics

Core formulas:

- `gross_verified_revenue = sum(cpv)`
- `platform_revenue = gross_verified_revenue * 0.45`
- `user_pool = gross_verified_revenue * 0.55`
- `cu_rate = user_pool / total_cu`
- `usd_allocated = user_cu_earned * cu_rate`

This keeps the economics deterministic and auditable.

## Go-To-Market

Initial wedge:

- small advertiser pilot
- controlled user cohort
- manual verification oversight

Expansion path:

- repeat advertisers
- more daily blocks
- enterprise and partner distribution

## Key Risks

- verification fraud
- settlement integrity
- compliance and payout handling
- operational scaling before automation

## Bottom Line

AdTV is a verified-attention network with embedded settlement infrastructure.

If verified attention proves monetizable at scale, the business can expand as both:

- a managed marketplace
- a software/control-plane product
