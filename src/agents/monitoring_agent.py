"""
Monitoring Agent: Watches network metrics like power and signal strength, then generates alerts
whenever anything looks abnormal so the system can investigate and fix the problem.
"""

from src.data_models import Alert
import time

class MonitoringAgent:
    def __init__(self):
        self.thresholds = {
            'power_level': (10.0, 100.0),
            'signal_strength': (-90.0, -30.0),
            'data_throughput': (100.0, 1500.0)
        }

    def analyze_telemetry(self, telemetry_data: dict) -> list[Alert]:
        alerts = []
        for tower_id, metrics in telemetry_data.items():
            status = metrics.get('status')
            if status == 'DOWN':
                alerts.append(Alert(
                    tower_id=tower_id,
                    metric='status',
                    value=-1, # Sentinel value for DOWN
                    timestamp=time.time(),
                    message=f"Tower {tower_id} is completely DOWN."
                ))
            elif status == 'ALARM':
                alerts.append(Alert(
                    tower_id=tower_id,
                    metric='status',
                    value=0, # Sentinel value for ALARM
                    timestamp=time.time(),
                    message=f"Tower {tower_id} is in ALARM state."
                ))

            for metric, value in metrics.items():
                if metric in self.thresholds:
                    min_val, max_val = self.thresholds[metric]
                    if not (min_val <= value <= max_val):
                        alerts.append(Alert(
                            tower_id=tower_id,
                            metric=metric,
                            value=value,
                            timestamp=time.time(),
                            message=f"Metric '{metric}' out of range ({value})."
                        ))
        return alerts
