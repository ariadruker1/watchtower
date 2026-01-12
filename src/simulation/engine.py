import json
import random

class SimulationEngine:
    def __init__(self, topology_file='watchtower_mvp/config/topology.json'):
        self.towers = self._load_topology(topology_file)
        self.telemetry = self._initialize_telemetry()
        self.anomaly = None
        self.anomaly_details = {}

    def _load_topology(self, topology_file):
        try:
            with open(topology_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _initialize_telemetry(self):
        telemetry = {}
        for tower in self.towers:
            telemetry[tower['id']] = self._generate_normal_metrics(tower['id'])
        return telemetry

    def _generate_normal_metrics(self, tower_id):
        # Find tower name from topology
        tower_name = "Unknown"
        for tower in self.towers:
            if tower['id'] == tower_id:
                tower_name = tower['name']
                break
        return {
            'tower_id': tower_id,
            'tower_name': tower_name,
            'power_level': round(random.uniform(95.0, 100.0), 2),
            'signal_strength': round(random.uniform(-50.0, -40.0), 2),
            'data_throughput': round(random.uniform(800.0, 1200.0), 2),
            'status': 'OK'
        }

    def tick(self):
        for tower_id in self.telemetry.keys():
            # Reset status to normal before applying any anomalies
            self.telemetry[tower_id] = self._generate_normal_metrics(tower_id)

        if self.anomaly:
            target_id = self.anomaly_details.get('target')
            if target_id:
                self._apply_anomaly(target_id)
            
            cascading_target_id = self.anomaly_details.get('cascading_target')
            if self.anomaly == 'FIBER_CUT' and cascading_target_id:
                self._apply_cascading_outage(cascading_target_id)

        return self.telemetry.copy()

    def inject_anomaly(self, problem_type):
        self.anomaly = problem_type
        self.anomaly_details = {}
        if not self.towers:
            return

        target_tower = random.choice(self.towers)
        self.anomaly_details['target'] = target_tower['id']

        if problem_type == 'FIBER_CUT':
            other_towers = [t for t in self.towers if t['id'] != target_tower['id']]
            if other_towers:
                cascading_target = random.choice(other_towers)
                self.anomaly_details['cascading_target'] = cascading_target['id']
                # The main target is also affected
                self.anomaly_details['main_target_also_affected'] = True


    def _apply_anomaly(self, tower_id):
        if self.anomaly == 'POWER_OUTAGE':
            self.telemetry[tower_id]['power_level'] = 0.0
            self.telemetry[tower_id]['signal_strength'] = -120.0
            self.telemetry[tower_id]['data_throughput'] = 0.0
            self.telemetry[tower_id]['status'] = 'DOWN'
        elif self.anomaly == 'FIBER_CUT':
            self.telemetry[tower_id]['power_level'] = round(random.uniform(95.0, 100.0), 2)
            self.telemetry[tower_id]['signal_strength'] = -120.0
            self.telemetry[tower_id]['data_throughput'] = 0.0
            self.telemetry[tower_id]['status'] = 'DOWN'
        elif self.anomaly == 'SIGNAL_INTERFERENCE':
            self.telemetry[tower_id]['signal_strength'] = round(random.uniform(-80.0, -70.0), 2)
            self.telemetry[tower_id]['data_throughput'] = round(random.uniform(100.0, 300.0), 2)
            self.telemetry[tower_id]['status'] = 'ALARM'

    def _apply_cascading_outage(self, tower_id):
        self.telemetry[tower_id]['power_level'] = round(random.uniform(95.0, 100.0), 2)
        self.telemetry[tower_id]['signal_strength'] = -110.0
        self.telemetry[tower_id]['data_throughput'] = 50.0
        self.telemetry[tower_id]['status'] = 'ALARM'
