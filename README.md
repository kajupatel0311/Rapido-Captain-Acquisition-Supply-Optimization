# Rapido Captain Acquisition & Supply Optimization

Data Science take-home focused on improving captain onboarding, approval, activation, and airport supply.

## 1. Problem

The goal of this analysis is to understand where captain acquisition is losing potential supply and identify practical interventions that can increase the number of captains who become productive.

The analysis covers two connected problems:

- Captain onboarding and document completion
- Airport demand-supply mismatch

The main business metric used in the decision analysis is not just signup or approval volume. The focus is on moving captains further through the funnel and ultimately increasing first-order completions.

---

## 2. Business Questions

### Part A — Captain Acquisition

1. What does the signup → approval → first-order funnel look like?
2. Which onboarding stage and captain segments have the largest actionable leakage?
3. Does `CAMP_WA_002` appear to improve captain approval?
4. What interventions should be prioritized based on expected business impact?

### Part B — Supply Optimization

1. Where and when does airport demand exceed available captain supply?
2. What happens to trips after airport pickups?
3. Should Rapido acquire more captains specifically for airport demand?

---

## 3. Data

The project uses the synthetic datasets provided for the assignment.

### Captain and onboarding data

- `captains.csv`
- `doc_events.csv`
- `approvals.csv`
- `activation.csv`
- `nudges.csv`

### Airport data

- `airport_hourly.csv`
- `airport_trips.csv`

The extraction cutoff specified in the assignment is:

`2026-06-30 23:59 IST`

The document sequence is:

`DL → RC → Aadhaar → Permit → Fitness → Insurance`

Permit is required for Auto and Cab. ERickshaw does not require a Permit.

---

## 4. Project Structure

```text
Rapido_Data_Science/
│
├── data/
│   ├── raw/
│   │   └── input CSV files
│   └── processed/
│       ├── captains_clean.csv
│       ├── doc_events_clean.csv
│       ├── approvals_clean.csv
│       ├── activation_clean.csv
│       ├── airport_hourly_clean.csv
│       └── captain_master.csv
│
├── notebooks/
│   └── analysis.ipynb
│
├── src/
│   ├── config.py
│   ├── data_loader.py
│   │
│   ├── data_quality/
│   │   └── audit.py
│   │
│   ├── preprocessing/
│   │   ├── clean.py
│   │   └── master_table.py
│   │
│   ├── onboarding/
│   │   ├── funnel.py
│   │   └── leak_analysis.py
│   │
│   ├── campaign/
│   │   └── campaign_analysis.py
│   │
│   ├── airport/
│   │   └── airport_analysis.py
│   │
│   └── decision/
│       └── decision_analysis.py
│
├── outputs/
│   ├── results/
│   ├── tables/
│   └── charts/
│
├── reports/
│   ├── memo/
│   └── deck/
│
├── run_analysis.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 5. Approach

The analysis is organized as a reproducible pipeline rather than a collection of manually generated tables.

```text
Raw CSVs
   ↓
Data quality checks
   ↓
Cleaning and normalization
   ↓
Captain master table
   ↓
Funnel analysis
   ↓
Segment-level leak analysis
   ↓
Campaign evaluation
   ↓
Airport supply analysis
   ↓
Decision engine
   ↓
