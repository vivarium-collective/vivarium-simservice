"""
Derived from the example available at https://github.com/tjsego/simservice/tree/develop/examples/ExplicitCell.

TODO
- get TissueForge output as input for ccc3
- create a step (manage_cells) to manage 1 TF process for every cell in CC3D. remove cells that have died and add new ones

# example cell manager spec
cell_manager = {
    'address': 'local:cell-manager',
    'config': {
        'processes': ['simservice:tissue-forge'],
        'process_config': {}
    },
    'inputs': {
        'cell_ids': ['cell_ids_store'],
    },
    'outputs': {
        'environment': ['tissue_forge_processes']
    }
}
"""
from process_bigraph import Composite, ProcessTypes
import numpy as np

# these imports are done to import to registry
from cc3d_simservice.CC3DProcess import SERVICE_NAME as cc3d_service_name
from tf_simservice.TissueForgeProcess import SERVICE_NAME as tf_service_name
from vivarium_simservice.emitter import get_emitter_schema
from tests.ExplicitCell import register_types

cell_type_name = 'cell'



def test_one_cell_one_direction(core):
    # Create the specs for a CC3D simulation
    dim = (30, 30, 30)
    cells = (6, 6, 6)

    # make an initial mask array
    initial_mask_array = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    initial_mask_array[10:20, 10:20] = 1

    # initial cell target volume
    init_cell_volume_target = 100.0

    # number of fluid particles is per_dim ** 2 * no. cell sites
    # per_dim = 5
    # no. cell sites = 100
    # result was 400
    # (5 * 10 - 2) ** 2

    # list of initial cell ids
    initial_cell_ids = [1]  # make this work for multiple cells

    # configure compucell3D
    compucell_config_dict = {
        'cc3d': {
            '_type': 'process',
            'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
            'config': {
                'dim': (dim[0], dim[1]),
                'initial_mask': initial_mask_array,
                'init_cell_volume_target': init_cell_volume_target,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
                # 'simservice_config': {}
            },
            'inputs': {
                'target_volumes': ['target_volumes_store']
            },
            'outputs': {
                'cell_ids': ['cell_ids_store'],
                'mask': ['mask_store']
            }
        },
    }

    # configure tissue forge
    tissue_forge_config_dict = {
        f'tissue-forge-{cell_id}': {
            '_type': 'process',
            'address': 'local:!tf_simservice.TissueForgeProcess.TissueForgeProcess',
            'config': {
                'cell_id': cell_id,
                'initial_mask': initial_mask_array,
                'growth_rate': 0,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
                'simservice_config': {
                    'dim': dim,
                    'cells': cells,
                    'per_dim': 5,
                    'num_steps': 1000,
                }
            },
            'inputs': {
                'mask': ['mask_store']
            },
            'outputs': {
                'domains': ['domains_store']
                # TODO map output to target_volumes
            }
        } for cell_id in initial_cell_ids
    }

    # configure the ram emitter
    ram_emitter_config = {
        'ram-emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'emit': {
                    'mask': {
                        '_type': 'array',
                        '_shape': (dim[0], dim[1]),
                        '_data': 'integer',
                    },
                    'domains': {
                        '_type': 'any',
                    }
                }
            },
            'inputs': {
                'mask': ['mask_store'],
                'domains': ['domains_store']
            }
        },
    }

    # combine all the specs
    composite = {
        **tissue_forge_config_dict,
        **compucell_config_dict,
        **ram_emitter_config
    }

    # initialize the composite
    sim = Composite(
        {'state': composite},
        core=core
    )

    # run it
    sim.run(5)
    results = sim.gather_results()

    import ipdb; ipdb.set_trace()

    print(results)

    
def test_one_cell_two_directions(core):
    # Create the specs for a CC3D simulation
    dim = (30, 30, 30)
    cells = (6, 6, 6)

    # make an initial mask array
    initial_mask_array = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    initial_mask_array[10:20, 10:20] = 1

    init_cell_volume_target = 100.0

    # list of initial cell ids
    initial_cell_ids = [1]  # make this work for multiple cells

    # configure compucell3D
    compucell_config_dict = {
        'cc3d': {
            '_type': 'process',
            'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
            'config': {
                'dim': (dim[0], dim[1]),
                'initial_mask': initial_mask_array,
                'init_cell_volume_target': init_cell_volume_target,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
                # 'simservice_config': {}
            },
            'inputs': {
                'target_volumes': ['target_volumes_store']
            },
            'outputs': {
                'cell_ids': ['cell_ids_store'],
                'mask': ['mask_store']
            }
        },
    }

    # configure tissue forge
    tissue_forge_config_dict = {
        f'tissue-forge-{cell_id}': {
            '_type': 'process',
            'address': 'local:!tf_simservice.TissueForgeProcess.TissueForgeProcess',
            'config': {
                'cell_id': cell_id,
                'initial_mask': initial_mask_array,
                'dim': dim,
                'cells': cells,
                'per_dim': 5,
                'num_steps': 1000,
                'growth_rate': 0,   # number of particles added every simulation step
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
                'simservice_config': {
                    'dim': dim,
                    'cells': cells,
                }
            },
            'inputs': {
                'mask': ['mask_store']
            },
            'outputs': {
                'domains': ['domains_store']
                # TODO map output to target_volumes
            }
        } for cell_id in initial_cell_ids
    }

    volume_config = {
        'volume_adapter': {
            '_type': 'step',
            'address': 'local:!tests.ExplicitCell.adapters.volume_from_particles.VolumeFromParticles',
            'config': {
                # TODO: calculate this from the initial fluid particles
                'optimal_density': 0.25},
            'inputs': {
                'domains': ['domains_store']},
            'outputs': {
                'volumes': ['target_volumes_store']}}}

    # configure the ram emitter
    ram_emitter_config = {
        'ram-emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'emit': {
                    'mask': {
                        '_type': 'array',
                        '_shape': (dim[0], dim[1]),
                        '_data': 'integer',
                    },
                    'domains': {
                        '_type': 'domains',
                    },
                    'volumes': 'map[float]',
                }
            },
            'inputs': {
                'mask': ['mask_store'],
                'domains': ['domains_store'],
                'volumes': ['target_volumes_store'],
            }
        },
        'domains_store': {'1': []}  # TODO (Ryan) -- this seems to want an existing value
    }

    # combine all the specs
    composite = {
        **tissue_forge_config_dict,
        **compucell_config_dict,
        **volume_config,
        **ram_emitter_config
    }

    # initialize the composite
    sim = Composite(
        {'state': composite},
        core=core
    )

    # run it
    sim.run(5)
    results = sim.gather_results()

    import ipdb; ipdb.set_trace()

    print(results)

    


if __name__ == '__main__':
    core = ProcessTypes()
    register_types(core)

    # test_one_cell_one_direction(core)
    test_one_cell_two_directions(core)
