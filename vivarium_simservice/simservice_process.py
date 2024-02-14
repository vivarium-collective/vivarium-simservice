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
        inputs_annotations = self.annotations.get('inputs', {})
        # this should set the _apply to "set" if none is specified
        return {
            key: {
                '_type': schema['type'],
                '_apply': 'set'}
            for key, schema in inputs_annotations.items()}

    def outputs(self):
        outputs_annotations = self.annotations.get('outputs', {})
        return {
            key: {
                '_type': schema['type'],
                '_apply': 'set'}
            for key, schema in outputs_annotations.items()}

    def update(self, inputs, interval):
        print(type(self), inputs)

        inputs_annotations = self.annotations.get('inputs', {})
        outputs_annotations = self.annotations.get('outputs', {})

        for key, schema in inputs_annotations.items():
            if 'set' in schema and key in inputs:
                set_method = getattr(self.service, schema['set'])
                set_method(inputs[key])

        self.service.step()

        outputs = {}
        for key, schema in outputs_annotations.items():
            if 'get' in schema and key in inputs:
                get_method = getattr(self.service, schema['get'])
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