Business recommendations
```

### Data quality

Before analysis, the pipeline checks for issues such as:

- Missing or duplicate captain IDs
- Invalid vehicle types
- Invalid document types
- Invalid document event types
- Invalid attempt numbers
- Orphan captain IDs
- Invalid approval statuses
- Invalid airport metrics
- Invalid hours
- Request/fulfillment mismatches
- Signup dates outside the assignment cutoff

The current run completed the quality checks with:

`0 issues detected`

Missing values are not blindly dropped. Validation and analytical filtering are handled separately so that data-quality problems are visible rather than silently removed.

---

## 6. Funnel Definition

The onboarding funnel follows the document order specified in the assignment.

A captain is counted as having cleared a document when a valid `verification_pass` event is present.

For Permit:

- Auto → Permit required
- Cab → Permit required
- ERickshaw → Permit not required

The final funnel is:

| Stage | Captains | Stage Conversion | Cumulative Conversion |
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

The biggest post-approval opportunity is also visible here:

`4,206 approved → 1,610 first orders`

This means 2,596 approved captains did not complete a first order in the observed data.

---

## 7. Key Findings

### 7.1 Onboarding

Only `6.4%` of signups reach a completed first order.

The largest absolute document-stage loss occurs at Insurance:

- 8,241 reached the stage
- 4,664 cleared it
- 3,577 were lost

However, absolute drop-off alone is not used to choose the intervention. Segment size, stage leakage, and downstream value are considered together.

### 7.2 Highest-priority onboarding segments

The decision analysis identifies Permit completion among Auto/Cab captains as the strongest actionable segment-level opportunity.

Examples include:

- Pune Auto, organic_app
- Hyderabad Cab, organic_app
- Hyderabad Auto, organic_app
- Bangalore Cab, organic_app
- Pune Auto, referral

For example, Pune Auto + organic_app at the Permit stage has:

- 1,172 captains reaching the stage
- 744 not cleared
- 20% recovery scenario
- 148.8 scenario incremental approvals
- approximately 57 expected first orders using the observed 38.3% approval-to-first-order rate

These numbers are scenario estimates, not measured causal impact.

### 7.3 Monthly onboarding opportunity

Using mature signup cohorts and a 20% relative reduction in stage non-clearance, the scenario model estimates approximately:

- Permit: `396.6` incremental approvals/month
- RC: `122.1`
- DL: `45.8`
- Aadhaar: `17.9`
- Fitness: `5.9`

The Permit estimate is therefore the main number used for prioritization.

---

## 8. CAMP_WA_002

The campaign analysis compares captains exposed to `CAMP_WA_002` with the control group.

### Observed result

- Treatment: 8,673 captains
- Control: 16,327 captains
- Treatment approval rate: 28.5%
- Control approval rate: 10.6%
- Observed lift: +17.9 percentage points
- 95% CI: +16.8 to +19.0 percentage points

After adjusting for available captain characteristics:

- Adjusted treatment probability: 27.6%
- Adjusted control probability: 10.9%
- Adjusted lift: +16.7 percentage points
- Odds ratio: 3.26

The result is statistically strong, but the campaign exposure was not randomized.

Therefore, the analysis treats this as an observational association rather than a causal estimate.

### Recommendation

Run a randomized holdout before scaling the campaign broadly.

The experiment should measure:

- Incremental approval
- Time to approval
- First-order conversion
- Cost per incremental approved captain
- Cost per incremental first-order captain

---

## 9. Airport Supply Analysis

The airport analysis shows a clear demand-supply mismatch at airport terminals compared with CBD zones.

The most problematic period is concentrated around:

`21:00–03:00`

The highest-gap hours include:

`22:00, 23:00, 01:00, 02:00, 00:00, 21:00`

Late-night airport trips also show:

- Higher cancellation rate: 17.09%
- Lower return-fare-within-20-min rate: 29.84%

For comparison, overall airport-trip cancellation is 13.77% and return fare within 20 minutes is 35.96%.

---

## 10. Acquisition Recommendation

The analysis does not recommend immediately acquiring a large number of airport-focused captains.

The preferred sequence is:

```text
Identify airport shortage
        ↓
Target the 21:00–03:00 window
        ↓
Use incentives / reposition existing supply
        ↓
Measure fulfillment and cancellations
        ↓
If the gap remains
        ↓
Run targeted acquisition
```

This is preferable to broad acquisition because the supply problem is concentrated in specific locations and hours.

If acquisition is required, it should be targeted using:

- Airport zone
- Hour
- Vehicle type
- Supply gap
- Expected utilization

---

## 11. Decision Framework

The project uses a simple decision framework focused on productive supply.

For onboarding interventions:

```text
Recoverable captains
        ×
Downstream approval probability
        ×
Approval → First Order rate
        =
Expected incremental first orders
```

The current scenario uses:

- Recovery rate: `20%`
- Approval → First Order rate: `38.3%`

These are assumptions for prioritization and are not causal estimates.

For airport supply:

```text
Demand gap
    ↓
