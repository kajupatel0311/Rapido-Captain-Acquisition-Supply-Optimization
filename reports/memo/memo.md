# Rapido Captain Acquisition & Supply — Executive Memo

## Executive Summary

The main opportunity is not simply to acquire more captains, but to increase the number of **productive captains** who complete onboarding, get approved, and actually complete a first order.

From 25,000 signups, 4,206 captains were approved and 1,610 completed a first order. This means only **6.4% of signups reached first order**, with meaningful leakage both during document verification and after approval.

The strongest onboarding opportunity is the **Permit stage for Auto/Cab captains**, particularly in Pune and Hyderabad. A scenario reducing Permit non-clearance by 20% indicates approximately **397 additional approvals per month** across mature cohorts. At the segment level, Pune Auto + organic acquisition has the largest modeled opportunity.

For supply-demand, airport shortages are concentrated during **21:00–03:00**, while airport-terminal fulfillment is substantially below CBD fulfillment. The immediate response should therefore be better positioning and incentives for existing captains before spending heavily on targeted acquisition.

---

## A1. Funnel

| Stage | Captains | Stage Conversion | Overall Conversion |
|---|---:|---:|---:|
| Signup | 25,000 | 100.0% | 100.0% |
| DL | 21,954 | 87.8% | 87.8% |
| RC | 15,852 | 72.2% | 63.4% |
| Aadhaar | 14,095 | 88.9% | 56.4% |
| Permit | 11,177 | 79.3% | 44.7% |
| Fitness | 8,241 | 73.7% | 33.0% |
| Insurance | 4,664 | 56.6% | 18.7% |
| All Documents Cleared | 4,664 | 100.0% | 18.7% |
| Approved | 4,206 | 90.2% | 16.8% |
| First Order | 1,610 | 38.3% | 6.4% |

**Biggest absolute document-stage loss:** Insurance, with 3,577 captains not clearing that stage.

**Largest downstream opportunity:** 2,596 approved captains did not complete a first order. This makes post-approval activation a major lever in addition to document recovery.

### Cohort rule

Funnel metrics are based on signup cohorts, with the latest signup period excluded where necessary so that captains have enough time to progress through onboarding.

---

## A2. Biggest Fixable Leak

The most actionable onboarding problem is **Permit completion for Auto/Cab captains**.

The opportunity is concentrated in specific city × vehicle × acquisition-channel segments rather than being evenly distributed across the funnel.

Top segment examples:

| Segment | Permit Reached | Not Cleared | Drop-off |
|---|---:|---:|---:|
| Pune · Auto · Organic | 1,172 | 744 | 63.5% |
| Hyderabad · Cab · Organic | 1,219 | 727 | 59.6% |
| Hyderabad · Auto · Organic | 1,129 | 682 | 60.4% |
| Pune · Auto · Referral | 820 | 525 | 64.0% |
| Bangalore · Cab · Organic | 941 | 558 | 59.3% |

A scenario reducing stage non-clearance by **20% relative** suggests approximately **397 incremental approvals per month from Permit alone** across mature cohorts.

This is a planning scenario, not a causal forecast.

The highest-priority individual segment is:

**Pune × Auto × Organic × Permit**

It represents a modeled opportunity of roughly **149 additional approvals/month**, before considering the downstream first-order conversion.

### Recommended intervention

Use an escalating Permit recovery journey:

1. Identify captains failing or repeatedly failing Permit verification.
2. Show a clear failure reason and the next required action.
3. Provide targeted document guidance.
4. Prioritize repeated-failure captains for assisted support.
5. Measure recovery by signup cohort and segment.

The key metric should be **incremental approvals per 1,000 affected captains**, not simply message engagement.

---

## A3. CAMP_WA_002

CAMP_WA_002 shows a strong positive association with approval.

- Treated captains: **8,673**
- Control captains: **16,327**
- Observed approval lift: **+17.9 percentage points**
- 95% CI: **+16.8 to +19.0 pp**
- Adjusted approval lift: **+16.7 percentage points**
- Adjusted odds ratio: **3.26**

The result is statistically strong, but campaign exposure was not randomized.

**Recommendation:** do not treat the +16.7 pp estimate as causal yet. Run a randomized holdout before scaling the campaign broadly.

The holdout should measure:

- Approval rate
- Incremental approvals
- Cost per incremental approval
- First-order conversion
- Cost per productive captain

