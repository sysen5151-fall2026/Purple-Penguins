# Recipe Roulette — Risk Register

## 1. Purpose

This document identifies, evaluates, and tracks system-level risks associated with the development and operation of Recipe Roulette.

The risk register supports the Chapter 12 Risk Management activities for SYSEN 5151 and provides traceability between identified risks, system architecture elements, mitigation strategies, and verification activities.

Risk likelihood and impact ratings were determined by the project team.

## 2. Risk Identification

The following risks were identified based on the Recipe Roulette system architecture, external interfaces, and expected operational behavior.

**Table 6: Risk Register**

| ID | Risk Description | IDEF0 Connection | Type | Lifecycle Phase |
|---|---|---|---|---|
| R1 | LLM service becomes unavailable or excessively slow. | App ↔ LLM API | Technical — Availability | Development, Operations & Maintenance |
| R2 | Generated recipes or prices are incorrect or violate dietary restrictions. | LLM output validation | Technical — Performance | Development & Testing |
| R3 | Grocery pricing information becomes unavailable or outdated. | Grocery Store / pricing interface | Technical — Data Integrity | Development, Operations & Maintenance |
| R4 | User information is exposed through an external service. | User input and API integration | Security — Privacy | Design, Development & Operations |
| R5 | External API usage exceeds the application's operating budget. | LLM request handling | Financial — Cost | Development, Operations & Maintenance |

**Architecture note:** R3's IDEF0 connection reflects the original risk identification table. Because the current implementation uses LLM-based pricing with store and location inputs, this connection should be reconciled with the latest Innoslate architecture before submission.

## 3. Risk Assessment Methodology

Each risk is evaluated using likelihood and impact ratings on a five-point scale.

### 3.1 Likelihood Scale

| Rating | Classification |
|---|---|
| 1 | Very Low |
| 2 | Low |
| 3 | Moderate |
| 4 | High |
| 5 | Very High |

### 3.2 Impact Scale

| Rating | Classification |
|---|---|
| 1 | Very Low |
| 2 | Low |
| 3 | Moderate |
| 4 | High |
| 5 | Very High |

Each risk is evaluated independently for its potential impact on:

- **Cost:** Additional expenses required to address the risk.
- **Schedule:** Delays to project development, testing, or operation.
- **Technical Performance:** Reduction in system functionality, reliability, accuracy, or compliance with requirements.

### 3.3 Overall Impact

The overall impact is determined by selecting the highest rating among the three impact categories.

**Overall Impact = Maximum (Cost Impact, Schedule Impact, Technical Impact)**

### 3.4 Overall Risk Score

The overall risk score is calculated by multiplying the likelihood rating by the overall impact rating.

**Overall Risk Score = Likelihood × Overall Impact**

Possible risk scores range from 1 to 25.

These calculations are used to prioritize risks requiring further mitigation and monitoring.

## 4. Populated Risk Assessment

**Table 7: Populated Risk Table**

| ID | Likelihood | Impact Cost | Impact Schedule | Impact Technical | Overall Impact | Overall Risk Score |
|---|---:|---:|---:|---:|---:|---:|
| R1 | 3 | 1 | 3 | 4 | 4 | **12** |
| R2 | 2 | 1 | 1 | 3 | 3 | **6** |
| R3 | 2 | 3 | 1 | 3 | 3 | **6** |
| R4 | 2 | 1 | 1 | 4 | 4 | **8** |
| R5 | 3 | 4 | 1 | 3 | 4 | **12** |

The assessment identifies R1 and R5 as the highest-scoring risks, each with an overall risk score of 12.

R1 concerns the availability and response time of the LLM service. R5 concerns the financial impact of external API usage exceeding the application's operating budget.

Both risks require consideration during system development and operation.

## 5. Risk Matrix

The following matrix places each identified risk according to its likelihood and overall impact ratings.

| Likelihood ↓ / Overall Impact → | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **5 — Very High** | — | — | — | — | — |
| **4 — High** | — | — | — | — | — |
| **3 — Moderate** | — | — | — | R1, R5 | — |
| **2 — Low** | — | — | R2, R3 | R4 | — |
| **1 — Very Low** | — | — | — | — | — |

The matrix indicates that R1 and R5 have the greatest overall risk scores under the team's assessment methodology.

The risk matrix should remain consistent with the corresponding Chapter 12 risk assessment in the team's systems engineering documentation.

## 6. Highest-Priority Risk Mitigation Plan

**Proposed Top Risk: R1 — LLM Service Becomes Unavailable or Excessively Slow**

R1 and R5 are tied for the highest score. R1 is proposed here for the detailed mitigation plan because Recipe Roulette already contains a communication retry mechanism associated with the UC.7 loss-of-communication use case.

**The team must confirm this selection before final submission.**

### 6.1 Risk Description

Recipe Roulette relies on an external LLM service to generate recipe recommendations and estimate ingredient prices.

If communication with the LLM service is interrupted, experiences excessive latency, or becomes unavailable, the application may be unable to complete the requested recipe-generation workflow.

This could negatively affect system availability, user experience, and compliance with functional requirements.

### 6.2 Risk Response Strategy

**Mitigate**

The proposed mitigation strategy is to limit communication retries, manage request failures, and provide controlled error responses when the LLM service remains unavailable.

The objective is to prevent uncontrolled request attempts while allowing the application to recover from temporary communication failures.

### 6.3 Implemented Fallback

Recipe Roulette includes an LLM communication retry mechanism designed to support recovery from temporary connection failures.

