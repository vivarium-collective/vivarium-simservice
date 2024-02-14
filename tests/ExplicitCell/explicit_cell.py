"""
Derived from the example available at https://github.com/tjsego/simservice/tree/develop/examples/ExplicitCell.
"""
from process_bigraph import Composite, ProcessTypes

from cc3d.core import PyCoreSpecs as pcs
from cc3d.core.PySteppables import SteppableBasePy

import numpy as np
from simservice import service_function
from typing import List, Tuple

from cc3d_simservice import CC3DProcess
from tf_simservice import TissueForgeProcess

from cc3d_simservice.CC3DProcess import SERVICE_NAME as cc3d_service_name
from tf_simservice.TissueForgeProcess import SERVICE_NAME as tf_service_name
from vivarium_simservice.emitter import get_emitter_schema

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
    core = ProcessTypes()


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
    # define mask apply function
    def set_next_mask(current, update, bindings, core):
        return update

    mask = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    mask[10:20, 10:20] = 1

    emitter_schema = get_emitter_schema(target_path=['mask'])
    composite = {
            'mask': {
                '_type': 'array',
                'value': mask,
                'shape': (dim[0], dim[1]),
                'data': 'int'
            },
            # **emitter_schema,
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
                        'inputs': {
                            'mask': {
                                'type': 'array',
                                # TODO -- should we pass additional info like this?
                                # '_shape': (dim[0], dim[1]),
                                # '_data': 'int',
                                '_apply': 'set',
                            }
                        }
                    }
                },
                'inputs': {
                    'mask': ['mask']
                },
                # 'outputs': {
                #     'mask': ['mask_final']
                # }
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
                        'outputs': {
                            'mask': {
                                'type': 'array',
                                # TODO -- should we pass additional info like this?
                                # '_shape': (dim[0], dim[1]),
                                # '_data': 'int',
                                # '_apply': 'set',
                            }
                        }
                    }
                },
                # 'inputs': {
                #     'mask': ['mask_initial']
                # },
                'outputs': {
                    'mask': ['mask']  # TODO -- where does this go?
                }
            },
    }

    sim = Composite({'state': composite}, core=core)
    sim.run(2)
    results = sim.gather_results()
    print(results)
