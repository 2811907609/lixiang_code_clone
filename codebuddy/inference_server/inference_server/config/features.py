class FeatureGate:

    def __init__(self):
        # Initialize the feature flags
        self.flags = {
            # will disable stop words, and prompt truncate when benchmark
            'in_benchmark': False,
        }

    def is_enabled(self, feature):
        """Check if a feature is enabled."""
        return self.flags.get(feature, False)

    def set_feature(self, feature, value):
        """Enable or disable a feature."""
        if feature not in self.flags:
            raise ValueError(f"Feature {feature} is not recognized.")
        self.flags[feature] = value

    @property
    def benchmark(self):
        return self.flags['in_benchmark']

    @benchmark.setter
    def benchmark(self, value: bool):
        self.flags['in_benchmark'] = value


feature_gate = FeatureGate()