The reported implementation:

- Allows a maximum of 10 total LLM request attempts, consisting of one initial request and up to nine retries.
- Stops retrying immediately after a successful response.
- Retries qualifying communication failures and selected temporary HTTP errors.
- Uses capped backoff between attempts.
- Disables automatic retries within the OpenAI SDK to prevent hidden additional attempts.
- Returns a controlled error when the retry limit is exhausted.
- Logs the final communication failure without exposing credentials or sensitive provider details.

This mechanism is classified as a **fallback**, because it attempts to recover from temporary communication interruptions and contains the failure when recovery is unsuccessful.

The retry mechanism primarily addresses loss of communication and transient unavailability. Excessive latency is addressed only to the extent supported by configured request timeouts and retry limits; it does not guarantee a maximum end-to-end response time.

### 6.4 Verification Evidence

The development team previously conducted automated tests using simulated OpenAI API failures.

The reported test cases verified:

| Test Scenario | Expected Result | Reported Result |
|---|---|---|
| Immediate successful response | One API request | Passed |
| Temporary failure followed by recovery | Retry until successful | Passed |
| Persistent communication failure | Stop after 10 total attempts | Passed |
| Recovery on the tenth attempt | Return successfully without an eleventh request | Passed |
| Retry exhaustion | Return controlled failure | Passed |
| Automatic SDK retries | No additional hidden attempts | Passed |
| Failure-event logging | Log safely without exposing credentials | Passed |

The retry-focused validation previously reported 18 passing integration tests.

These results provide automated verification evidence for the UC.7 communication failsafe. The team should reconfirm the tests against the final submitted repository branch.

### 6.5 Residual Risk

Although the retry mechanism improves resilience, it does not eliminate the possibility that the LLM service will remain unavailable.

Persistent outages may still prevent Recipe Roulette from providing recipe recommendations.

Repeated attempts may also increase response latency and API usage costs, creating a relationship between R1 and R5.

The risk therefore requires continued monitoring.

## 7. Risk Monitoring and Tracking Plan

The following monitoring activities are proposed for R1 during development, integration, and testing, before operational deployment.

| Monitoring Item | Method | Purpose |
|---|---|---|
| LLM communication failures | Review sanitized application logs | Identify repeated or persistent service failures |
| Number of request attempts | Automated retry tests and request counting | Verify the maximum of 10 total attempts |
| Retry exhaustion | Simulate persistent service failure | Verify controlled failure handling |
| LLM response time | Collect request timing measurements | Identify excessive latency |
| API error frequency | Review error classifications during testing | Detect recurring provider availability issues |
| API request consumption | Review request counts and usage data | Identify cost impacts associated with retries |

### 7.1 Monitoring Triggers

The following conditions should trigger investigation:

- An LLM request exceeds the configured retry limit.
- Persistent failures repeatedly result in controlled service-unavailable responses.
- LLM response times exceed team-defined acceptable performance thresholds.
- Changes to the OpenAI adapter or SDK invalidate previously verified retry behavior.
- API usage associated with retry attempts approaches the application's operating budget.

### 7.2 Responsible Personnel

**Risk Owner:** Recipe Roulette Development Team

A specific team member should be assigned responsibility for maintaining the risk register and reviewing monitoring evidence before final submission.

### 7.3 Monitoring Frequency

Risk R1 should be reviewed during development and integration testing, particularly after modifications to the LLM API interface, error-handling implementation, or retry configuration.

The risk assessment should be updated if new evidence indicates a change in likelihood or impact.

## 8. Model and Requirements Traceability

The risk register is intended to maintain traceability between the risk assessment, the Innoslate architecture, the system requirements, and the implemented product.

| Risk ID | Related System Element | Relevant Verification or Mitigation Area |
|---|---|---|
| R1 | App ↔ LLM API; UC.7 Loss of Communication with LLM API | Retry limit, communication failures, controlled error handling |
| R2 | LLM output validation | Recipe correctness, dietary restrictions, pricing validation |
| R3 | Grocery pricing interface / current LLM pricing process | Pricing availability, estimate quality, data integrity |
| R4 | User input and external API integration | Data handling, API credentials, privacy controls |
| R5 | LLM request handling | API request monitoring, retry consumption, operating costs |

### 8.1 Related Requirement

**STH.1.1.14 — LLM Communication Retry Limit**

The requirement should specify that the system makes a maximum of 10 total communication attempts, including the initial request, to remain consistent with the implemented retry behavior and the Innoslate Sys.2.4.2 model element.

### 8.2 Related Use Case

**UC.7 — Loss of Communication with LLM API**

This use case models the system response when communication with the external LLM service fails.

The retry implementation and associated automated tests provide verification evidence for the communication failure behavior represented in this model.

## 9. Risk Register Maintenance

The Recipe Roulette Development Team is responsible for maintaining this risk register throughout the remaining development lifecycle.

The register should be reviewed when:

- System architecture or external dependencies change.
- New risks are identified during testing.
- Existing mitigation strategies are modified.
- Requirements or interface contracts are revised.
- Test evidence reveals new failure conditions.
- The assessed likelihood or impact of a risk changes.

Any changes to risk ratings should be reviewed and approved by the team and reflected consistently in the systems engineering model and project documentation.

---

**Project:** Recipe Roulette  
**Course:** SYSEN 5151 — Systems Engineering  
**Team:** Purple Penguins  
**Document:** Product Risk Register  
**Reference:** Chapter 12 — Risk Management