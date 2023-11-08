from process_bigraph import Process
from simservice.service_factory import process_factory


class SimserviceProcess(Process):
    config_schema = {
        'service_name': 'string',
        'args': 'list[string]',
        'kwargs': 'tree[any]'}


    def __init__(self, config=None):
        super().__init__(config)

        service_name = self.config['service_name']
        self.service = process_factory(
            service_name,
            *self.config['args'],
            **self.config['kwargs'])

        self.service.run()
        self.service.init()
        self.service.start()

        try:
            self.annotations = self.service.annotations()
        except:
            raise Exception(f'simservice requires an annotations() method to describe the schema')


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


