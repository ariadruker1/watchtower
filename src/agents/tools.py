"""
Tools: Provides agents with functions to look up real information like weather, maintenance history, policies,
and engineer schedules so they base their decisions on facts instead of making things up.
"""

import random
import yaml
from typing import Optional, Dict, Any
from pathlib import Path


# Tool definitions for Claude tool_use
TOOLS_SCHEMA = [
    {
        "name": "get_weather_at_tower",
        "description": "Checks for severe weather conditions near a specific cell tower",
        "input_schema": {
            "type": "object",
            "properties": {
                "tower_id": {"type": "string", "description": "Cell tower ID (e.g., 'T001')"}
            },
            "required": ["tower_id"]
        }
    },
    {
        "name": "get_tower_maintenance_history",
        "description": "Retrieves recent maintenance logs for a specific cell tower",
        "input_schema": {
            "type": "object",
            "properties": {
                "tower_id": {"type": "string", "description": "Cell tower ID"}
            },
            "required": ["tower_id"]
        }
    },
    {
        "name": "check_regional_news_alerts",
        "description": "Scans for public reports of major events in a given region that might affect network",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Region name (e.g., 'New York City')"}
            },
            "required": ["region"]
        }
    },
    {
        "name": "lookup_telecom_pattern",
        "description": "Look up known telecom failure patterns and their characteristics from knowledge base",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_type": {
                    "type": "string",
                    "description": "Incident type (POWER_OUTAGE, FIBER_CUT, SIGNAL_INTERFERENCE, etc.)"
                }
            },
            "required": ["incident_type"]
        }
    },
    {
        "name": "get_standard_operating_procedure",
        "description": "Fetches the official runbook for a given type of incident",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_type": {"type": "string", "description": "Incident type"}
            },
            "required": ["incident_type"]
        }
    },
    {
        "name": "get_on_call_engineer_schedule",
        "description": "Checks the schedule to find which specialist teams are available for dispatch",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_company_policy_document",
        "description": "Retrieves specific sections of the company's network operations policy",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Policy section (customer_impact_thresholds, remediation_risk_levels, default)"
                }
            },
            "required": ["section"]
        }
    }
]


def get_weather_at_tower(tower_id: str) -> Dict[str, Any]:
    """Checks for severe weather conditions near a specific cell tower."""
    conditions = [
        "Clear skies, no weather hazards",
        "Light rain, 0.2 inches/hour",
        "Heavy thunderstorms with lightning risk",
        "High winds 45+ mph, potential infrastructure stress"
    ]
    if random.random() < 0.1:
        condition = random.choice(conditions[2:])
        severity = "HIGH"
    else:
        condition = conditions[0]
        severity = "LOW"

    return {
        "tower_id": tower_id,
        "condition": condition,
        "severity": severity,
        "source": "weather_api_mock"
    }


def get_tower_maintenance_history(tower_id: str) -> Dict[str, Any]:
    """Retrieves recent maintenance logs for a specific cell tower."""
    histories = [
        "No recent maintenance. Site stable for 6 months.",
        "Routine inspection performed 2 weeks ago. All systems nominal.",
        f"Power unit (PSU) replaced 3 months ago. Functioning normally.",
        "Signal calibration performed last week. RF performance verified."
    ]
    return {
        "tower_id": tower_id,
        "recent_activity": random.choice(histories),
        "source": "maintenance_db_mock"
    }


def check_regional_news_alerts(region: str) -> Dict[str, Any]:
    """Scans for public reports of major events in a given region."""
    alerts = [
        "No major events reported affecting infrastructure.",
        "Commercial power outage reported in downtown area (scheduled maintenance).",
        "Major fiber optic cable cut by construction work on interstate.",
        "Wildfires reported in northern region, potential risk to power infrastructure."
    ]
    if random.random() < 0.05:
        alert = random.choice(alerts[1:])
        has_events = True
    else:
        alert = alerts[0]
        has_events = False

    return {
        "region": region,
        "alert": alert,
        "has_relevant_events": has_events,
        "source": "news_api_mock"
    }


