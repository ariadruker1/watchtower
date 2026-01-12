# Watchtower MVP - AI Self-Healing Demo Plan

## 1. Objective
Create a Python-based command-line application in under one hour that demonstrates an AI-driven "self-healing" workflow for common telecom network outages. The demo will showcase problem detection, AI-driven diagnosis, governance, human approval, and simulated remediation.

## 2. Core Workflow
1.  **Problem Generation**: The simulation will randomly inject one of three predefined failure scenarios at a random time.
2.  **Detection**: A `MonitoringAgent` will detect anomalous metrics in the telemetry stream.
3.  **Diagnosis & Planning**: A `SupervisorAgent` will orchestrate a workflow where a `DiagnosticAgent` identifies the root cause and a `RemediationAgent` proposes a solution.
4.  **Governance**: A `GovernanceAgent` will audit the process against a predefined policy (`policy.yaml`).
5.  **Human Approval**: The simulation will pause and present the final, validated plan to a human operator for a Y/N approval.
6.  **Action**: Upon approval, the `RemediationAgent` will execute a simulated action (e.g., dispatching a truck).

## 3. Failure Scenarios
The simulation will randomly select from:
- **Power Outage**: A single tower loses power.
- **Fiber Cut**: A major fiber link is severed, causing a cascading outage of multiple towers.
- **Signal Interference**: A tower's performance is degraded by RF interference, presenting subtle, fluctuating metrics.

## 4. Agent Architecture
- **`MonitoringAgent`**: Detects metric deviations.
- **`DiagnosticAgent`**: Diagnoses the root cause from alerts.
- **`RemediationAgent`**: Proposes solutions based on a `runbooks.yaml` file.
- **`GovernanceAgent`**: Audits decisions against `policy.yaml`.
- **`SupervisorAgent`**: The orchestrator. Manages the workflow, boosts confidence for persistent issues, and interfaces with the human operator.

## 5. Terminal UI Design (`rich` library)
The `run_demo.py` script will use `rich` to render a three-panel layout:
- **Panel 1 (Left - Live Status)**: A continuously updating table showing the status (`OK`, `ALARM`, `DOWN`) and key metrics for all cell towers.
- **Panel 2 (Right - Agent Log)**: A log panel that streams the "thoughts" and decisions of the AI agents in real-time.
- **Panel 3 (Bottom - User Input)**: A dedicated area that is normally hidden but appears specifically to prompt the user for "Y/N" approval when a decision is required.
