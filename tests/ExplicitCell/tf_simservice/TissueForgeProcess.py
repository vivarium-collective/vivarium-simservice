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
                          kwargs=_def_kwargs(),
                          annotations={})
        if 'service_name' not in config.keys():
            config['service_name'] = SERVICE_NAME
        if 'args' not in config.keys():
            config['args'] = []
        if 'kwargs' not in config.keys():
            config['kwargs'] = _def_kwargs()
        if 'annotations' not in config.keys():
            config['annotations'] = {}
        for k, v in _def_kwargs().items():
            if k not in config['kwargs'].keys():
                config['kwargs'][k] = v
        if 'domain' not in config['annotations'].keys():
            config['annotations']['domain'] = {'type': 'any',
                                               'get': 'get_domains'}
        if 'mask' not in config['annotations'].keys():
            def set_next_mask(current, update, bindings, core):
                return update

            config['annotations']['mask'] = {
                '_type': 'array',
                '_apply': set_next_mask  # TODO -- what is this???
            }

        super().__init__(config)
