from vivarium_simservice.simservice_process import SimServiceProcess
from cc3d.core.simservice.PyServiceCC3D import SERVICE_NAME
from cc3d.core import PyCoreSpecs as pcs


def _def_specs():
    return [pcs.PottsCore()]


class CC3DProcess(SimServiceProcess):

    def __init__(self, config=None, core=None):

        if config is None:
            config = dict(service_name=SERVICE_NAME,
                          args=[],
                          kwargs={'specs': _def_specs()},
                          annotations={})
        if 'service_name' not in config:
            config['service_name'] = SERVICE_NAME
        if 'specs' not in config['kwargs']:
            config['kwargs']['specs'] = _def_specs()

        config_copy = config.copy()
        self._specs = config_copy['kwargs'].pop('specs')
        self._steppables = config_copy['kwargs'].pop('steppables') if 'steppables' in config_copy['kwargs'] else None

        super().__init__(config_copy, core)

    def pre_run(self, config=None):
        self.service.register_specs(self._specs)

        if self._steppables is not None:
            [self.service.register_steppable(steppable) for steppable in self._steppables]
