class ScenarioEngine:

    def simulate(self, base_demand, growth_percent):

        future = base_demand * (1 + growth_percent / 100)

        return {
            "current": base_demand,
            "simulated": future,
            "increase": future - base_demand,
        }
