# Analysis Memo
from pathlib import Path

memo = """# Rapido Captain Acquisition & Supply — Executive Memo

## Executive summary

The main opportunity is not simply to increase captain sign-ups; it is to convert existing signup intent into approved and productive supply. From 25,000 sign-ups, 4,206 captains are approved (16.8%) and only 1,610 complete a first order (6.4%). The largest onboarding losses occur at RC, Permit, and Insurance, while Permit is the clearest targeted opportunity because its leakage is concentrated in specific city × vehicle × acquisition-channel segments. Separately, the airport supply gap is heavily concentrated late at night, where return-fare availability is weaker and cancellation is higher.

I recommend: **(1)** target Permit verification in the highest-leak segments, **(2)** validate CAMP_WA_002 with a randomized holdout before scaling, and **(3)** test late-night airport incentives/repositioning before broad airport captain acquisition.

## 1. Funnel and biggest fixable leak

The onboarding funnel is defined at the captain level. Permit is required for Auto and Cab, while ERickshaw skips the Permit stage. The final funnel is:

| Stage | Captains | Stage conversion | Signup → stage |
|---|---:|---:|---:|
| Signup | 25,000 | 100.0% | 100.0% |
| DL | 21,954 | 87.8% | 87.8% |
| RC | 15,852 | 72.2% | 63.4% |
| Aadhaar | 14,095 | 88.9% | 56.4% |
| Permit | 11,177 | 79.3% | 44.7% |
| Fitness | 8,241 | 73.7% | 33.0% |
| Insurance | 4,664 | 56.6% | 18.7% |
| Approved | 4,206 | 90.2% | 16.8% |
| First Order | 1,610 | 38.3% | 6.4% |

RC has the largest absolute loss among sequential document stages (6,102 captains), while Insurance has the weakest conversion (56.6%). However, the segment analysis identifies **Permit** as the most actionable targeted bottleneck.

The largest Permit leaks are concentrated in Pune Auto organic_app (744 not cleared; 63.5% drop-off), Hyderabad Cab organic_app (727; 59.6%), Hyderabad Auto organic_app (682; 60.4%), Bangalore Cab organic_app (558; 59.3%), and Pune Auto referral (525; 64.0%).

Under a planning scenario that reduces Permit non-clearance by 20% for mature cohorts and applies historical downstream approval rates, Permit represents approximately **396.6 scenario-estimated incremental approvals across the observed mature segment-month population**. This is a sizing scenario, not a causal forecast.

**Action:** prioritize Permit document guidance, verification feedback, and re-upload support in the highest-leak segments rather than applying a blanket intervention across all captains.

## 2. CAMP_WA_002

CAMP_WA_002 is strongly associated with approval:

- Treated: 8,673 captains
- Control: 16,327 captains
- Observed approval lift: **+17.9 percentage points**
- 95% CI: **+16.8 to +19.0 pp**
- Adjusted lift: **+16.7 pp**
- Odds ratio: **3.26** (95% CI approximately 3.04–3.50)

The result is statistically strong, but campaign exposure was not randomized. Therefore, the estimate should be treated as **observational association, not causal impact**.

**Action:** run a randomized holdout before materially increasing campaign spend. Primary KPI should be incremental approved captains per unit of campaign cost, with secondary checks for downstream first-order conversion.

## 3. Airport supply and post-trip behavior

Airport supply is substantially worse than the rest of the marketplace. The estimated gap is concentrated in late-night hours: **72.7% of the estimated airport supply gap falls between 21:00 and 03:00**. The largest hourly gaps are at 22:00 (about 1,070 captain-equivalents), 23:00 (1,061), 01:00 (1,060), 02:00 (1,018), 00:00 (973), and 21:00 (897).

Across 60,000 sampled airport-origin trips:

- Cancellation rate: **13.8%**
- Return-fare within 20 minutes: **36.0%**
- Average fare: **₹279**
- Average distance: **17.9 km**

During the late-night window, return-fare availability falls to **29.8%** while cancellation rises to **17.1%**. This pattern is consistent with weaker late-night round-trip economics or other supply friction, although the trip data has no captain_id and therefore cannot establish individual captain retention.

**Action:** test late-night airport repositioning and targeted economic incentives before broad acquisition. Measure fulfilment, unfulfilled requests, ETA, captain online hours, cancellation, and incentive ROI.

## 4. Prioritized recommendations

### 1 — Fix targeted Permit leakage
**Impact:** Highest modeled onboarding opportunity; Permit contributes ~396.6 scenario-estimated incremental approvals across mature segment-months under the stated assumption.  
**Cost:** Medium — product/ops changes to guidance, verification feedback, and re-upload support.  
**Risk:** Low–medium — avoid increasing approvals by weakening document-quality controls.  
**Measurement:** Permit clearance rate, re-upload rate, verification turnaround, A2O, and cost per incremental approval.

### 2 — Validate CAMP_WA_002 before scaling
**Impact:** Large observed/adjusted association (+17.9 pp / +16.7 pp).  
**Cost:** Low–medium — randomized holdout and campaign instrumentation.  
**Risk:** Medium — observed association may contain selection/confounding.  
**Measurement:** incremental approval lift, confidence interval, cost per incremental approval, and downstream R2A.

### 3 — Solve airport late-night supply economics before broad acquisition
**Impact:** 72.7% of the estimated airport gap is late-night.  
**Cost:** Medium — incentive/repositioning experiment.  
**Risk:** Medium — incentives can improve fulfilment while destroying unit economics.  
**Measurement:** fulfilment, ETA, unfulfilled demand, cancellation, captain utilization, and incentive ROI.

## Assumptions and limitations

- The latest signup cohort is excluded from A2 opportunity sizing because it may not have reached full onboarding maturity.
- Permit applies to Auto and Cab; ERickshaw skips that stage.
- The 20% improvement rate is a planning assumption.
- A2 downstream approval rates are based on historical mature cohorts and are not causal.
- CAMP_WA_002 was not randomized; causal impact requires a holdout.
- Airport supply sizing uses a historical fulfillment benchmark and should be treated as a capacity-sizing indicator, not a literal hiring requirement.
- Airport trip data is sampled and does not contain captain_id, so post-trip behavior is a proxy for trip economics rather than longitudinal captain retention.
"""

out = Path("/mnt/data/rapido_updated/memo.md")
out.write_text(memo, encoding="utf-8")
print(out)