---

## A4. Ranked Recommendations

### 1. Fix Permit completion in high-opportunity segments

**Impact:** High  
**Cost:** Medium  
**Risk:** Medium  

Prioritize Auto/Cab Permit recovery in Pune and Hyderabad first. The modeled opportunity is approximately **397 incremental approvals/month** under the stated 20% recovery scenario.

**Measurement:** incremental approval rate and first-order conversion among intervention vs. control groups.

---

### 2. Improve Approved → First Order conversion

**Impact:** High  
**Cost:** Medium  
**Risk:** Low–Medium  

Only **38.3% of approved captains completed a first order**. This is a large pool of already-approved captains where acquisition cost has effectively already been incurred.

Test:

- first-order nudges,
- supply-zone recommendations,
- onboarding completion assistance,
- targeted incentives,
- early activation support.

**Measurement:** approved-to-first-order conversion and cost per incremental first-order captain.

---

### 3. Validate CAMP_WA_002 before scaling

**Impact:** Potentially High  
**Cost:** Low  
**Risk:** Low  

The campaign has a strong adjusted association, but causal impact has not been established.

Run a randomized holdout and scale only if incremental approval and first-order economics remain positive.

---

# Associate Analysis — Airport Supply

## B1. Where is supply insufficient?

Airport terminals show a major supply-demand mismatch compared with CBD zones.

Approximate fulfillment:

- Airport terminals: **~60%**
- CBD zones: **~97.5%**

The largest hourly gaps occur during **21:00–03:00**, particularly around 22:00, 23:00, 00:00, 01:00 and 02:00.

This indicates that the problem is not simply insufficient supply throughout the day; it is concentrated in specific airport time windows.

---

## B2. What happens after airport trips?

Across airport trips:

- Cancellation rate: **13.8%**
- Return fare within 20 minutes: **36.0%**
- Average fare: approximately **₹279**
- Average trip distance: approximately **17.9 km**

During the late-night 21:00–03:00 window:

- Cancellation rate increases to **17.1%**
- Return-fare rate falls to **29.8%**

This suggests that late-night airport supply is less attractive from a utilization perspective and may require stronger positioning or incentives.

---

## B3. Should Rapido target specific captain acquisition?

### Recommendation: Yes, but not as the first intervention.

The analysis indicates that airport supply shortage is highly concentrated in late-night hours. Before acquiring new captains specifically for the airport, Rapido should test whether existing supply can be repositioned effectively.

### Priority sequence

**1. Reposition existing captains**

Target nearby captains before the 21:00–03:00 shortage window.

**2. Introduce targeted airport incentives**

Use time- and location-specific incentives rather than broad incentives.

**3. Measure the economics**

Compare incremental fulfilled requests against incentive cost.

**4. Only then use targeted acquisition**

If the shortage remains after repositioning and incentives, acquire captains matching the required:

- city,
- vehicle type,
- airport proximity,
- availability during 21:00–03:00.

This is a better strategy than optimizing for generic signup volume.

---

# Decision Framework

The analysis prioritizes interventions using:

**Affected captains × recovery opportunity × downstream approval probability × first-order conversion**

This shifts the objective from:

> "How many captains can we acquire?"

to:

> **"How many productive captains can we create?"**

For supply planning, the same principle is applied from the opposite direction:

**Demand gap → required supply → captain profile → targeted intervention → measured incremental supply**

---

# Final Recommendation

Rapido should focus on three connected levers:

1. **Recover high-value onboarding leaks**, starting with Permit for Auto/Cab captains in Pune and Hyderabad.
2. **Convert approved captains into first orders**, because a large existing pool is already lost after approval.
3. **Use controlled experiments for campaign and airport interventions**, rather than assuming observational uplift is causal.

The broader opportunity is to move from volume-based acquisition to **demand-led productive captain acquisition**: identify where supply is needed, determine which captain profiles can solve the gap, and invest only where incremental productive supply can be measured.

---

## Key Assumptions & Limitations

- The data is synthetic and should be treated as an analytical exercise rather than production performance.
- Permit recovery estimates use a **20% relative reduction in non-clearance** as a scenario assumption.
- CAMP_WA_002 exposure is observational; the adjusted estimate should not be interpreted as causal.
- Airport supply-gap estimates depend on the hourly supply-demand assumptions in the provided data.
- Recommendations should ultimately be validated through randomized or controlled experiments.