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
            'growth_rate': 'integer'
        })
    config_schema.update()

    # access methods for the ports
    access_methods = {
        'inputs': {
            'mask': 'set_next_mask',
            'growth_rates': 'set_growth_rates'
        },
        'outputs': {
            'domains': 'get_domains'
        }
    }
    service_name = SERVICE_NAME

    def on_start(self, config=None):
        # TODO -- get the cell_id to match the mask
        self.service.add_domain(
            self.config['cell_id'],
            self.config['initial_mask'],
            self.config['growth_rate']
        )

    def inputs(self):
        return {
            'mask': {
                '_type': 'array',
                '_shape': (self.config['dim'][0], self.config['dim'][1]),
                '_data': 'integer',
                '_apply': 'set',
            },
            'growth_rates': {
                '_type': 'map',
                '_value': {
                    '_type': 'int'
                }
            }
        }

    def outputs(self):
        return {
            'domains': 'domains'
        }

    def _handle_split_prototype(self, mask, parent_id: int, child_id: int, growth_rate: int):
        # Prototyping the procedure for splitting a cell and taking the child to a new service.
        # Not really intended for deployment; just outlining the procedures to spawn a new
        # service with a newly created cell while taking the newly created cell from its
        # parent cell in this service.

        from simservice.service_factory import process_factory

        child_service = process_factory(self.service_name, *[], **self.simservice_config)
        child_service.run()
        child_service.init()
        child_service.start()

        child_domain = self.service.divide_cell_and_take(mask, parent_id, child_id)
        child_service.add_set_domain(child_id, mask, child_domain, growth_rate)

        return child_service


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
