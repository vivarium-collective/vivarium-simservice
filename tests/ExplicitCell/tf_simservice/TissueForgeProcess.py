# todo: cleanup default vs. required arguments

from process_bigraph import Composite, ProcessTypes
from vivarium_simservice.simservice_process import SimServiceProcess
from tests.ExplicitCell.tf_simservice.TissueForgeSimServiceFactory import SERVICE_NAME


def _def_kwargs():
    return dict(dim=[10.0, 10.0, 10.0],
                cells=[3, 3, 3])


def _missing_inputs_exc():
    raise ValueError('Missing required specification for inputs that cannot be deduced.')


class TissueForgeProcess(SimServiceProcess):
    config_schema = {
        'dim': 'tuple[float,float,float]',
        'cells': 'tuple[integer,integer,integer]',
        'per_dim': 'integer',
        'num_steps': 'integer',
    }

    # TODO -- maybe by default, assume inputs have a 'set_*' method and outputs have a 'get_*' method
    # if otherwise, it has to be specified in the access_methods
    access_methods = {
        'inputs': {
            'mask': 'set_next_mask'
        },
        'outputs': {
            'domains': 'get_domains'
        }
    }
    service_name = SERVICE_NAME

    def __init__(self, config=None, core=None):
        super().__init__(config, core)

        # if config is None:
        #     config_copy = dict(service_name=SERVICE_NAME,
        #                        args=[],
        #                        kwargs=_def_kwargs(),
        #                        interface={},
        #                        methods={})
        # else:
        #     config_copy = config.copy()
        #
        # if 'service_name' not in config_copy:
        #     config_copy['service_name'] = SERVICE_NAME
        # if 'args' not in config_copy:
        #     config_copy['args'] = []
        # if 'kwargs' not in config_copy:
        #     config_copy['kwargs'] = _def_kwargs()
        # if 'interface' not in config_copy:
        #     config_copy['interface'] = {'inputs': {},
        #                                 'outputs': {}}
        # else:
        #     if 'inputs' not in config_copy['interface']:
        #         config_copy['interface']['inputs'] = {}
        #     if 'outputs' not in config_copy['interface']:
        #         config_copy['interface']['outputs'] = {}
        # if 'methods' not in config_copy:
        #     config_copy['methods'] = {'inputs': {},
        #                               'outputs': {}}
        # else:
        #     if 'inputs' not in config_copy['methods']:
        #         config_copy['methods']['inputs'] = {}
        #     if 'outputs' not in config_copy['methods']:
        #         config_copy['methods']['outputs'] = {}
        #
        # # Apply default kwargs as necessary
        # for k, v in _def_kwargs().items():
        #     if k not in config_copy['kwargs']:
        #         config_copy['kwargs'][k] = v
        #
        # # Check for required interface input information that cannot be deduced
        # if 'mask' not in config_copy['interface']['inputs']:
        #     _missing_inputs_exc()
        #

        # # Apply default interface information as necessary
        # if 'domains' not in config_copy['interface']['outputs']:
        #     config_copy['interface']['outputs']['domains'] = {'_type': 'tree[any]'}
        # # Apply default methods information as necessary
        # if 'mask' not in config_copy['methods']['inputs']:
        #     config_copy['methods']['inputs']['mask'] = {'set': 'set_next_mask'}
        # if 'domains' not in config_copy['methods']['outputs']:
        #     config_copy['methods']['outputs']['domains'] = {'get': 'get_domains'}

    def inputs(self):
        return {
            'mask': {
                '_type': 'array',
                '_shape': (self.config['dim'][0], self.config['dim'][1]),
                '_data': 'integer',
                '_apply': 'set',
            }
        }

    def outputs(self):
        return {
            'domains': {
                '_type': 'any', #'dict[integer,list]'   # TODO make this type
            }
        }


def run_tissue_forge_alone():
    core = ProcessTypes()

    state = {
        'tissueforge': {
            '_type': 'process',
            'address': 'local:!tf_simservice.TissueForgeProcess.TissueForgeProcess',
            'config': {
                'dim': [10.0, 10.0, 10.0],
                'cells': [3, 3, 3],
                'per_dim': 5,
                'num_steps': 1000
            },
        }
    }

    # make the composite sim
    sim = Composite(config={'state': state}, core=core)

    # run the sim
    sim.run(10)

    # get the results
    results = sim.gather_results()

    print(results)


if __name__ == '__main__':
    run_tissue_forge_alone()
