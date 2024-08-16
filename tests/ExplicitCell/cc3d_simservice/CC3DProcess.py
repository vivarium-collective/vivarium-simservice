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
from cc3d.core.PySteppables import MitosisSteppableBase
from simservice import service_function
from process_bigraph import deep_merge

cell_type_name = 'cell'
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


class InterfaceSteppable(MitosisSteppableBase):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.init_cell_volume_target = 0
        self.init_split_threshold = -1
        self.split_thresholds = {}
        # For capturing the id of a cell created during mitosis
        self._new_cell_ids: List[Tuple[int, int]] = []

    def start(self):
        """Make proxy methods out of methods on this class"""
        service_function(self.add_cell)
        service_function(self.cell_mask)
        service_function(self.cell_ids)
        service_function(self.set_target_volumes)
        service_function(self.set_initial_target_volume)
        service_function(self.set_split_thresholds)
        service_function(self.set_initial_split_threshold)
        service_function(self.divided_cell_ids)

    def step(self, mcs):
        self._new_cell_ids.clear()

        # Implement a mitosis criterion
        cells_to_divide = []
        for cell_id, split_threshold in self.split_thresholds.items():
            if split_threshold <= 0:
                continue
            cell = self.fetch_cell_by_id(cell_id)
            if cell.volume >= split_threshold:
                cells_to_divide.append(cell)
        [self.divide_cell_along_major_axis(cell) for cell in cells_to_divide]

    @property
    def type(self):
        """Simple convenience property to get the label of the cell type"""
        return getattr(self.cell_type, cell_type_name)

    def update_attributes(self):

        self._new_cell_ids.append((self.parent_cell.id, self.child_cell.id))
        self.parent_cell.targetVolume = self.init_cell_volume_target
        self.clone_parent_2_child()

    def add_cell(self, loc: List[Tuple[int, int]]):
        """Adds a cell to the simulation"""
        new_cell = self.new_cell(self.type)
        new_cell.lambdaVolume = cell_volume_lambda
        new_cell.targetVolume = self.init_cell_volume_target
        self.split_thresholds[new_cell.id] = self.init_split_threshold
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

    def set_target_volumes(self, volumes):
        for cell_id, cell_volume_target in volumes.items():
            cell = self.fetch_cell_by_id(int(cell_id))
            if cell is None:
                warnings.warn(f'Unknown cell id: {cell_id}')
            else:
                cell.targetVolume = cell_volume_target

    def set_initial_target_volume(self, _cell_volume_target: float):
        self.init_cell_volume_target = _cell_volume_target

    def set_split_thresholds(self, _split_thresholds):
        self.split_thresholds = _split_thresholds

    def set_initial_split_threshold(self, _split_threshold: float):
        self.init_split_threshold = _split_threshold

    def divided_cell_ids(self) -> List[Tuple[int, int]]:
        return self._new_cell_ids


class CC3DProcess(SimServiceProcess):
    config_schema = deep_merge(
        dct=copy.deepcopy(SimServiceProcess.config_schema),
        merge_dct={
            'dim': 'tuple[integer,integer]',
            'initial_mask': 'any',
            'init_cell_volume_target': 'float',
            'init_split_threshold': 'float'
        })

    access_methods = {
        'inputs': {
            'target_volumes': 'set_target_volumes',
            'split_thresholds': 'set_split_thresholds'
        },
        'outputs': {
            'cell_ids': 'cell_ids',
            'mask': 'cell_mask',
            'divided_cell_ids': 'divided_cell_ids'
        }
    }
    service_name = SERVICE_NAME

    def __init__(self, config=None, core=None):
        # Extract implementation-specific inputs
        self._specs = {'dim': config['dim']}
        self._initial_mask = config['initial_mask']
        self._init_cell_volume_target = config['init_cell_volume_target']
        self._init_split_threshold = config['init_split_threshold']
        super().__init__(config, core)

    def inputs(self):
        return {
            'target_volumes': 'map[float]',
            'split_thresholds': 'map[float]'
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
            },
            'divided_cell_ids': {
                '_type': 'parent_child_ids',
                '_apply': 'set'
            }
        }

    def pre_run(self, config=None):
        self.service.register_specs(specs(**self._specs))
        self.service.register_steppable(InterfaceSteppable)

    def on_start(self, config=None):
        # Handle service functions not being immediately available after startup
        while True:
            try:
                self.service.set_initial_target_volume(self._init_cell_volume_target)
                self.service.set_initial_split_threshold(self._init_split_threshold)
                break
            except AttributeError:
                pass

        cell_ids = [cid for cid in np.unique(self._initial_mask) if cid != 0]
        initial_masks = []
        for cid in cell_ids:
            xcoords, ycoords = np.where(self._initial_mask == cid)
            initial_masks.append([(int(xcoords[i]), int(ycoords[i])) for i in range(xcoords.shape[0])])
        # Handle service functions not being immediately available after startup
        for im in initial_masks:
            self.service.add_cell(im)

    def initial_state(self):
        return {
            'mask': self.service.cell_mask()
        }


def run_cc3d_alone():
    from process_bigraph import Composite, ProcessTypes

    core = ProcessTypes()

    dim = (30, 30)
    initial_mask = np.zeros(dim, dtype=int)
    initial_mask[10:15, 10:15] = 1
    init_cell_volume_target = 25.0
    init_split_threshold = 50.0

    composite = {
        'cc3d': {
            '_type': 'process',
            'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
            'config': {
                'dim': dim,
                'initial_mask': initial_mask,
                'init_cell_volume_target': init_cell_volume_target,
                'init_split_threshold': init_split_threshold,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
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
    }

    sim = Composite(
        {'state': composite},
        core=core
    )

    sim.run(2)


if __name__ == '__main__':
    run_cc3d_alone()
