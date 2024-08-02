from process_bigraph import Step, Composite, ProcessTypes, deep_merge


class VolumeFromParticles(Step):
    config_schema = {
        'optimal_density': 'float'}

    def __init__(self, config, core=None):
        super().__init__(config, core)

    def inputs(self):
        return {
            'domains': 'domains'
        }

    def outputs(self):
        return {
            'volumes': 'map[set_float]'}

    def update(self, inputs):
        volumes = {}
        for domain_key, particles in inputs['domains'].items():
            fluid_count = len(particles[1])
            volumes[domain_key] = fluid_count * self.config['optimal_density']

        return {
            'volumes': volumes}
