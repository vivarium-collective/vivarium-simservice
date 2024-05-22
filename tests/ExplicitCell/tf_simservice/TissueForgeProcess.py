# todo: cleanup default vs. required arguments

from vivarium_simservice.simservice_process import SimServiceProcess
from .TissueForgeSimServiceFactory import SERVICE_NAME


def _def_kwargs():
    return dict(dim=[10.0, 10.0, 10.0],
                cells=[3, 3, 3])


def _missing_inputs_exc():
    raise ValueError('Missing required specification for inputs that cannot be deduced.')


class TissueForgeProcess(SimServiceProcess):

    def __init__(self, config=None, core=None):

        if config is None:
            config_copy = dict(service_name=SERVICE_NAME,
                               args=[],
                               kwargs=_def_kwargs(),
                               interface={},
                               methods={})
        else:
            config_copy = config.copy()

        if 'service_name' not in config_copy:
            config_copy['service_name'] = SERVICE_NAME
        if 'args' not in config_copy:
            config_copy['args'] = []
        if 'kwargs' not in config_copy:
            config_copy['kwargs'] = _def_kwargs()
        if 'interface' not in config_copy:
            config_copy['interface'] = {'inputs': {},
                                        'outputs': {}}
        else:
            if 'inputs' not in config_copy['interface']:
                config_copy['interface']['inputs'] = {}
            if 'outputs' not in config_copy['interface']:
                config_copy['interface']['outputs'] = {}
        if 'methods' not in config_copy:
            config_copy['methods'] = {'inputs': {},
                                      'outputs': {}}
        else:
            if 'inputs' not in config_copy['methods']:
                config_copy['methods']['inputs'] = {}
            if 'outputs' not in config_copy['methods']:
                config_copy['methods']['outputs'] = {}

        # Apply default kwargs as necessary
        for k, v in _def_kwargs().items():
            if k not in config_copy['kwargs']:
                config_copy['kwargs'][k] = v

        # Check for required interface input information that cannot be deduced
        if 'mask' not in config_copy['interface']['inputs']:
            _missing_inputs_exc()

        # Apply default interface information as necessary
        if 'domains' not in config_copy['interface']['outputs']:
            config_copy['interface']['outputs']['domains'] = {'_type': 'tree[any]'}
        # Apply default methods information as necessary
        if 'mask' not in config_copy['methods']['inputs']:
            config_copy['methods']['inputs']['mask'] = {'set': 'set_next_mask'}
        if 'domains' not in config_copy['methods']['outputs']:
            config_copy['methods']['outputs']['domains'] = {'get': 'get_domains'}

        super().__init__(config_copy, core)
