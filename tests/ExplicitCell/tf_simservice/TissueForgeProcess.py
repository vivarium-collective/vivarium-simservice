"""
TissueForge Process
"""

import copy
from process_bigraph import Composite, ProcessTypes, deep_merge
from vivarium_simservice.simservice_process import SimServiceProcess
from tests.ExplicitCell.tf_simservice.TissueForgeSimServiceFactory import SERVICE_NAME


def _def_kwargs():
    return dict(dim=[10.0, 10.0, 10.0],
                cells=[3, 3, 3])


def _missing_inputs_exc():
    raise ValueError('Missing required specification for inputs that cannot be deduced.')


class TissueForgeProcess(SimServiceProcess):

    # TODO -- inherit config_schema from base class
    config_schema = deep_merge(
        dct=copy.deepcopy(SimServiceProcess.config_schema),
        merge_dct={
            'dim': 'tuple[float,float,float]',
            'cells': 'tuple[integer,integer,integer]',
            'per_dim': 'integer',
            'num_steps': 'integer',
            'cell_id': 'integer',
            'initial_mask': 'array[integer]',
        })
    config_schema.update()

    # access methods for the ports
    access_methods = {
        'inputs': {
            'mask': 'set_next_mask'
        },
        'outputs': {
            'domains': 'get_domains'
        }
    }
    service_name = SERVICE_NAME

    def on_start(self, config=None):
        # TODO -- get the cell_id to match the mask
        self.service.add_domain(self.config['cell_id'], self.config['initial_mask'])

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
            'domains': 'domains'
            # 'domains': {
            #     '_type': 'any',   # TODO -- make this a real type
            # }
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
                'num_steps': 1000,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                }
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