def lookup_telecom_pattern(incident_type: str) -> Dict[str, Any]:
    """Look up known telecom failure patterns from knowledge base."""
    config_path = Path(__file__).parent.parent.parent / "config" / "telecom_patterns.yaml"
    try:
        with open(config_path, 'r') as f:
            patterns = yaml.safe_load(f)
            pattern = patterns.get(incident_type)
            if pattern:
                return {
                    "incident_type": incident_type,
                    "found": True,
                    "data_signature": pattern.get('data_signature'),
                    "common_causes": pattern.get('common_causes', []),
                    "confidence_indicators": pattern.get('confidence_indicators', []),
                    "risk_level": pattern.get('risk_level', 'UNKNOWN')
                }
            else:
                return {
                    "incident_type": incident_type,
                    "found": False,
                    "message": f"No pattern found for {incident_type}"
                }
    except FileNotFoundError:
        return {
            "incident_type": incident_type,
            "found": False,
            "message": "Telecom patterns KB not found"
        }


def get_standard_operating_procedure(incident_type: str) -> Dict[str, Any]:
    """Fetches the official runbook for a given type of incident."""
    config_path = Path(__file__).parent.parent.parent / "config" / "runbooks.yaml"
    try:
        with open(config_path, 'r') as f:
            runbooks = yaml.safe_load(f)
            procedure = runbooks.get(incident_type)
            if procedure:
                return {
                    "incident_type": incident_type,
                    "found": True,
                    "description": procedure.get('description'),
                    "action_template": procedure.get('action_template')
                }
            else:
                return {
                    "incident_type": incident_type,
                    "found": False,
                    "message": f"No runbook found for {incident_type}"
                }
    except FileNotFoundError:
        return {
            "incident_type": incident_type,
            "found": False,
            "message": "Runbooks file not found"
        }


def get_on_call_engineer_schedule() -> Dict[str, Any]:
    """Checks the schedule to find which specialist teams are available for dispatch."""
    teams = [
        "Response Team Alpha (Fiber Optics Specialists)",
        "Response Team Bravo (Power and Electrical Specialists)",
        "Service Unit Charlie (RF and Spectrum Specialists)"
    ]
    available_team = random.choice(teams)
    return {
        "available_team": available_team,
        "eta_minutes": random.randint(30, 90),
        "source": "engineer_schedule_mock"
    }


def get_company_policy_document(section: str) -> Dict[str, Any]:
    """Retrieves specific sections of the company's network operations policy."""
    policies = {
        "customer_impact_thresholds": (
            "Policy 4.1.a: Any remediation plan affecting >1,000 subscribers "
            "must have plan_confidence >= 0.9"
        ),
        "remediation_risk_levels": (
            "Policy 8.2.c: Physical dispatch = MEDIUM risk minimum. "
            "Core traffic rerouting = HIGH risk minimum."
        ),
        "default": "Prioritize: (1) Service restoration (2) Customer impact (3) Personnel safety"
    }
    content = policies.get(section, policies.get('default'))
    return {
        "section": section,
        "found": True,
        "content": content,
        "source": "policy_db_mock"
    }


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with given input."""
    tools_map = {
        'get_weather_at_tower': get_weather_at_tower,
        'get_tower_maintenance_history': get_tower_maintenance_history,
        'check_regional_news_alerts': check_regional_news_alerts,
        'lookup_telecom_pattern': lookup_telecom_pattern,
        'get_standard_operating_procedure': get_standard_operating_procedure,
        'get_on_call_engineer_schedule': get_on_call_engineer_schedule,
        'get_company_policy_document': get_company_policy_document,
    }

    tool_func = tools_map.get(tool_name)
    if not tool_func:
        return {'error': f'Unknown tool: {tool_name}'}

    try:
        # Call the tool with unpacked input
        return tool_func(**tool_input)
    except Exception as e:
        return {'error': str(e), 'tool': tool_name}
