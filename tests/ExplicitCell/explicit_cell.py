"""
Derived from the example available at https://github.com/tjsego/simservice/tree/develop/examples/ExplicitCell.
"""
from process_bigraph import Composite

from cc3d.core import PyCoreSpecs as pcs
from cc3d.core.PySteppables import SteppableBasePy

import numpy as np
from simservice import service_function
from typing import List, Tuple

from cc3d_simservice import CC3DProcess
from tf_simservice import TissueForgeProcess

from cc3d_simservice.CC3DProcess import SERVICE_NAME as cc3d_service_name
from tf_simservice.TissueForgeProcess import SERVICE_NAME as tf_service_name

cell_type_name = 'cell'


class InterfaceSteppable(SteppableBasePy):

    def start(self):
        """Make proxy methods out of methods on this class"""
        service_function(self.add_cell)
        service_function(self.cell_mask)

    @property
    def type(self):
        """Simple convenience property to get the label of the cell type"""
        return getattr(self.cell_type, cell_type_name)

    def add_cell(self, loc: List[Tuple[int, int]]):
        """Adds a cell to the simulation"""
        new_cell = self.new_cell(self.type)
        for x, y in loc:
            self.cell_field[x, y, 0] = new_cell
        return new_cell.id

    def cell_mask(self):
        """Gets the mask of the cell field"""
        result = np.zeros((self.dim.x, self.dim.y), dtype=int)
        for cell in self.cell_list:
            for ptd in self.get_cell_pixel_list(cell):
                result[ptd.pixel.x, ptd.pixel.y] = cell.id
        return result


if __name__ == '__main__':
    # Create the specs for a CC3D simulation

    dim = [30, 30, 30]
    cells = [6, 6, 6]

    specs = [pcs.PottsCore(dim_x=dim[0],
                           dim_y=dim[1],
                           fluctuation_amplitude=10.0),
             pcs.PixelTrackerPlugin(),
             pcs.CellTypePlugin(cell_type_name)]

    volume_plugin = pcs.VolumePlugin()
    volume_plugin.param_new(cell_type_name, 100, 10)
    specs.append(volume_plugin)

    contact_plugin = pcs.ContactPlugin(2)
    contact_plugin.param_new(cell_type_name, 'Medium', 10)
    contact_plugin.param_new(cell_type_name, cell_type_name, 10)
    specs.append(contact_plugin)

    # Create a CC3D process and annotate it

    # cc3d_process = CC3DProcess(config={'kwargs': {'specs': specs,
    #                                               'steppables': [InterfaceSteppable]},
    #                                    'annotations': {
    #                                        'mask': {
    #                                            'type': 'Any',
    #                                            'get': 'cell_mask'
    #                                        }
    #                                    }})
    #
    # # Create a Tissue Forge process. The underlying service is constructed ad hoc and so requires not customization here
    #
    # tf_process = TissueForgeProcess(config={'kwargs': {'dim': dim,
    #                                                    'cells': cells,
    #                                                    'per_dim': 5,
    #                                                    'num_steps': 1000}})
    #
    # # Initialize a cell using the underlying SimService interfaces
    #
    # loc = []
    # for i in range(10, 20):
    #     for j in range(10, 20):
    #         loc.append((i, j))
    # cell_id = cc3d_process.service.add_cell(loc)
    # tf_process.service.add_domain(cell_id, cc3d_process.service.cell_mask())
    # tf_process.service.equilibrate()
    #
    # update_cc3d = cc3d_process.update(state={'mask': cc3d_process.service.cell_mask()},
    #                                   interval=1)
    # print('update_cc3d')
    # print(update_cc3d)
    # update_tf = tf_process.update(state={'mask': cc3d_process.service.cell_mask()},
    #                               interval=1)
    # print('update_tf')
    # print(update_tf)

    # define mask apply function
    def set_next_mask(current, update, bindings, core):
        return update

    mask = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    mask[10:20, 10:20] = 1

    composite = {
        'state': {
            'mask': {
                '_type': 'array',
                'value': mask,
                'shape': (dim[0], dim[1]),
                'data': 'int'
            },
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
                    'annotations': {
                        'mask': {
                            '_type': 'array',
                            '_shape': (dim[0], dim[1]),
                            '_data': 'int',
                            '_apply': 'set',
                        }
                    }
                },
                'inputs': {
                    'mask': ['mask_initial']
                },
                'outputs': {
                    'mask': ['mask']
                }
            },
            'cc3d': {
                '_type': 'process',
                'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
                'config': {
                    'service_name': cc3d_service_name,
                    'args': [],
                    'kwargs': {
                        'specs': specs,
                        'steppables': [InterfaceSteppable]
                    },
                    'annotations': {
                        'mask': {
                            '_type': 'array',
                            '_shape': (dim[0], dim[1]),
                            '_data': 'int',
                            '_apply': 'set',
                        }
                        # 'mask': {
                        #     'type': 'any',
                        #     'get': 'cell_mask'
                        # }
                    }
                },
                'inputs': {
                    'mask': ['mask']
                },
                'outputs': {
                    'mask': ['mask_final']  # TODO -- where does this go?
                }
            },
        }
    }

    sim = Composite(composite)
    sim.run(1.0)
    results = sim.gather_results()
    print(results)
