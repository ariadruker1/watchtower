# Watchtower MVP - Upgraded Agent Architecture

This document outlines the architecture for the enhanced Watchtower agents. These agents are designed as powerful, autonomous entities that leverage a Large Language Model (LLM) to reason, use tools, and make decisions.

Each agent's specific persona, goals, and tools are detailed in its own markdown file in this directory.

## Agent Roles Overview

*   **`MonitoringAgent`**: A high-speed, rule-based filter that constantly watches the raw telemetry stream to identify potential anomalies and trigger the workflow.
*   **`SupervisorAgent`**: The "Operations Chief" that orchestrates the entire workflow between the more advanced, LLM-powered agents.
*   **`DiagnosticAgent`**: The "Veteran Field Engineer" that uses its tools and reasoning to determine the root cause of an anomaly.
*   **`RemediationAgent`**: The "Pragmatic Planner" that designs a safe and effective solution to the diagnosed problem.
*   **`GovernanceAgent`**: The "Meticulous Auditor" that reviews the generated plan for safety and policy compliance.
*   **`ExecutionAgent`**: The "Hands-On Operator" that carries out the approved actions in the simulated environment.

---

## High-Level Agent Interaction Flow

The flowchart below illustrates the complete, cyclical workflow. The process begins with the simple `MonitoringAgent`, which escalates issues to the LLM-powered team. The workflow includes intelligent feedback loops based on the `GovernanceAgent`'s decisions.

```
       [Raw Telemetry Stream]
              |
              v
+-----------------------------+
|      **MonitoringAgent**    |
| (Rule-based filter)         |------> (1) `Alert` object created
+-----------------------------+
              |
              v
+-----------------------------+
|      **SupervisorAgent**    |
+-------------+---------------+
              |
 (2) Forwards `Alert`
              |
              v
+-----------------------------+
|      DiagnosticAgent        |------> (3) Returns: `Incident` object
| (thinks, uses tools)        |
+-----------------------------+
              |
              v
+-------------+---------------+
|      **SupervisorAgent**    |
+-------------+---------------+
              |
 (4) Forwards `Incident`
              |
              v
+-----------------------------+
|      RemediationAgent       |------> (5) Returns: `RemediationPlan` object
| (thinks, creates plan)      |
+-----------------------------+
              |
              v
+-------------+---------------+
|      **SupervisorAgent**    |
+-------------+---------------+
              |
 (6) Forwards `RemediationPlan`
              |
              v
+-----------------------------+
|      GovernanceAgent        |------> (7) Returns: `GovernanceDecision` object
| (audits plan against policy)|       (e.g., `APPROVE`, `REJECT_BAD_PLAN`)
+-----------------------------+
              |
              |
+-------------v---------------+
|      **SupervisorAgent**    |
|   (Routes based on decision)|
+-----------------------------+------------------------------------------------------+
|                                                                                      |
+<--[IF REJECT_BAD_PLAN: Loop back to `RemediationAgent` with feedback]                  |
|                                                                                      |
+<--[IF REJECT_LOW_CONFIDENCE: Loop back to `DiagnosticAgent` with feedback]             |
|                                                                                      |
+---->[IF APPROVE: Continue to Human Operator]-----------------------------------------+
                                      |
                               (8) `RemediationPlan` is ready
                                      |
                                      v
                               +----------------+
                               | Human Operator |
                               +-------+--------+
                                       |
                          +------------+----------------+------------------+
                          |                             |                  |
                          v                             v                  v
                       [If NO]                     [If YES]         [If User provides
                 (Plan is rejected.              (Plan is          an ALTERNATIVE PLAN]
                  Problem persists &            approved)                  |
                  will be re-detected)              |                      |
                                                    +----------+-----------+
                                                               |
                                                               v
                                                 +-----------------------------+
                                                 |      **ExecutionAgent**     |
                                                 | (Executes approved plan)    |-----> (9) Returns: `ExecutionResult`
                                                 +-----------------------------+
                                                               |
                                                               v
                                                 +-----------------------------+
                                                 |      **SupervisorAgent**    |
                                                 | (Logs result, concludes)    |
                                                 +-----------------------------+

```