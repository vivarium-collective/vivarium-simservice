from vivarium_simservice.simservice_process import SimServiceProcess
from .TissueForgeSimServiceFactory import SERVICE_NAME


def _def_kwargs():
    return dict(dim=[10.0, 10.0, 10.0],
                cells=[3, 3, 3])


class TissueForgeProcess(SimServiceProcess):

    def __init__(self, config=None):

        if config is None:
            config = dict(service_name=SERVICE_NAME,
                          args=[],
                          kwargs=_def_kwargs())
        if 'service_name' not in config.keys():
            config['service_name'] = SERVICE_NAME
        if 'args' not in config.keys():
            config['args'] = []
        if 'kwargs' not in config.keys():
            config['kwargs'] = _def_kwargs()
        for k, v in _def_kwargs().items():
            if k not in config['kwargs'].keys():
                config['kwargs'][k] = v

        super().__init__(config)

        self.annotations['domains'] = {'type': 'Any',
                                       'get': 'get_domains'}
        self.annotations['mask'] = {'type': 'Any',
                                    'set': 'set_next_mask'}
