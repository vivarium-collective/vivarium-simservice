from process_bigraph import Process
from simservice.service_factory import process_factory


class SimServiceProcess(Process):
    config_schema = {
        'service_name': 'string',
        'args': 'list[any]',
        'kwargs': 'tree[any]'}

    def __init__(self, config=None):
        super().__init__(config)

        self.annotations = dict()
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

    def schema(self):
        return {
            key: {
                '_type': schema['type'],
                '_apply': 'set'}
            for key, schema in self.annotations.items()}

    def update(self, state, interval):
        for key, schema in self.annotations.items():
            if 'set' in schema and key in state:
                set_method = getattr(self.service, schema['set'])
                set_method(state[key])

        self.service.step()

        update = {}
        for key, schema in self.annotations.items():
            if 'get' in schema and key in state:
                get_method = getattr(self.service, schema['get'])
                update[key] = get_method(state[key])

        return update

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
