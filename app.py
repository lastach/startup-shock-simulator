"""
Startup Financials Simulator — rigorous financial decision-making for founders.

You run ThermaLoop (smart-ventilation retrofit, SaaS+hardware hybrid) through
5 weeks of financial decisions. Each decision modifies a forward-projected
cash-flow and unit-economics model. There are no generic "morale" metrics —
every lever is a financial lever with a modeled consequence.

Financial model:
  - Weekly P&L: MRR, gross margin, S&M spend, G&A, net burn
  - Cash walk: beginning cash + collections - disbursements = ending cash
  - Unit economics: CAC, gross-margin-based LTV, LTV:CAC, payback months
  - Forward runway: months to zero cash given current net burn and growth rate
  - Failure states: payroll default, covenant breach, negative gross margin,
    LTV:CAC < 1 for two consecutive weeks (value-destruction)
"""

import streamlit as st
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import copy

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================

st.set_page_config(
    page_title="Startup Financials Simulator",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .crisis-card {
        border-left: 5px solid #7B2D8E;
        padding: 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #f0e6ff 100%);
        border-radius: 8px;
        margin: 15px 0;
    }
    .metric-box {
        text-align: center;
        padding: 14px 10px;
        border-radius: 8px;
        background: #f8f9fa;
        font-weight: 600;
    }
    .metric-box .label { font-size: 12px; color: #666; font-weight: 600; }
    .metric-box .value { font-size: 22px; font-weight: 700; }
    .metric-box .sub { font-size: 11px; color: #888; margin-top: 2px; }
    .kpi-good { color: #15803d; }
    .kpi-warn { color: #b45309; }
    .kpi-bad  { color: #b91c1c; }
    .option-panel {
        padding: 12px 14px;
        margin: 8px 0;
        border-left: 4px solid #7B2D8E;
        background: #f8f4ff;
        border-radius: 4px;
    }
    .impact-positive { color: #15803d; font-weight: 700; }
    .impact-negative { color: #b91c1c; font-weight: 700; }
    .impact-neutral  { color: #a16207; font-weight: 700; }
    h1, h2, h3 { color: #7B2D8E; }
    .formula {
        background: #f3f4f6; padding: 6px 10px; border-radius: 4px;
        font-family: ui-monospace, Menlo, monospace; font-size: 12px;
        color: #374151;
    }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# FINANCIAL MODEL
# ============================================================================

@dataclass
class Financials:
    """Forward-projected financial state. All $ in USD, revenue per month."""
    # Revenue
    mrr: float = 22_000.0                 # current monthly recurring revenue
    customers: int = 275                  # paying customers
    arpa_month: float = 80.0              # avg revenue per account / month (~$960/yr)
    gross_margin: float = 0.62            # blended COGS (hardware+SaaS hosting+support)
    monthly_churn: float = 0.035          # logo churn
    monthly_growth_rate: float = 0.06     # net new MRR growth rate

    # Cash
    cash: float = 220_000.0               # post-seed cash position
    ar_outstanding: float = 0.0           # accounts receivable
    debt_principal: float = 0.0           # venture debt principal
    debt_rate_annual: float = 0.0         # debt APR
    debt_covenant_min_cash: float = 0.0   # covenant floor

    # Cap table
    fully_diluted_shares: float = 10_000_000.0
    founder_ownership: float = 0.75       # fraction owned by founder(s) post-seed
    post_money_valuation: float = 6_000_000.0  # post-seed valuation mark

    # Cost structure (monthly)
    headcount: int = 6                    # fully-loaded incl founder
    avg_fully_loaded_comp_mo: float = 7_500.0   # per head, incl payroll tax/benefits
    other_ga_mo: float = 4_500.0          # tools, rent, legal, accounting
    sm_spend_mo: float = 4_000.0          # sales & marketing
    cac: float = 420.0                    # current blended CAC
    rbf_repayment_mo: float = 0.0         # revenue-based financing repayment/mo
    rbf_cap_remaining: float = 0.0        # remaining RBF balance

    # Derived state for learner visibility
    survival_streak_neg_unit_econ: int = 0
    notes: List[str] = field(default_factory=list)

    def opex_month(self) -> float:
        return (self.headcount * self.avg_fully_loaded_comp_mo
                + self.other_ga_mo
                + self.sm_spend_mo
                + self.rbf_repayment_mo
                + (self.debt_principal * self.debt_rate_annual / 12.0))

    def cogs_month(self) -> float:
        return self.mrr * (1 - self.gross_margin)

    def gross_profit_month(self) -> float:
        return self.mrr * self.gross_margin

    def net_burn_month(self) -> float:
        """Negative = burning cash; positive = cash-flow-positive."""
        return self.gross_profit_month() - self.opex_month()

    def ltv(self) -> float:
        """LTV = ARPA × gross_margin / monthly_churn (SaaS steady-state)."""
        if self.monthly_churn <= 0:
            return float("inf")
        return self.arpa_month * self.gross_margin / self.monthly_churn

    def ltv_cac(self) -> float:
        if self.cac <= 0:
            return float("inf")
        return self.ltv() / self.cac

    def payback_months(self) -> float:
        """CAC / (ARPA × gross_margin). Months to recover CAC at gross margin."""
        gp_per_customer_mo = self.arpa_month * self.gross_margin
        if gp_per_customer_mo <= 0:
            return float("inf")
        return self.cac / gp_per_customer_mo

    def runway_months(self) -> float:
        """
        Forward runway: simulate forward with current growth rate and net burn,
        stop when cash goes below covenant (default 0). This captures the fact
        that growing MRR can extend runway nonlinearly.
        """
        cash = self.cash
        mrr = self.mrr
        g = self.monthly_growth_rate
        gm = self.gross_margin
        floor = max(0.0, self.debt_covenant_min_cash)
        months = 0
        # Fixed costs approximation
        fixed = (self.headcount * self.avg_fully_loaded_comp_mo
                 + self.other_ga_mo
                 + self.sm_spend_mo
                 + self.rbf_repayment_mo
                 + (self.debt_principal * self.debt_rate_annual / 12.0))
        # Project up to 36 months
        for _ in range(36):
            gp = mrr * gm
            net = gp - fixed
            cash += net
            mrr = mrr * (1 + g)
            months += 1
            if cash <= floor:
                return months - max(0.0, (cash - floor) / max(1.0, fixed - gp)) if (fixed - gp) > 0 else float(months)
        return 36.0  # cap at 36

    def runway_label(self) -> Tuple[str, str]:
        r = self.runway_months()
        if r >= 18:
            return (f"{r:.1f} mo", "kpi-good")
        if r >= 9:
            return (f"{r:.1f} mo", "kpi-warn")
        return (f"{r:.1f} mo", "kpi-bad")

    def apply_monthly_step(self, weeks: int = 1):
        """
        Advance the model by `weeks` weeks. We apply monthly growth/churn as a
        proportional weekly step so a 1-week decision has 1-week of compounding.
        """
        frac = weeks / 4.33  # weeks per month
        g = (1 + self.monthly_growth_rate) ** frac - 1
        c = (1 + self.monthly_churn) ** frac - 1   # churn compounds
        # New MRR from growth (gross adds implied by growth rate and churn)
        new_mrr = self.mrr * (g + c)
        # Customer count tracks MRR if ARPA constant
        self.mrr = max(0.0, self.mrr * (1 + g))
        # Net cash impact = gross profit - opex, scaled to the week fraction
        self.cash += (self.gross_profit_month() - self.opex_month()) * frac
        # Update customers to match new MRR at current ARPA
        if self.arpa_month > 0:
            self.customers = int(round(self.mrr / self.arpa_month))
        # Track consecutive weeks of negative unit economics
        if self.ltv_cac() < 1.0:
            self.survival_streak_neg_unit_econ += 1
        else:
            self.survival_streak_neg_unit_econ = 0


# ============================================================================
# DECISION SCENARIOS — each is a financial decision with modeled effects
# ============================================================================

# Each decision has:
#   title, setup (narrative), and a dict of options.
# Each option has a `apply(fin)` function that mutates a Financials dataclass,
# plus `description`, `tradeoff` (explicit tradeoff text), and `why_it_works`
# (the financial mechanism being tested).

DECISIONS = {
    1: {
        "title": "Week 1 — Pricing Decision",
        "narrative": (
            "You're at $22K MRR / 275 customers / 3.5% monthly churn. Your ACV is "
            "$960/year. A peer raised prices 20% and saw no net churn; your board "
            "is pushing you to test it. Your CAC is $420 and LTV:CAC is ~3.4 — just "
            "above the institutional threshold, but fragile."
        ),
        "decision_question": "How do you move price?",
        "options": {
            "A": {
                "title": "Raise prices 20% on new customers only; grandfather existing",
                "tradeoff": "Higher new-MRR lift, slower than blanket increase; no churn spike from existing base.",
                "why": "ARPA lift raises LTV proportionally; grandfathering avoids churn shock. "
                       "LTV:CAC improves mostly on new cohorts — takes ~1 cohort to see impact.",
                "apply": lambda f: _raise_price_new_only(f),
            },
            "B": {
                "title": "Raise prices 20% across the board, effective next cycle",
                "tradeoff": "Fastest ARPA lift; modeled ~15% churn spike on existing base for 1 cycle.",
                "why": "Higher ARPA × gross margin / churn = LTV lift. But short-term churn "
                       "spike hurts MRR and your growth rate until the base reprices.",
                "apply": lambda f: _raise_price_blanket(f),
            },
            "C": {
                "title": "Cut prices 15% to accelerate customer acquisition",
                "tradeoff": "Faster logo growth; LTV compresses; margin thin; CAC payback lengthens.",
                "why": "You're trading ARPA for volume. Only works if acquisition velocity "
                       "more than offsets ARPA compression — rarely true below 40% margin.",
                "apply": lambda f: _cut_price(f),
            },
            "D": {
                "title": "Hold prices; invest in cross-sell/expansion revenue",
                "tradeoff": "Preserves base; slower to improve LTV:CAC; depends on product surface.",
                "why": "Expansion revenue is the highest-leverage LTV play when it works — "
                       "but you need a product surface (add-on, tier, seat expansion) to cross-sell into.",
                "apply": lambda f: _invest_expansion(f),
            },
        },
    },
    2: {
        "title": "Week 2 — Cost Structure",
        "narrative": (
            "Your monthly opex is running ~${opex:.0f} ({headcount} heads × ~$7.5K "
            "fully-loaded + ~$4.5K G&A + ~$4K S&M). Gross profit is ~${gp:.0f}/mo. "
            "Net burn ~${burn:.0f}/mo. Your runway is {runway:.1f} months at current "
            "growth rate. The board wants 18+ months before the next raise."
        ),
        "decision_question": "Where do you cut?",
        "options": {
            "A": {
                "title": "Lay off 2 team members (20% reduction), refocus on core product",
                "tradeoff": "Immediate burn reduction ~$17K/mo; slower product velocity; morale hit.",
                "why": "Headcount is usually the largest fixed cost. Fully-loaded cost "
                       "(comp × 1.25-1.35 for tax+benefits) is the real number — not base salary.",
                "apply": lambda f: _layoff_two(f),
            },
            "B": {
                "title": "Across-the-board 15% temporary salary cut, no layoffs",
                "tradeoff": "~$11K/mo savings; team intact; real attrition risk for top performers.",
                "why": "Preserves optionality on team but creates adverse selection — your best "
                       "people have outside options and leave first. Only works if paired with equity refresh.",
                "apply": lambda f: _salary_cut(f),
            },
            "C": {
                "title": "Renegotiate vendor contracts + cut discretionary spend only",
                "tradeoff": "~$2-3K/mo savings; preserves team and capacity; doesn't meaningfully move runway.",
                "why": "Vendor savings are real but small. If your cash problem is measured in "
                       "months of runway, trimming SaaS tools won't fix it.",
                "apply": lambda f: _vendor_cuts(f),
            },
            "D": {
                "title": "Don't cut; accelerate growth to outpace burn",
                "tradeoff": "No cash saved; requires growth rate to rise materially; high-risk.",
                "why": "'Grow into the burn' only works if your LTV:CAC is already healthy (≥3). "
                       "If LTV:CAC is <3, growing multiplies losses.",
                "apply": lambda f: _no_cut(f),
            },
        },
    },
    3: {
        "title": "Week 3 — Funding Decision",
        "narrative": (
            "You've got 3 live term sheets and a fourth option. Cash is ${cash:,.0f}, "
            "runway {runway:.1f} months. Your current post-money mark is implicit "
            "(last SAFE valued you at $6M). The deal terms below reflect realistic "
            "2024-era pricing for a seed-stage SaaS at your metrics."
        ),
        "decision_question": "Which capital do you take?",
        "options": {
            "A": {
                "title": "$500K priced seed extension at $5M pre ($5.5M post) — 9.1% dilution",
                "tradeoff": "Clean equity; valuation below last SAFE cap (mild down-round signal); dilutive.",
                "why": "Priced rounds set a mark and reset the option pool. 9.1% dilution for "
                       "~8 months of runway. Compare: would you take the same dilution for the same runway today?",
                "apply": lambda f: _priced_seed(f),
            },
            "B": {
                "title": "$300K SAFE at $8M cap, 20% discount — defer pricing to Series A",
                "tradeoff": "No immediate dilution; stacks on existing SAFEs; conversion math gets complex.",
                "why": "SAFEs compound — at Series A, all uncapped SAFEs convert at the A cap, "
                       "all capped SAFEs convert at their cap. Stacked SAFEs can cause 25%+ hidden dilution.",
                "apply": lambda f: _safe_note(f),
            },
            "C": {
                "title": "$300K venture debt at 12% APR, 24-month term, 5% warrant coverage, $50K min-cash covenant",
                "tradeoff": "No equity dilution upfront; interest is real cash out; covenant can force sale in a down cycle.",
                "why": "Venture debt is senior to equity in liquidation. Interest ($3K/mo here) hits "
                       "operating cash. Covenant breach = lender can accelerate. Cheap if you hit plan; brutal if you don't.",
                "apply": lambda f: _venture_debt(f),
            },
            "D": {
                "title": "$200K revenue-based financing — repay 2.5× from 8% of monthly revenue",
                "tradeoff": "Non-dilutive; repayment scales with revenue; expensive in the fast-growth case.",
                "why": "Effective APR depends on revenue trajectory. Grow fast → you repay the 2.5× "
                       "cap quickly → implied APR becomes 40%+. Grow slowly → cheap, but you're starved for growth capital.",
                "apply": lambda f: _rbf(f),
            },
        },
    },
    4: {
        "title": "Week 4 — Accounts Receivable Crunch",
        "narrative": (
            "Your largest customer (18% of MRR, ~$3,960/mo) is 65 days past due on a "
            "$23,760 AR balance. Their AP contact isn't responding. You're DSO 47 days on "
            "the rest of your book. A single-customer AR problem at your scale is a "
            "financial-control problem, not a customer problem."
        ),
        "decision_question": "How do you collect?",
        "options": {
            "A": {
                "title": "Factor the AR with a receivables firm — get $21,384 (10% fee) in 5 days",
                "tradeoff": "Immediate cash; 10% fee = $2,376 hit; customer relationship unaffected.",
                "why": "Factoring converts AR → cash at a discount. At 10%/60-day cycle, "
                       "annualized factoring cost is ~60%. Expensive, but cheap vs. running out of cash.",
                "apply": lambda f: _factor_ar(f),
            },
            "B": {
                "title": "Offer 5% early-pay discount ($1,188) for immediate payment",
                "tradeoff": "~$22,572 in 7-14 days; customer-friendly; sets a precedent you can't undo.",
                "why": "Early-pay discounts become the expectation. Once you offer 5% once, "
                       "you're likely to see 30% of customers request it. Budget for it going forward.",
                "apply": lambda f: _early_pay_discount(f),
            },
            "C": {
                "title": "Escalate to CFO with collections letter, suspend service if no response in 14 days",
                "tradeoff": "Full recovery if successful; ~50% probability of churning them entirely.",
                "why": "Leverage works when you have leverage. At 18% of MRR, if they churn, "
                       "your MRR drops ~$3,960/mo — and it raises the diligence question of whether "
                       "the business is too concentrated (customer concentration is a red flag).",
                "apply": lambda f: _escalate_collections(f),
            },
            "D": {
                "title": "Write it off, refocus on diversifying the book",
                "tradeoff": "Bad-debt hit $23,760; accept customer concentration was the real problem; fast moving on.",
                "why": "Writing off bad debt is GAAP-compliant but burns cash you can't get back. "
                       "The real lesson: 18%-of-MRR concentration was the underlying risk. Fix *that*.",
                "apply": lambda f: _writeoff(f),
            },
        },
    },
    5: {
        "title": "Week 5 — Growth Capital Allocation",
        "narrative": (
            "You have ~$40K of discretionary capital you can deploy this quarter. Your "
            "current LTV:CAC is {ltv_cac:.2f}, payback {payback:.1f} months. Each option "
            "below is a modeled allocation — the 'right' answer depends on your unit economics."
        ),
        "decision_question": "Where do you deploy the $40K?",
        "options": {
            "A": {
                "title": "Hire 1 AE at $40K ramp (3 months); assume quota = 15 new customers/quarter",
                "tradeoff": "Adds $10K/mo fully-loaded cost permanently; MRR lift +$1,000/mo after ramp.",
                "why": "AE ROI math: (15 customers × $67 ARPA × 12 × margin) / ($10K × 12) ≈ 0.75x in year 1. "
                       "Sales hires require 12+ months to pay back — fund only if the playbook is repeatable.",
                "apply": lambda f: _hire_ae(f),
            },
            "B": {
                "title": "Double paid-acquisition spend for 2 months ($40K); measure cohort payback",
                "tradeoff": "Short experiment; answers 'does CAC hold at 2× volume?' question.",
                "why": "CAC is rarely constant with scale — usually rises 20-50% as you exhaust "
                       "the best channels. This test is diagnostic: if CAC holds, scale further; "
                       "if CAC rises, find a new channel before spending more.",
                "apply": lambda f: _double_paid(f),
            },
            "C": {
                "title": "Invest in retention/expansion — reduce monthly churn from 3.5% to 2.5%",
                "tradeoff": "$40K over 2 quarters; direct LTV lift ~40%; slower top-of-funnel growth.",
                "why": "LTV lift from churn reduction: 3.5% → 2.5% is a 40% LTV lift. At current ARPA "
                       "and margin, that's worth +$290 LTV per customer. With 180 customers, $52K "
                       "book-value lift. Retention is the highest-ROI lever in SaaS.",
                "apply": lambda f: _invest_retention(f),
            },
            "D": {
                "title": "Hold the cash — extend runway, wait for better market conditions",
                "tradeoff": "+1.5 months of runway; no growth lift; signals caution to next round.",
                "why": "Cash is optionality. Holding is the right call when your LTV:CAC is below "
                       "1 (growing would destroy value), or when you're within 3 months of a raise. "
                       "Otherwise, idle cash is a drag on returns.",
                "apply": lambda f: _hold_cash(f),
            },
        },
    },
}


# ============================================================================
# DECISION MECHANICS — each mutates Financials with modeled effects
# ============================================================================

def _raise_price_new_only(f: Financials):
    """+20% ARPA applies only to new customers; modeled via gradual ARPA lift."""
    # Effective ARPA blends: existing base at old ARPA, new adds at +20%.
    # Approximate steady-state: ARPA climbs 5% per month as base rolls over.
    f.arpa_month *= 1.05
    f.mrr = f.customers * f.arpa_month
    # CAC unchanged; LTV rises via ARPA → gross margin effect.
    f.notes.append("Price +20% on new; ARPA lift ~5% this week as cohorts turn.")


def _raise_price_blanket(f: Financials):
    """+20% ARPA on existing; +15% churn spike for this cycle."""
    f.arpa_month *= 1.20
    churn_before = f.monthly_churn
    f.monthly_churn *= 1.50  # one-time spike (modeled for this step)
    lost_mrr = f.mrr * f.monthly_churn * 0.23  # weekly fraction of monthly churn
    f.mrr = max(0, f.mrr * 1.20 - lost_mrr)
    f.customers = int(f.mrr / f.arpa_month) if f.arpa_month > 0 else f.customers
    # Revert churn to normal (the spike was one-time)
    f.monthly_churn = churn_before * 1.05  # residual elevation
    f.notes.append(f"Blanket +20% price; churn spike to {f.monthly_churn*100:.1f}% this cycle.")


def _cut_price(f: Financials):
    """-15% ARPA, +25% acquisition velocity, CAC holds, growth rate rises."""
    f.arpa_month *= 0.85
    f.mrr = f.customers * f.arpa_month
    f.monthly_growth_rate = min(0.15, f.monthly_growth_rate * 1.25)
    # LTV compresses proportional to ARPA
    f.notes.append("Cut price 15%; ARPA down; modeled +25% gross-add velocity.")


def _invest_expansion(f: Financials):
    """ARPA lift over time via cross-sell; small up-front S&M investment."""
    f.arpa_month *= 1.07   # 7% expansion revenue lift this step
    f.mrr = f.customers * f.arpa_month
    f.sm_spend_mo += 500   # +$500/mo for cross-sell motion
    f.notes.append("Expansion revenue play: +7% ARPA, +$500/mo S&M for cross-sell motion.")


def _layoff_two(f: Financials):
    """Remove 2 heads; -$17K/mo burn; -25% product velocity (modeled as growth rate hit)."""
    f.headcount = max(2, f.headcount - 2)
    # Growth rate takes a modeled ~20% relative hit (less product velocity)
    f.monthly_growth_rate *= 0.80
    # One-time severance: 4 weeks comp
    f.cash -= 2 * f.avg_fully_loaded_comp_mo * (4/4.33)  # ~1 month severance each
    f.notes.append("Laid off 2; ~$17K/mo burn cut; growth rate -20%; 1-mo severance paid.")


def _salary_cut(f: Financials):
    """-15% comp across board; attrition risk of 1 head in ~50% of scenarios (modeled deterministically as 0.5 head)."""
    f.avg_fully_loaded_comp_mo *= 0.85
    # Modeled attrition: expected 0.5 heads lost; approximate as -0.15 growth rate impact
    f.monthly_growth_rate *= 0.90
    f.notes.append("15% salary cut; growth rate -10% from modeled attrition risk.")


def _vendor_cuts(f: Financials):
    f.other_ga_mo = max(2500, f.other_ga_mo - 2500)
    f.notes.append("Vendor/tool cuts: -$2.5K/mo G&A.")


def _no_cut(f: Financials):
    # Double down on growth — +$3K/mo to S&M
    f.sm_spend_mo += 3000
    # Growth rate rises IF LTV:CAC >= 3 (real in-model gating), else stays flat
    if f.ltv_cac() >= 3.0:
        f.monthly_growth_rate = min(0.15, f.monthly_growth_rate + 0.02)
        f.notes.append("No cuts; +$3K/mo S&M; LTV:CAC≥3 so growth rate rises +2pp.")
    else:
        # Growing with bad unit economics = burning faster without growth response
        f.notes.append("No cuts; +$3K/mo S&M; LTV:CAC<3 so growth rate does NOT respond — "
                       "you're burning faster without the top-line payoff.")


def _priced_seed(f: Financials):
    f.cash += 500_000
    # Dilution: new shares issued
    new_shares = f.fully_diluted_shares * (0.091 / (1 - 0.091))
    f.fully_diluted_shares += new_shares
    f.founder_ownership *= (1 - 0.091)
    f.post_money_valuation = 5_500_000
    f.notes.append("Priced seed extension: +$500K cash, 9.1% dilution, post-money $5.5M.")


def _safe_note(f: Financials):
    f.cash += 300_000
    # SAFE doesn't dilute now; track cap for future conversion
    f.notes.append("SAFE: +$300K cash, no dilution yet. $8M cap stacks with existing SAFEs — "
                   "at Series A this can compound to 20%+ hidden dilution.")


def _venture_debt(f: Financials):
    f.cash += 300_000
    f.debt_principal = 300_000
    f.debt_rate_annual = 0.12
    f.debt_covenant_min_cash = 50_000
    # 5% warrant coverage on principal = $15K in warrants (modeled as future dilution ~0.27%)
    f.founder_ownership *= (1 - 0.0027)
    f.notes.append("Venture debt: +$300K cash, 12% APR (~$3K/mo interest), $50K min-cash "
                   "covenant, 5% warrant coverage (~0.3% founder dilution).")


def _rbf(f: Financials):
    f.cash += 200_000
    f.rbf_cap_remaining = 200_000 * 2.5   # $500K total repayment
    f.rbf_repayment_mo = f.mrr * 0.08
    f.notes.append(f"RBF: +$200K cash; 8% of MRR = ${f.rbf_repayment_mo:.0f}/mo repayment until "
                   f"${f.rbf_cap_remaining:,.0f} paid.")


def _factor_ar(f: Financials):
    f.cash += 21_384
    f.ar_outstanding = max(0, f.ar_outstanding - 23_760)
    f.notes.append("Factored AR: +$21,384 cash now (vs. $23,760 face). $2,376 fee = "
                   "~60% annualized cost — acceptable if the alternative is insolvency.")


def _early_pay_discount(f: Financials):
    f.cash += 22_572
    f.ar_outstanding = max(0, f.ar_outstanding - 23_760)
    # Set precedent: future billings leak ~1% on expected early-pay adoption
    f.arpa_month *= 0.99
    f.mrr = f.customers * f.arpa_month
    f.notes.append("Early-pay discount: +$22,572. Modeled -1% future ARPA from precedent leakage.")


def _escalate_collections(f: Financials):
    # Expected value: 50% recover fully, 50% churn
    recovered = 23_760 * 0.5
    churn_mrr_loss = 3_960 * 0.5
    f.cash += recovered
    f.mrr -= churn_mrr_loss
    f.customers = int(f.mrr / f.arpa_month) if f.arpa_month > 0 else f.customers
    f.notes.append(f"Escalation: $11,880 recovered (expected value); $1,980/mo MRR lost "
                   f"(expected value) from 50% churn probability.")


def _writeoff(f: Financials):
    f.ar_outstanding = max(0, f.ar_outstanding - 23_760)
    f.mrr -= 3_960
    f.customers = int(f.mrr / f.arpa_month) if f.arpa_month > 0 else f.customers
    f.notes.append("Wrote off $23,760 and churned the customer. MRR -$3,960/mo. "
                   "Lesson: 18%-of-MRR concentration was the real risk.")


def _hire_ae(f: Financials):
    f.cash -= 40_000
    f.headcount += 1
    # Fully-loaded cost permanent; ramps up to ~$10K/mo by week 13
    # For week-5 modeling: growth rate +1pp after ramp, MRR lift delayed
    f.monthly_growth_rate += 0.01
    f.notes.append("AE hire: -$40K ramp, +1 head (+$10K/mo after ramp), +1pp growth rate. "
                   "Year-1 payback ~0.75x — only fund if playbook is proven.")


def _double_paid(f: Financials):
    f.cash -= 40_000
    f.sm_spend_mo += 6_000  # $40K over ~2 months = +$6K/mo for the quarter
    # CAC typically rises 30% at 2× volume
    f.cac *= 1.30
    # Growth rate rises proportionally to spend if CAC held; but CAC rose, so net +0.5pp
    f.monthly_growth_rate += 0.005
    f.notes.append("Doubled paid S&M: CAC rose 30% (diminishing returns); growth +0.5pp. "
                   "Diagnostic result: channel is saturating.")


def _invest_retention(f: Financials):
    f.cash -= 40_000
    # Churn reduction is the modeled payoff
    f.monthly_churn = max(0.015, f.monthly_churn - 0.01)
    f.notes.append(f"Retention investment: monthly churn {f.monthly_churn*100:.1f}%. "
                   f"LTV lift ~{0.01 / f.monthly_churn * 100:.0f}% — highest-ROI lever in this model.")


def _hold_cash(f: Financials):
    # Hold doesn't change model; just extends runway
    f.notes.append("Held cash: +~1.5 months of runway; no growth lift. Defensible only "
                   "if LTV:CAC < 1 or a raise is imminent (<90 days).")


# ============================================================================
# SESSION STATE
# ============================================================================

def init_state():
    if "fin" not in st.session_state:
        st.session_state.fin = Financials()
    if "current_week" not in st.session_state:
        st.session_state.current_week = 0
    if "game_started" not in st.session_state:
        st.session_state.game_started = False
    if "decisions" not in st.session_state:
        st.session_state.decisions = {}  # week -> option key
    if "snapshots" not in st.session_state:
        st.session_state.snapshots = {}  # week -> Financials snapshot

init_state()


# ============================================================================
# DASHBOARD
# ============================================================================

def _kpi_color(value: float, good_above: float, warn_above: float) -> str:
    if value >= good_above: return "kpi-good"
    if value >= warn_above: return "kpi-warn"
    return "kpi-bad"


def render_dashboard(f: Financials):
    """Render the financial KPI dashboard."""
    # Row 1: cash / MRR / runway
    cols = st.columns(6)
    with cols[0]:
        cash_class = _kpi_color(f.cash, 100_000, 40_000)
        st.markdown(
            f"<div class='metric-box'><div class='label'>CASH</div>"
            f"<div class='value {cash_class}'>${f.cash:,.0f}</div>"
            f"<div class='sub'>bank balance</div></div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f"<div class='metric-box'><div class='label'>MRR</div>"
            f"<div class='value'>${f.mrr:,.0f}</div>"
            f"<div class='sub'>{f.customers} customers × ${f.arpa_month:,.0f} ARPA</div></div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        gm_pct = f.gross_margin * 100
        gm_class = _kpi_color(gm_pct, 70, 55)
        st.markdown(
            f"<div class='metric-box'><div class='label'>GROSS MARGIN</div>"
            f"<div class='value {gm_class}'>{gm_pct:.1f}%</div>"
            f"<div class='sub'>GP/mo: ${f.gross_profit_month():,.0f}</div></div>",
            unsafe_allow_html=True,
        )
    with cols[3]:
        burn = f.net_burn_month()
        burn_class = "kpi-good" if burn >= 0 else ("kpi-warn" if burn > -30000 else "kpi-bad")
        burn_label = f"${burn:+,.0f}/mo"
        st.markdown(
            f"<div class='metric-box'><div class='label'>NET BURN</div>"
            f"<div class='value {burn_class}'>{burn_label}</div>"
            f"<div class='sub'>GP − OpEx (incl. debt)</div></div>",
            unsafe_allow_html=True,
        )
    with cols[4]:
        rw_text, rw_class = f.runway_label()
        st.markdown(
            f"<div class='metric-box'><div class='label'>RUNWAY</div>"
            f"<div class='value {rw_class}'>{rw_text}</div>"
            f"<div class='sub'>forward-projected, {f.monthly_growth_rate*100:.1f}% MRR growth</div></div>",
            unsafe_allow_html=True,
        )
    with cols[5]:
        lc = f.ltv_cac()
        lc_class = _kpi_color(lc, 3.0, 1.5)
        st.markdown(
            f"<div class='metric-box'><div class='label'>LTV:CAC</div>"
            f"<div class='value {lc_class}'>{lc:.2f}</div>"
            f"<div class='sub'>LTV ${f.ltv():,.0f} / CAC ${f.cac:.0f}</div></div>",
            unsafe_allow_html=True,
        )

    # Row 2: structural / unit econ detail
    cols2 = st.columns(6)
    with cols2[0]:
        st.markdown(
            f"<div class='metric-box'><div class='label'>MONTHLY CHURN</div>"
            f"<div class='value'>{f.monthly_churn*100:.1f}%</div>"
            f"<div class='sub'>logo churn</div></div>",
            unsafe_allow_html=True,
        )
    with cols2[1]:
        pb = f.payback_months()
        pb_class = _kpi_color(-pb, -12, -18)  # lower is better → invert
        pb_text = f"{pb:.1f} mo" if pb < 999 else "—"
        st.markdown(
            f"<div class='metric-box'><div class='label'>CAC PAYBACK</div>"
            f"<div class='value {pb_class}'>{pb_text}</div>"
            f"<div class='sub'>CAC / (ARPA × GM)</div></div>",
            unsafe_allow_html=True,
        )
    with cols2[2]:
        st.markdown(
            f"<div class='metric-box'><div class='label'>OPEX/MO</div>"
            f"<div class='value'>${f.opex_month():,.0f}</div>"
            f"<div class='sub'>{f.headcount} heads + G&A + S&M</div></div>",
            unsafe_allow_html=True,
        )
    with cols2[3]:
        fo = f.founder_ownership * 100
        fo_class = _kpi_color(fo, 50, 30)
        st.markdown(
            f"<div class='metric-box'><div class='label'>FOUNDER OWN.</div>"
            f"<div class='value {fo_class}'>{fo:.1f}%</div>"
            f"<div class='sub'>fully-diluted</div></div>",
            unsafe_allow_html=True,
        )
    with cols2[4]:
        debt_text = f"${f.debt_principal:,.0f}" if f.debt_principal > 0 else "none"
        st.markdown(
            f"<div class='metric-box'><div class='label'>DEBT</div>"
            f"<div class='value'>{debt_text}</div>"
            f"<div class='sub'>{f.debt_rate_annual*100:.0f}% APR"
            f"{f' / cov ${f.debt_covenant_min_cash:,.0f}' if f.debt_covenant_min_cash > 0 else ''}</div></div>",
            unsafe_allow_html=True,
        )
    with cols2[5]:
        rbf_text = f"${f.rbf_cap_remaining:,.0f} left" if f.rbf_cap_remaining > 0 else "none"
        st.markdown(
            f"<div class='metric-box'><div class='label'>RBF BALANCE</div>"
            f"<div class='value'>{rbf_text}</div>"
            f"<div class='sub'>${f.rbf_repayment_mo:,.0f}/mo</div></div>",
            unsafe_allow_html=True,
        )

    # Failure flags
    flags = _failure_flags(f)
    if flags:
        st.markdown("")
        for flag in flags:
            st.error(flag)


def _failure_flags(f: Financials) -> List[str]:
    flags = []
    if f.cash < 0:
        flags.append("⚠️ **Insolvent:** cash below $0. You cannot make payroll.")
    if f.debt_covenant_min_cash > 0 and f.cash < f.debt_covenant_min_cash:
        flags.append(f"⚠️ **Covenant breach:** cash below ${f.debt_covenant_min_cash:,.0f} "
                     f"floor. Lender can accelerate the debt (demand full repayment).")
    if f.gross_margin < 0.20:
        flags.append(f"⚠️ **Gross margin collapse:** {f.gross_margin*100:.1f}%. At <20% GM, "
                     f"you cannot build a business — growth amplifies loss, not profit.")
    if f.survival_streak_neg_unit_econ >= 2:
        flags.append("⚠️ **Value-destruction:** LTV:CAC below 1.0 for 2+ consecutive weeks. "
                     "Every new customer loses money. Growth = faster insolvency.")
    if f.founder_ownership < 0.25:
        flags.append(f"⚠️ **Founder dilution risk:** founder ownership {f.founder_ownership*100:.1f}%. "
                     f"Below 25%, alignment with future investors becomes structurally harder; "
                     f"control provisions start mattering more than equity math.")
    return flags


# ============================================================================
# RENDER SCREENS
# ============================================================================

def render_intro():
    st.title("💵 Startup Financials Simulator")
    st.markdown("""
### Rigorous Financial Decision-Making for Founders

You run **ThermaLoop** — a smart-ventilation retrofit company, SaaS + hardware hybrid.
You have paying customers, a team, and a real P&L. Over 5 weeks you'll face 5
*financial* decisions — pricing, cost structure, funding, AR, growth allocation.

**This is not a crisis-management sim.** Every decision modifies a forward-projected
P&L and cash-flow model. There are no morale meters; there are unit-economics,
burn rate, runway, and cap-table consequences. Learners who don't read the
tradeoffs carefully will trip one of the modeled failure states:
*insolvency, covenant breach, margin collapse, value-destructive growth, founder dilution.*

---
### Starting P&L

| Metric | Value | Notes |
|---|---|---|
| Cash | $220,000 | post-seed bank balance |
| MRR | $22,000 | 275 customers × $80/mo ARPA (~$960 ACV) |
| Gross margin | 62% | hardware + SaaS hosting + support blended |
| Monthly churn | 3.5% | logo churn |
| Monthly growth | 6.0% | net new MRR |
| CAC | $420 | blended |
| LTV | ~$1,416 | ARPA × GM / churn |
| LTV:CAC | ~3.4 | just above the institutional threshold |
| CAC payback | ~8.5 mo | CAC / (ARPA × GM) |
| OpEx | ~$53.5K/mo | 6 heads × $7.5K + $4.5K G&A + $4K S&M |
| Gross profit | ~$13.6K/mo | MRR × GM |
| Net burn | ~$40K/mo | GP − OpEx |
| Runway | ~7-9 mo | forward-projected at current growth |
| Founder ownership | 75% | post-seed, fully-diluted |
| Post-money | $6M | last-round valuation mark |

---

### The mechanics

1. Each week you'll see a **financial decision** with 4 options
2. Each option has **modeled financial consequences** that update the P&L
3. The dashboard updates; if you trip a failure state (insolvency, covenant
breach, margin collapse, value-destructive growth), the sim surfaces it
4. After week 5, you'll see your **full decision cascade** — every option's
impact across cash, MRR, unit economics, and cap-table dilution
5. You'll also see the **counterfactuals**: what would have happened if you'd
picked each of the other options

**There is no "right" answer at any step.** The rigorous play is to read the
tradeoff, look at the dashboard, and pick the option with the best risk-adjusted
financial outcome *given your current state*.
""")

    if st.button("🚀 START — Week 1: Pricing Decision", use_container_width=True, type="primary"):
        st.session_state.game_started = True
        st.session_state.current_week = 1
        st.session_state.snapshots[0] = copy.deepcopy(st.session_state.fin)
        st.rerun()


def _format_narrative(narrative: str, f: Financials) -> str:
    """Substitute live model values into narrative placeholders."""
    return narrative.format(
        headcount=f.headcount,
        opex=f.opex_month(),
        gp=f.gross_profit_month(),
        burn=-f.net_burn_month() if f.net_burn_month() < 0 else 0,
        runway=f.runway_months(),
        cash=f.cash,
        ltv_cac=f.ltv_cac(),
        payback=f.payback_months(),
    )


def render_week(week: int):
    f: Financials = st.session_state.fin
    decision = DECISIONS[week]

    st.title(f"WEEK {week} of 5")
    st.subheader(decision["title"])
    render_dashboard(f)

    st.markdown("---")
    st.markdown(f"**Scenario:** {_format_narrative(decision['narrative'], f)}")
    st.markdown(f"**{decision['decision_question']}**")

    if week in st.session_state.decisions:
        # Already decided — show outcome
        chosen = st.session_state.decisions[week]
        opt = decision["options"][chosen]
        st.success(f"✅ You chose **{chosen}: {opt['title']}**")
        st.markdown(f"**Tradeoff:** {opt['tradeoff']}")
        st.markdown(f"**Mechanism:** {opt['why']}")
        if st.session_state.fin.notes:
            st.markdown("**Model effects applied this week:**")
            for note in st.session_state.fin.notes[-3:]:
                st.markdown(f"- {note}")

        st.markdown("---")
        if st.button(
            "Next Week →" if week < 5 else "See Final Debrief →",
            use_container_width=True, type="primary",
        ):
            if week < 5:
                st.session_state.current_week = week + 1
            else:
                st.session_state.current_week = 6
            st.rerun()
    else:
        # Show options
        for key, opt in decision["options"].items():
            with st.container():
                st.markdown(
                    f"<div class='option-panel'>"
                    f"<strong>{key}. {opt['title']}</strong><br>"
                    f"<em>Tradeoff:</em> {opt['tradeoff']}<br>"
                    f"<em>Mechanism:</em> {opt['why']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Choose {key}", key=f"btn_{week}_{key}"):
                    # Snapshot BEFORE applying for counterfactual analysis
                    st.session_state.snapshots[week] = copy.deepcopy(st.session_state.fin)
                    # Apply decision
                    st.session_state.fin.notes = []
                    opt["apply"](st.session_state.fin)
                    # Advance model 1 week
                    st.session_state.fin.apply_monthly_step(weeks=1)
                    st.session_state.decisions[week] = key
                    st.rerun()


def render_debrief():
    f: Financials = st.session_state.fin
    st.title("📊 Final Financial Debrief")
    render_dashboard(f)

    st.markdown("---")
    # Overall outcome
    flags = _failure_flags(f)
    if flags:
        st.error("**You triggered one or more failure states** — the business, as modeled, is in distress.")
    elif f.runway_months() >= 18 and f.ltv_cac() >= 3.0:
        st.success("**Series A-ready:** runway ≥ 18 months AND LTV:CAC ≥ 3.0. "
                   "This is the default institutional diligence screen. You passed both.")
    elif f.runway_months() >= 12 and f.ltv_cac() >= 2.0:
        st.info("**Fundable, not yet at Series A bar:** you're operable and can raise a "
                "bridge, but institutional priced-round metrics aren't there yet.")
    else:
        st.warning("**Below the institutional bar:** runway or unit economics aren't where "
                   "they need to be for a priced round. You're operating, but on thinner ice.")

    # Decision archetype
    st.subheader("Your Decision Pattern")
    arch = _classify_archetype()
    st.markdown(f"**{arch['name']}** — {arch['description']}")
    st.markdown(f"**The failure mode of this pattern:** {arch['failure_mode']}")

    # Cascade analysis
    st.subheader("Decision Cascade")
    st.caption("Each row: the option you picked, its modeled effect on cash, MRR, and LTV:CAC.")
    for week in range(1, 6):
        if week not in st.session_state.decisions:
            continue
        chosen = st.session_state.decisions[week]
        decision = DECISIONS[week]
        opt = decision["options"][chosen]
        before: Financials = st.session_state.snapshots.get(week)
        after_map = st.session_state.snapshots.get(week + 1) if (week + 1) in st.session_state.snapshots else f
        after: Financials = after_map
        if before:
            delta_cash = after.cash - before.cash
            delta_mrr = after.mrr - before.mrr
            delta_lc = after.ltv_cac() - before.ltv_cac()
            with st.expander(f"Week {week}: {chosen} — {opt['title']}"):
                st.markdown(f"**Tradeoff:** {opt['tradeoff']}")
                st.markdown(f"**Mechanism:** {opt['why']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Cash Δ", f"${delta_cash:+,.0f}")
                c2.metric("MRR Δ", f"${delta_mrr:+,.0f}")
                c3.metric("LTV:CAC Δ", f"{delta_lc:+.2f}")

    # Counterfactuals
    st.subheader("Counterfactuals: What if you'd chosen differently?")
    st.caption("Each week's 4 options re-run from the actual pre-decision state.")
    for week in range(1, 6):
        if week not in st.session_state.snapshots:
            continue
        base: Financials = st.session_state.snapshots[week]
        decision = DECISIONS[week]
        with st.expander(f"Week {week} alternatives — {decision['title']}"):
            for key, opt in decision["options"].items():
                sim_fin = copy.deepcopy(base)
                sim_fin.notes = []
                opt["apply"](sim_fin)
                sim_fin.apply_monthly_step(weeks=1)
                picked = "✅" if st.session_state.decisions.get(week) == key else "  "
                st.markdown(
                    f"{picked} **{key}. {opt['title']}** → "
                    f"cash ${sim_fin.cash:,.0f} | MRR ${sim_fin.mrr:,.0f} | "
                    f"LTV:CAC {sim_fin.ltv_cac():.2f} | runway {sim_fin.runway_months():.1f} mo"
                )

    # Lessons
    st.subheader("What the model exposed")
    lessons = _generate_lessons(f)
    for i, lesson in enumerate(lessons, 1):
        st.markdown(f"{i}. {lesson}")

    st.markdown("---")
    if st.button("🔄 Restart", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def _classify_archetype() -> Dict[str, str]:
    """Classify decision pattern from the 5 choices."""
    d = st.session_state.decisions
    # Tally: pricing (1), cost (2), funding (3), AR (4), growth (5)
    # Archetype dimensions
    aggressive = 0   # blanket price hikes, layoffs, priced rounds, escalation, AE hire
    conservative = 0 # grandfathering, vendor cuts, SAFE, factor AR, hold cash
    dilutive = 0     # took equity dilution
    debt_user = 0    # took debt

    mapping = {
        (1, "B"): "aggressive", (1, "A"): "conservative", (1, "C"): "aggressive",
        (2, "A"): "aggressive", (2, "B"): "conservative", (2, "C"): "conservative", (2, "D"): "aggressive",
        (3, "A"): "dilutive",   (3, "B"): "dilutive",    (3, "C"): "debt_user",    (3, "D"): "debt_user",
        (4, "A"): "conservative", (4, "B"): "conservative", (4, "C"): "aggressive", (4, "D"): "conservative",
        (5, "A"): "aggressive", (5, "B"): "aggressive", (5, "C"): "conservative", (5, "D"): "conservative",
    }
    for week, choice in d.items():
        tag = mapping.get((week, choice), "")
        if tag == "aggressive": aggressive += 1
        elif tag == "conservative": conservative += 1
        elif tag == "dilutive": dilutive += 1
        elif tag == "debt_user": debt_user += 1

    if aggressive >= 3:
        return {
            "name": "The Accelerator",
            "description": "You pushed on every lever — price, cost, growth. This is high-variance "
                           "founding: you maximize upside in the fast-growth case and amplify damage "
                           "in the slow-growth case.",
            "failure_mode": "Aggressive posture requires LTV:CAC ≥ 3 as a precondition. If your unit "
                            "economics aren't proven, aggressive decisions accelerate insolvency rather "
                            "than growth. Always check unit economics before you press the accelerator.",
        }
    if conservative >= 3:
        return {
            "name": "The Preservationist",
            "description": "You protected cash, minimized commitment, avoided structural change. This "
                           "is low-variance founding: you extend runway in the slow-growth case and "
                           "leave upside on the table in the fast-growth case.",
            "failure_mode": "Preservation without growth is a slow bleed. Runway extension without "
                            "LTV:CAC improvement just delays the same decision — and competitors who "
                            "are compounding growth will reach Series A bar first. Know what you're waiting for.",
        }
    if debt_user >= 1 and dilutive == 0:
        return {
            "name": "The Debt-User",
            "description": "You preferred non-dilutive capital. This works when your growth trajectory "
                           "is predictable enough to service debt. The tradeoff is covenant exposure "
                           "and the cost of interest against operating cash.",
            "failure_mode": "Venture debt is senior to equity. If you miss covenants in a down cycle, "
                            "the lender can accelerate and force a sale at distressed pricing. RBF "
                            "looks cheap until you grow fast and realize you paid 40%+ implied APR.",
        }
    if dilutive >= 1:
        return {
            "name": "The Equity-Funder",
            "description": "You funded via equity when capital was needed. Clean, but expensive — "
                           "every round resets your cap table and compounds dilution. The discipline "
                           "here is raising only what you need to hit the next *metric milestone*.",
            "failure_mode": "Stacking SAFEs or under-raising forces you to raise again sooner, which "
                            "typically means more dilution at worse terms. If you raise $300K at "
                            "$6M cap then again at $6M cap 9 months later, you've done a flat round — "
                            "and the market reads that as a red flag.",
        }
    return {
        "name": "The Balanced Operator",
        "description": "No single posture dominated your decisions. You read each scenario on its merits.",
        "failure_mode": "Balance can become indecision at inflection points. The best balanced operators "
                        "pre-commit to decision rules ('if LTV:CAC < 2 in week 4, we cut S&M by 30%') "
                        "so the framework holds under pressure.",
    }


def _generate_lessons(f: Financials) -> List[str]:
    lessons = []

    if f.ltv_cac() < 1.0:
        lessons.append(
            "**LTV:CAC < 1.0 — growth destroys value.** Every new customer costs more "
            "than they'll ever return. The only valid moves are (a) raise ARPA, (b) "
            "lower CAC, (c) improve gross margin, or (d) reduce churn. Scaling sales or "
            "marketing here loses money faster."
        )
    elif f.ltv_cac() < 2.0:
        lessons.append(
            "**LTV:CAC 1.0-2.0 — survivable, not fundable.** The business operates, but "
            "no priced-round investor will lead. Focus on the single highest-leverage "
            "lever (usually retention / churn reduction) before raising."
        )

    if f.runway_months() < 6:
        lessons.append(
            "**Runway < 6 months is a raise-or-die state.** In this zone, every decision "
            "is filtered through 'does this help me raise in 90 days?' That's a narrow "
            "lens that usually forces suboptimal terms."
        )
    elif f.runway_months() < 12:
        lessons.append(
            "**Runway 6-12 months — you're now fundraising whether you want to be or "
            "not.** The diligence process takes 3-4 months. Below 12 months, start the "
            "conversation now."
        )

    if f.founder_ownership < 0.40:
        lessons.append(
            f"**Founder ownership {f.founder_ownership*100:.1f}%.** Each round has compressed "
            f"your equity. At Series A (typical 20% dilution + 10% option pool refresh), "
            f"founders who enter under 40% usually exit under 25% — the zone where board "
            f"control mechanics start mattering more than economic upside."
        )

    if f.gross_margin < 0.50:
        lessons.append(
            f"**Gross margin {f.gross_margin*100:.1f}%.** Below 50% GM, every dollar of "
            f"revenue leaves less than 50¢ for OpEx. SaaS investors screen for 70%+; "
            f"hybrid hardware/SaaS businesses are evaluated on a blended 55-65%. Your "
            f"GM puts a ceiling on LTV — and therefore on what you can spend on CAC."
        )

    if f.debt_principal > 0 and f.cash < f.debt_covenant_min_cash * 1.5:
        lessons.append(
            f"**Covenant pressure.** Your cash (${f.cash:,.0f}) is close to the "
            f"${f.debt_covenant_min_cash:,.0f} covenant floor. A missed quarter can "
            f"trigger acceleration. The lesson: when you take debt, model downside "
            f"scenarios to covenant-breach, not just base case."
        )

    if not lessons:
        lessons.append(
            "**You threaded the needle.** LTV:CAC above institutional threshold, runway "
            "intact, cap table preserved. The model is hard to pass without thinking "
            "carefully about each decision's second-order effects."
        )

    # Always teach the framework lesson
    lessons.append(
        "**Every financial decision changes multiple line items at once.** Pricing "
        "moves ARPA → MRR → LTV, and usually churn. Cost cuts move burn → runway, and "
        "usually growth rate. Funding moves cash → dilution and (for debt) covenant "
        "risk. The rigorous founder reads *all* the second-order effects before choosing — "
        "not just the headline number."
    )

    return lessons


# ============================================================================
# MAIN
# ============================================================================

def main():
    if not st.session_state.game_started:
        render_intro()
    elif 1 <= st.session_state.current_week <= 5:
        render_week(st.session_state.current_week)
    else:
        render_debrief()


if __name__ == "__main__":
    main()
