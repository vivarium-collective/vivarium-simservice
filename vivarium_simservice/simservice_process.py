from process_bigraph import Process
from simservice.service_factory import process_factory


class SimServiceProcess(Process):
    config_schema = {
        'service_name': 'string',
        'args': 'list[any]',
        'kwargs': 'tree[any]',
        'annotations': 'tree[any]'
    }

    def __init__(self, config=None, core=None):
        super().__init__(config, core)

        self.annotations = self.config['annotations']
        """To be particularized by both a service provider and user"""

        service_name = self.config['service_name']
        self.service = process_factory(
            service_name,
            *self.config['args'],
            **self.config['kwargs'])

        self.pre_run(config)
        self.service.run()
        self.on_run(config)
        self.service.init()
        self.on_init(config)
        self.service.start()
        self.on_start(config)

    def inputs(self):
        # todo: maybe inform/warn when annotations are empty
        # TODO -- might want to use the full annotations, not just the "type" info.
        # this should set the _apply to "set" if none is specified
        input_schema = self.annotations.get('inputs', {}).get('schema', {})
        return input_schema

    def outputs(self):
        output_schema = self.annotations.get('outputs', {}).get('schema', {})
        return output_schema

    def update(self, inputs, interval):
        print(type(self), inputs)

        inputs_methods = self.annotations.get('inputs', {}).get('methods', {})
        outputs_methods = self.annotations.get('outputs', {}).get('methods', {})

        for key, method in inputs_methods.items():
            if 'set' in method:
                set_method = getattr(self.service, method['set'])
                set_method(inputs[key])

        self.service.step()

        outputs = {}
        for key, method in outputs_methods.items():
            if 'get' in method:
                get_method = getattr(self.service, method['get'])
                outputs[key] = get_method()

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
