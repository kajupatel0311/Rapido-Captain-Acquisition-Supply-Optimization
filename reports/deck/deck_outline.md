# Deck Outline
from pathlib import Path

deck = """# Rapido Captain Acquisition & Supply — 6-Slide Deck

## Slide 1 — Executive Summary: Optimize for productive supply

### Headline
**The biggest opportunity is converting existing signup intent into productive captain supply — not simply adding more sign-ups.**

### Key numbers
- **25,000** sign-ups
- **4,206** approved → **16.8% A2O**
- **1,610** first orders → **6.4% signup → first order**
- **72.7%** of estimated airport supply gap occurs during **21:00–03:00**

### Three decisions
1. **Target Permit leakage** in high-impact city × vehicle × channel segments.
2. **Validate CAMP_WA_002** with randomized holdout before scaling.
3. **Test airport incentives/repositioning** before broad airport acquisition.

### Speaker note
“I would optimize for productive supply rather than sign-ups. The data shows two distinct problems: document-stage conversion and post-approval activation. Airport shortage is also concentrated in a specific late-night window, so I would solve the operational/economic issue before buying more supply.”

---

## Slide 2 — Funnel: Document leakage is concentrated

### Headline
**Only 16.8% of sign-ups reach approval, and 6.4% complete a first order.**

### Funnel

| Stage | Captains | Conversion |
|---|---:|---:|
| Signup | 25,000 | 100.0% |
| DL | 21,954 | 87.8% |
| RC | 15,852 | 72.2% |
| Aadhaar | 14,095 | 88.9% |
| Permit* | 11,177 | 79.3% |
| Fitness | 8,241 | 73.7% |
| Insurance | 4,664 | 56.6% |
| Approved | 4,206 | 90.2% |
| First Order | 1,610 | 38.3% |

*Permit required for Auto/Cab; ERickshaw skips Permit.

### Callouts
- **RC:** largest absolute sequential document loss — **6,102**
- **Insurance:** weakest major document-stage conversion — **56.6%**
- **Approved → First Order:** **2,596** approved captains do not complete a first order

### Speaker note
“RC is the largest absolute document leak, while Insurance has the weakest conversion. However, the segmented analysis makes Permit the most actionable targeted bottleneck. I would treat first-order conversion separately because it is a post-approval activation problem.”

---

## Slide 3 — A2: Target Permit leakage where it is concentrated

### Headline
**Permit is the clearest targeted onboarding opportunity, concentrated in a handful of segments.**

### Top segment leaks

| Segment | Reached | Not cleared | Drop-off |
|---|---:|---:|---:|
| Pune · Auto · organic_app | 1,172 | **744** | 63.5% |
| Hyderabad · Cab · organic_app | 1,219 | **727** | 59.6% |
| Hyderabad · Auto · organic_app | 1,129 | **682** | 60.4% |
| Bangalore · Cab · organic_app | 941 | **558** | 59.3% |
| Pune · Auto · referral | 820 | **525** | 64.0% |

### Opportunity sizing
**~396.6 scenario-estimated incremental approvals** across the observed mature segment-month population if Permit non-clearance falls by 20% and historical downstream approval rates hold.

### Important label
**Planning scenario — not causal impact.**

### Action
Improve Permit:
- upfront document requirements/guidance
- clearer failure reasons
- faster re-upload loop
- targeted operational follow-up

### Speaker note
“I am not recommending a blanket Permit intervention. The leakage is concentrated, so I would start with Pune Auto and Hyderabad Auto/Cab, especially organic acquisition. The 396.6 number is scenario sizing based on a 20% relative reduction in non-clearance, not a forecast.”

---

## Slide 4 — A3: CAMP_WA_002 has a strong signal, but needs an experiment

### Headline
**CAMP_WA_002 is associated with +16.7 pp adjusted approval lift — validate before scaling.**

### Results
- Treated: **8,673**
- Control: **16,327**
- Observed approval lift: **+17.9 pp**
- 95% CI: **+16.8 to +19.0 pp**
- Adjusted lift: **+16.7 pp**
- Odds ratio: **3.26**
- Odds-ratio 95% CI: approximately **3.04–3.50**

### Decision
**Do not interpret this as causal yet.**

### Experiment
Randomly hold out a portion of eligible captains and compare:
- incremental approval rate
- cost per incremental approved captain
- downstream first-order rate
- campaign ROI

### Speaker note
“The statistical signal is very strong, but significance is not the same as causality. Because campaign exposure was not randomized, I would use the current result to justify an experiment, not a 5× budget increase.”

---

## Slide 5 — Airport: shortage is a late-night problem with weaker economics

### Headline
**72.7% of the estimated airport gap falls between 21:00–03:00.**

### Supply
Largest estimated hourly gaps:
- 22:00 → **1,070**
- 23:00 → **1,061**
- 01:00 → **1,060**
- 02:00 → **1,018**
- 00:00 → **973**
- 21:00 → **897**

### Trip behavior
From **60,000** sampled airport-origin trips:
- Overall cancellation: **13.8%**
- Overall return-fare rate: **36.0%**
- Late-night cancellation: **17.1%**
- Late-night return-fare rate: **29.8%**

### Diagnosis
Late-night shortage coincides with:
**higher cancellation + lower return-fare availability**

This suggests weaker captain economics or positioning friction, but the trip data has no captain_id, so this is **not proof of individual captain retention**.

### Speaker note
“The supply gap is not evenly distributed. Most of it occurs overnight, exactly when return-fare availability is lower and cancellations are higher. That makes an economic/positioning intervention a better first test than broad acquisition.”

---

## Slide 6 — Roadmap: Fix conversion, validate growth, then acquire selectively

### Headline
**Prioritize interventions by evidence, reversibility, and measurable supply impact.**

| Priority | Recommendation | Impact | Cost | Risk | Primary KPI |
|---|---|---|---|---|---|
| 1 | Target Permit leakage | High | Medium | Low–Med | Incremental A2O |
| 2 | Randomized CAMP_WA_002 holdout | High potential | Low–Med | Medium | Incremental approvals / ₹ |
| 3 | Late-night airport incentives + repositioning | High | Medium | Medium | Fulfilment + incentive ROI |

### 30-day execution plan
**Week 1:** launch Permit funnel diagnostics and airport experiment design  
**Week 2:** start targeted Permit intervention + airport control/test  
**Week 3:** monitor A2O, fulfilment, ETA, cancellation and economics  
**Week 4:** scale winners; stop interventions that fail ROI thresholds

### Final principle
**Acquire more captains only where operational fixes cannot close the supply gap economically.**

### Speaker note
“My sequencing is deliberate: fix the highest-value conversion leak, establish causal evidence for the campaign, and test whether airport supply can be unlocked from existing captains before adding acquisition cost.”

---

# Appendix — numbers to remember for the debrief

- Sign-ups: **25,000**
- Approved: **4,206**
- First orders: **1,610**
- A2O: **16.8%**
- Signup → first order: **6.4%**
- R2A: **38.3%**
- Permit stage: **11,177**
- Permit scenario opportunity: **~396.6**
- CAMP_WA_002 observed lift: **+17.9 pp**
- CAMP_WA_002 adjusted lift: **+16.7 pp**
- Airport late-night gap share: **72.7%**
- Overall airport cancellation: **13.8%**
- Late-night cancellation: **17.1%**
- Overall return-fare rate: **36.0%**
- Late-night return-fare rate: **29.8%**

# Core caveats

1. A2 opportunity is a scenario estimate, not causal impact.
2. June/latest signup cohort is excluded from A2 maturity-based sizing.
3. Permit is required only for Auto/Cab.
4. CAMP_WA_002 is observational; randomized validation is required.
5. Airport additional-captain estimates are capacity-sizing indicators, not a literal hiring target.
6. Airport trips lack captain_id, so B2 cannot establish individual captain retention.
"""

out = Path("/mnt/data/rapido_updated/deck_outline.md")
out.write_text(deck, encoding="utf-8")
print(out)
