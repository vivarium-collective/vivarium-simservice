"""
CompuCell3D Process
"""

import copy
import numpy as np
from typing import List, Tuple
import warnings

from vivarium_simservice.simservice_process import SimServiceProcess
from cc3d.core.simservice.PyServiceCC3D import SERVICE_NAME
from cc3d.core import PyCoreSpecs as pcs
from cc3d.core.PySteppables import SteppableBasePy
from simservice import service_function
from process_bigraph import deep_merge

cell_type_name = 'cell'
cell_volume_target = 100
cell_volume_lambda = 10


def _def_kwargs():
    return dict(dim=(30, 30),
                initial_mask=[])


def specs(dim: Tuple[int, int]):
    result = [pcs.PottsCore(dim_x=dim[0],
                            dim_y=dim[1],
                            fluctuation_amplitude=10.0),
              pcs.PixelTrackerPlugin(),
              pcs.CellTypePlugin(cell_type_name),
              pcs.VolumePlugin()]

    contact_plugin = pcs.ContactPlugin(2)
    contact_plugin.param_new(cell_type_name, 'Medium', 10)
    contact_plugin.param_new(cell_type_name, cell_type_name, 10)
    result.append(contact_plugin)
    return result


class InterfaceSteppable(SteppableBasePy):

    def start(self):
        """Make proxy methods out of methods on this class"""
        service_function(self.add_cell)
        service_function(self.cell_mask)
        service_function(self.cell_ids)
        service_function(self.set_target_volumes)

    @property
    def type(self):
        """Simple convenience property to get the label of the cell type"""
        return getattr(self.cell_type, cell_type_name)

    def add_cell(self, loc: List[Tuple[int, int]]):
        """Adds a cell to the simulation"""
        new_cell = self.new_cell(self.type)
        new_cell.lambdaVolume = cell_volume_lambda
        new_cell.targetVolume = cell_volume_target
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

    def cell_ids(self) -> List[int]:
        return [cell.id for cell in self.cell_list]

    def set_target_volumes(self, info: List[Tuple[int, float]]):
        for cell_id, cell_target_volume_ratio in info:
            cell = self.fetch_cell_by_id(cell_id)
            if cell is None:
                warnings.warn(f'Unknown cell id: {cell_id}')
            else:
                cell.targetVolume = cell_volume_target * cell_target_volume_ratio


class CC3DProcess(SimServiceProcess):
    config_schema = deep_merge(
        dct=copy.deepcopy(SimServiceProcess.config_schema),
        merge_dct={
            'dim': 'tuple[integer,integer]',
            'initial_mask': 'list[tuple[integer,integer]]',
        })

    access_methods = {
        'inputs': {
            'target_volumes': 'set_target_volumes'
        },
        'outputs': {
            'cell_ids': 'cell_ids',
            'mask': 'cell_mask',
        }
    }

    def inputs(self):
        return {
            'target_volumes': {
                '_type': 'list',
                '_apply': 'set'
            }
        }

    def outputs(self):
        return {
            'cell_ids': {
                '_type': 'list',
                '_apply': 'set'
            },
            'mask': {
                '_type': 'array',
                '_shape': (self.config['dim'][0], self.config['dim'][1]),
                '_data': 'integer',
                '_apply': 'set',
            }
        },

    def pre_run(self, config=None):
        self.service.register_specs(specs(**self._specs))
        self.service.register_steppable(InterfaceSteppable)

    def on_start(self, config=None):
        # Handle service functions not being immediately available after startup
        while True:
            try:
                self.service.add_cell(self._initial_mask)
                break
            except AttributeError:
                pass

    def initial_state(self):
        return {
            'mask': self.service.cell_mask()
        }
