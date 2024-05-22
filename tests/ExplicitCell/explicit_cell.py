"""
Derived from the example available at https://github.com/tjsego/simservice/tree/develop/examples/ExplicitCell.
"""
from process_bigraph import Composite, ProcessTypes

from cc3d_simservice.CC3DProcess import SERVICE_NAME as cc3d_service_name
from tf_simservice.TissueForgeProcess import SERVICE_NAME as tf_service_name
from vivarium_simservice.emitter import get_emitter_schema

cell_type_name = 'cell'


if __name__ == '__main__':
    core = ProcessTypes()

    # Create the specs for a CC3D simulation
    dim = [30, 30, 30]
    cells = [6, 6, 6]

    initial_mask = []
    for i in range(10):
        for j in range(10):
            initial_mask.append((i+10, j+10))

    # mask = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    # mask[10:20, 10:20] = 1

    composite = {
        # 'mask_store': mask,
        'tissue-forge': {
            '_type': 'process',
            'address': 'local:!tf_simservice.TissueForgeProcess.TissueForgeProcess',
            'config': {
                'service_name': tf_service_name,
                'args': [],
                'kwargs': {
                    'dim': dim,
                    'cells': cells,
                    'per_dim': 5,
                    'num_steps': 1000
                },
                'interface': {
                    'inputs': {
                        'mask': {
                            '_type': 'array',
                            '_shape': (dim[0], dim[1]),
                            '_data': 'integer',
                            '_apply': 'set',
                        }
                    },
                    'outputs': {
                        'domains': {
                            '_type': 'tree[any]'
                        }
                    }
                },
                'methods': {
                    'inputs': {
                        'mask': {
                            'set': 'set_next_mask'
                        }
                    },
                    'outputs': {
                        'domains': {
                            'get': 'get_domains'
                        }
                    }
                }
            },
            'inputs': {
                'mask': ['mask_store']
            },
            'outputs': {
                'domains': ['domains_store']
            }
        },
        'cc3d': {
            '_type': 'process',
            'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
            'config': {
                'service_name': cc3d_service_name,
                'args': [],
                'kwargs': {
                    'dim': (dim[0], dim[1]),
                    'initial_mask': initial_mask
                },
                'interface': {
                    'inputs': {
                        'target_volumes': {
                            '_type': 'list',
                            '_apply': 'set'
                        }
                    },
                    'outputs': {
                        'cell_ids': {
                            '_type': 'list',
                            '_apply': 'set'
                        },
                        'mask': {
                            '_type': 'array',
                            '_shape': (dim[0], dim[1]),
                            '_data': 'integer',
                            '_apply': 'set',
                        }
                    },
                },
                'methods': {
                    'inputs': {
                        'target_volumes': {
                            'set': 'set_target_volumes'
                        }
                    },
                    'outputs': {
                        'cell_ids': {
                            'get': 'cell_ids'
                        },
                        'mask': {
                            'get': 'cell_mask'
                        }
                    }
                }
            },
            'inputs': {
                'target_volumes': ['target_volumes_store']
            },
            'outputs': {
                'cell_ids': ['cell_ids_store'],
                'mask': ['mask_store']
            }
        },
        'ram-emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'emit': {
                    'data': {
                            '_type': 'array',
                            '_shape': (dim[0], dim[1]),
                            '_data': 'integer',
                        }
                }
            },
            'inputs': {
                'data': ['mask_store']
            }
        },
    }

    sim = Composite(
        {'state': composite},
        core=core
    )

    import ipdb; ipdb.set_trace()

    sim.run(2)
    results = sim.gather_results()
    print(results)
