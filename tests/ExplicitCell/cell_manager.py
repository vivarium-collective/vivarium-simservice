from process_bigraph import Composite, Process, Step, ProcessTypes, deep_merge


class CellManager(Step):
    config_schema = {
        'dimensions': 'tuple[integer,integer]'}


    def __init__(self, config, core=None):
        super().__init__(config, core)


    def inputs(self):
        return {
            # 'domain_mapping': 'map[domains]',
            'tissue_processes': 'map[process]',
            'divided_cells': 'parent_child_ids',
            'mask': {
                '_type': 'array',
                '_shape': self.config['dimensions'],
                '_data': 'integer'}}


    def outputs(self):
        return {
            'divisions': 'map[maybe[integer]]'}


    def update(self, state, interval):
        update = {'divisions': {}}

        if state['divided_cells']:
            for divided in state['divided_cells']:
                parent_id, child_id = divided
                update['divisions'][parent_id] = child_id
