"""
This module provides a base class for Vivarium processes wrapper of simulation services.
"""

from process_bigraph import Process, ProcessTypes, deep_merge
from simservice.service_factory import process_factory


class SimServiceProcess(Process):
    config_schema = {
        'process_config': {
            'disable_ports': {
                'inputs': 'list[string]',  # a list of input port ids to disable
                'outputs': 'list[string]'  # a list of output port ids to disable
            }
        },
        'simservice_config': 'tree[any]'
    }

    access_methods = {
        'inputs': {},
        'outputs': {}
    }
    service_name = None

    def __init__(self, config=None, core=None):
        super().__init__(config, core)
        assert self.service_name is not None, "Service name must be defined in derived class"

        # TODO -- find a way to parse out simservice config and process config
        self.process_config = self.config.pop('process_config', {})
        self.simservice_config = self.config.pop('simservice_config', {})

        self.service = process_factory(
            self.service_name,
            *[],
            **self.simservice_config)

        self.pre_run(config)
        self.service.run()
        self.on_run(config)
        self.service.init()
        self.on_init(config)
        self.service.start()
        self.on_start(config)

        # complete the access methods with default values ion
        inputs = self.inputs()
        outputs = self.outputs()
        for input_key, schema in inputs.items():
            if input_key not in self.access_methods['inputs']:
                self.access_methods['inputs'][input_key] = f'set_{input_key}'
        for output_key, schema in outputs.items():
            if output_key not in self.access_methods['outputs']:
                self.access_methods['outputs'][output_key] = f'get_{output_key}'

        # check that the access methods exist in the service
        for key, method in self.access_methods['inputs'].items():
            assert hasattr(self.service, method), f"Method {method['set']} not found in service {self.service_name}"
        for key, method in self.access_methods['outputs'].items():
            assert hasattr(self.service, method), f"Method {method['set']} not found in service {self.service_name}"

    def update(self, inputs, interval):
        # print(type(self), inputs)
        # set the inputs
        for key, value in inputs.items():
            # skip disabled ports
            if key in self.process_config['disable_ports']['inputs']:
                continue

            # retrieve the set method and call it
            method = self.access_methods['inputs'][key]
            set_method = getattr(self.service, method)
            set_method(value)

        # step the sim service
        self.service.step()

        # get the outputs
        outputs = {}
        for key, method in self.access_methods['outputs'].items():
            # skip disabled ports
            if key in self.process_config['disable_ports']['outputs']:
                continue

            # retrieve the get method and call it
            get_method = getattr(self.service, method)
            outputs[key] = get_method()

        # print(type(self), outputs)
        return outputs

    def pre_run(self, config=None):
        """To be implemented by derived classes. Called before simulation service call to `run`."""
        pass

    def on_run(self, config=None):
        """To be implemented by derived classes. Called after simulation service call to `run`."""
        pass

    def on_init(self, config=None):
        """To be implemented by derived classes. Called after simulation service call to `init`."""
        pass

    def on_start(self, config=None):
        """To be implemented by derived classes. Called after simulation service call to `start`."""
        pass


if __name__ == "__main__":
    core = ProcessTypes()
    d = core.dataclass({'mask': 'float',
                        'particle': 'map[string]'})
    instance = d(mask=1.0, particle={'name': 'test'})
    instance_dict = instance.to_dict()
