"""
Derived from the example available at https://github.com/tjsego/simservice/tree/develop/examples/ExplicitCell.
"""

from cc3d.core import PyCoreSpecs as pcs
from cc3d.core.PySteppables import SteppableBasePy

import numpy as np
from simservice import service_function
from typing import List, Tuple

from cc3d_simservice import CC3DProcess
from tf_simservice import TissueForgeProcess

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

    cc3d_process = CC3DProcess(config={'kwargs': {'specs': specs,
                                                  'steppables': [InterfaceSteppable]}})
    cc3d_process.annotations['mask'] = {'type': 'Any',
                                        'get': 'cell_mask'}

    # Create a Tissue Forge process. The underlying service is constructed ad hoc and so requires not customization here

    tf_process = TissueForgeProcess(config={'kwargs': {'dim': dim,
                                                       'cells': cells,
                                                       'per_dim': 5,
                                                       'num_steps': 1000}})

    # Initialize a cell using the underlying SimService interfaces

    loc = []
    for i in range(10, 20):
        for j in range(10, 20):
            loc.append((i, j))
    cell_id = cc3d_process.service.add_cell(loc)
    tf_process.service.add_domain(cell_id, cc3d_process.service.cell_mask())
    tf_process.service.equilibrate()
