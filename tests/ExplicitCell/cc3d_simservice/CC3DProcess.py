# todo: cleanup default vs. required arguments

import numpy as np
from typing import List, Tuple
import warnings

from vivarium_simservice.simservice_process import SimServiceProcess
from cc3d.core.simservice.PyServiceCC3D import SERVICE_NAME
from cc3d.core import PyCoreSpecs as pcs
from cc3d.core.PySteppables import SteppableBasePy
from simservice import service_function

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

    def __init__(self, config=None, core=None):

        if config is None:
            config_copy = dict(service_name=SERVICE_NAME,
                               args=[],
                               kwargs=_def_kwargs(),
                               interface={},
                               methods={})
        else:
            config_copy = config.copy()

        if 'service_name' not in config_copy:
            config_copy['service_name'] = SERVICE_NAME
        if 'kwargs' not in config_copy:
            config_copy['kwargs'] = _def_kwargs()
        if 'interface' not in config_copy:
            config_copy['interface'] = {'inputs': {},
                                        'outputs': {}}
        else:
            if 'inputs' not in config_copy['interface']:
                config_copy['interface']['inputs'] = {}
            if 'outputs' not in config_copy['interface']:
                config_copy['interface']['outputs'] = {}
        if 'methods' not in config_copy:
            config_copy['methods'] = {'inputs': {},
                                      'outputs': {}}
        else:
            if 'inputs' not in config_copy['methods']:
                config_copy['methods']['inputs'] = {}
            if 'outputs' not in config_copy['methods']:
                config_copy['methods']['outputs'] = {}

        # Apply default kwargs as necessary
        for k, v in _def_kwargs().items():
            if k not in config_copy['kwargs']:
                config_copy['kwargs'][k] = v

        # Extract implementation-specific inputs
        self._specs = {'dim': config_copy['kwargs'].pop('dim')}
        self._initial_mask = config_copy['kwargs'].pop('initial_mask')

        # Apply default interface information as necessary
        if 'target_volumes' not in config_copy['interface']['inputs']:
            config_copy['interface']['inputs']['target_volumes'] = {
                '_type': 'list',
                '_apply': 'set'
            }
        if 'mask' not in config_copy['interface']['outputs']:
            config_copy['interface']['outputs']['mask'] = {
                '_type': 'array',
                '_shape': (self._specs['dim'][0], self._specs['dim'][1]),
                '_data': 'integer',
                '_apply': 'set'
            }
        if 'cell_ids' not in config_copy['interface']['outputs']:
            config_copy['interface']['outputs']['cell_ids'] = {
                '_type': 'list',
                '_apply': 'set'
            }

        # Apply default methods information as necessary
        if 'target_volumes' not in config_copy['methods']['inputs']:
            config_copy['methods']['inputs']['target_volumes'] = {'set': 'set_target_volumes'}
        if 'mask' not in config_copy['methods']['outputs']:
            config_copy['methods']['outputs']['mask'] = {'get': 'cell_mask'}
        if 'cell_ids' not in config_copy['methods']['outputs']:
            config_copy['methods']['outputs']['cell_ids'] = {'get': 'cell_ids'}

        super().__init__(config_copy, core)

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
