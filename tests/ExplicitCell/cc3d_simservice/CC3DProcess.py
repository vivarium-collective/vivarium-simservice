from vivarium_simservice.simservice_process import SimServiceProcess
from cc3d.core.simservice.PyServiceCC3D import SERVICE_NAME
from cc3d.core import PyCoreSpecs as pcs


def _def_specs():
    return [pcs.PottsCore()]


class CC3DProcess(SimServiceProcess):

    def __init__(self, config=None):

        if config is None:
            config = dict(service_name=SERVICE_NAME,
                          args=[],
                          kwargs={'specs': _def_specs()})
        if 'service_name' not in config.keys():
            config['service_name'] = SERVICE_NAME
        if 'args' not in config.keys():
            config['args'] = []
        if 'kwargs' not in config.keys():
            config['kwargs'] = dict()
        if 'specs' not in config['kwargs'].keys():
            config['kwargs']['specs'] = _def_specs()

        config_copy = config.copy()
        self._specs = config_copy['kwargs'].pop('specs')
        self._steppables = config_copy['kwargs'].pop('steppables') if 'steppables' in config_copy['kwargs'] else None

        super().__init__(config_copy)

    def pre_run(self, config=None):
        self.service.register_specs(self._specs)

        if self._steppables is not None:
            [self.service.register_steppable(steppable) for steppable in self._steppables]
