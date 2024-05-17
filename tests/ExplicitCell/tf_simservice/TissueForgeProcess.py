from vivarium_simservice.simservice_process import SimServiceProcess
from .TissueForgeSimServiceFactory import SERVICE_NAME


def _def_kwargs():
    return dict(dim=[10.0, 10.0, 10.0],
                cells=[3, 3, 3])


class TissueForgeProcess(SimServiceProcess):

    def __init__(self, config=None, core=None):

        if config is None:
            config = dict(service_name=SERVICE_NAME,
                          args=[],
                          kwargs=_def_kwargs(),
                          annotations={})
        if 'service_name' not in config:
            config['service_name'] = SERVICE_NAME
        if 'args' not in config:
            config['args'] = []
        if 'kwargs' not in config:
            config['kwargs'] = _def_kwargs()
        for k, v in _def_kwargs().items():
            if k not in config['kwargs']:
                config['kwargs'][k] = v
        # if 'domain' not in config['annotations'].keys():
        #     config['annotations']['domain'] = {'type': 'any',
        #                                        'get': 'get_domains'}
        if not config['interface'].get('inputs'):
            def set_next_mask(current, update, bindings, core):
                return update

            config['interface']['inputs'] = {
                'mask': {
                    '_type': 'array',
                    '_data': 'integer',
                    '_apply': set_next_mask
                }
            }

        super().__init__(config, core)

    def inputs(self):
        # TODO -- remove this process and get inputs from the config
        dim = self.config['kwargs']['dim']
        return {
            'mask': {
                '_type': 'array',
                '_shape': (dim[0], dim[1]),
                '_data': 'integer',
                '_apply': 'set'
            }
        }

    # def outputs(self):
    #     return {
    #         'vector_positions': {
    #             # '_type': 'tuple'  # TODO
    #         },
    #         # 'particle_ids': {},
    #     }