Existing supply intervention
    ↓
Controlled measurement
    ↓
Targeted acquisition if required
```

The objective is to increase productive captain supply rather than maximize signup volume alone.

---

## 12. Recommendations

### 1. Improve Permit completion

Prioritize Auto/Cab segments with high Permit leakage, especially in Pune and Hyderabad.

Use targeted document guidance and assisted resolution for repeated failures.

**Impact:** Approximately 397 incremental approvals/month under the 20% recovery scenario.

**Cost:** Low to medium

**Risk:** Low to medium

---

### 2. Validate CAMP_WA_002 with a holdout

The campaign has a strong observed and adjusted association with approval.

Before scaling, run a randomized experiment to measure true incremental impact.

**Impact:** Potentially significant, but causal impact is not established yet.

**Cost:** Low

**Risk:** Medium

---

### 3. Improve Approved → First Order conversion

There are 2,596 approved captains who do not complete a first order.

Potential interventions include:

- First-order nudges
- Activation incentives
- Zone-specific supply opportunities
- Assisted activation

The primary metric should be incremental first orders rather than approval volume alone.

---

### 4. Fix airport late-night supply before broad acquisition

Use targeted incentives and repositioning during the 21:00–03:00 shortage window.

Only add acquisition after measuring whether existing-supply interventions are insufficient.

---

## 13. Outputs

The pipeline generates the following outputs.

### Processed data

```text
data/processed/captains_clean.csv
data/processed/doc_events_clean.csv
data/processed/approvals_clean.csv
data/processed/activation_clean.csv
data/processed/airport_hourly_clean.csv
data/processed/captain_master.csv
```

### Results

```text
outputs/results/data_quality_report.json
outputs/results/intervention_priority.json
outputs/results/campaign_confidence.json
```

### Analysis tables

```text
outputs/tables/onboarding_funnel.csv
outputs/tables/document_funnel.csv
outputs/tables/document_dropoff.csv
outputs/tables/document_failure_reasons.csv
outputs/tables/a2_actionable_segments.csv
outputs/tables/a2_approval_opportunity.csv
outputs/tables/a2_segment_leaks.csv
outputs/tables/intervention_priority.csv
outputs/tables/campaign_descriptive.csv
outputs/tables/airport_hourly_summary.csv
outputs/tables/airport_zone_summary.csv
outputs/tables/b2_airport_trip_destination.csv
outputs/tables/b2_airport_trip_hourly.csv
outputs/tables/b2_airport_trip_overall.csv
outputs/tables/b3_airport_recommendation.csv
outputs/tables/b3_airport_supply_gap.csv
```

---

## 14. How to Run

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run the complete analysis

```powershell
python run_analysis.py
```

The script reads the raw CSV files from:

```text
data/raw/
```

and writes cleaned data and analysis outputs to:

```text
data/processed/
outputs/
```

---

## 15. Assumptions and Limitations

### Scenario assumptions

The intervention priority model assumes a 20% relative reduction in stage non-clearance.

This is a planning scenario and should not be interpreted as a causal forecast.

### Campaign limitation

`CAMP_WA_002` was not evaluated from a randomized experiment. The adjusted result controls for available variables but cannot remove all selection bias.

### Productivity limitation

The supplied data provides first-order completion, but does not provide a complete long-term captain productivity or contribution margin measure.

Therefore, first-order completion is used as the available proxy for productive activation.

### Airport acquisition limitation

The estimated airport supply gap should not be interpreted as a direct recommendation to acquire that exact number of captains. Existing-supply interventions should be tested first.

---

## 16. Final Business Takeaway

The main opportunity is not simply to acquire more captains.

It is to improve the conversion of acquired captains into productive supply.

The analysis therefore connects:

```text
Captain acquisition
        ↓
Onboarding recovery
        ↓
Approval
        ↓
First-order activation
        ↓
Airport demand-supply matching
        ↓
Productive supply
```

This leads to a practical strategy:

**Fix high-value onboarding friction, validate acquisition interventions experimentally, improve post-approval activation, and acquire new supply only where demand gaps justify it.**

