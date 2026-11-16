# Anomaly Detector Baseline Specification

**Evidrava Point-in-Time Market Evidence Benchmark**

This document specifies the experimental protocol, feature definitions, baseline algorithms, and leakage testing framework for evaluating trading anomaly detectors against the Evidrava registry.

---

## 1. Core Research Objectives

The benchmark measures:
1. **Detection Performance**: Can automated anomaly detectors identify trading manipulation during documented conduct intervals?
2. **Hindsight Leakage Impact (Hypothesis H1)**: Does training or tuning detectors on retrospective ("hindsight") labels inflate recall and early-warning claims compared to models trained strictly on information available at score time `t`?

---

## 2. Baseline Model Families

### A. Statistical Rule Baselines (Unsupervised)
- **Volume Z-Score Rule**:
  $$\text{Z}_{\text{vol}, t} = \frac{V_t - \mu_{V, [t-k, t-1]}}{\sigma_{V, [t-k, t-1]}}$$
  where $k=60$ trading sessions lookback. An alert fires when $\text{Z}_{\text{vol}, t} > \theta_{\text{vol}}$.
- **Return Residual Volatility Rule**:
  Normalized daily return deviation relative to market index (e.g., Nifty 50) beta:
  $$r_{i, t} - (\alpha_i + \beta_i r_{m, t}) > \theta_{\text{ret}} \cdot \sigma_{\epsilon, i}$$

### B. Machine Learning Baselines
- **Isolation Forest (Liu et al., 2008)**:
  - Input features: 5-day, 20-day, and 60-day rolling volume ratios, return skewness, high-low spread ratios, and turnover velocity.
  - Preprocessing: Robust scaling fitted strictly on training folds (`c <= t`).
  - Budget / Contamination factor: Calibrated to yield a target false alert rate (e.g., $\le 10$ alerts per 1,000 instrument sessions).

---

## 3. Strict vs Hindsight Label Definitions (H1 Protocol)

| Aspect | Strict Point-in-Time Setup | Hindsight Setup |
|---|---|---|
| **Label Availability** | An episode is labeled positive only if its disclosure was public by fit cutoff $c \le t$. | Positive labels are assigned using all orders published up to the global collection cutoff $C$. |
| **Conduct Boundary** | Uses only the conduct interval documented in orders public at or before $t$. | Uses post-hoc reconciled conduct intervals from orders published years later. |
| **Universe Definition** | Active traded instruments known on date $t$. | Survivorship-biased retrospective cohort. |

**Leakage Test (Hard Check)**:
Any detector that produces alerts before an episode's verified public disclosure using hindsight features or labels must fail the leakage audit (`LEAKAGE_DETECTED`).

---

## 4. Evaluation Metrics

1. **Episode Recall**:
   $$\text{Recall}_{\text{episode}} = \frac{\text{Episodes with } \ge 1 \text{ alert in conduct interval}}{\text{Total eligible sampled episodes}}$$
2. **Alert Density**:
   $$\text{Alert Rate} = \frac{\text{Total alerts fired}}{\text{Total scored instrument sessions}} \times 1,000$$
3. **Detection Lead Time**:
   Number of active trading sessions between the first alert in the conduct interval and the first verified public disclosure of enforcement proceedings.
4. **Group-Preserving Validation**:
   Cross-validation folds must keep whole related-matter groups in the same partition (`train` or `test`) to prevent intra-case information contamination.
