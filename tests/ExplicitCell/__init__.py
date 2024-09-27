

def register_types(core):
    core.register('set_float', {
        '_inherit': 'float',
        '_apply': 'set'})

    core.register(
        'positions',
        'list[tuple[float,float,float]]')

    # TODO: provide utility to set the '_apply' method to an existing schema
    core.register(
        'domains', {
            '_type': 'map',
            '_value': {
                '_type': 'tuple',
                '_apply': 'set',
                '_0': 'positions',
                '_1': 'positions'
            }
        }
    )

    
    core.register('cell_id', 'integer')


    core.register(
        'cell_divisions',
        'dictionary[cell_id,maybe[cell_id]]')


    core.register('parent_child_ids', {
        '_type': 'list[tuple[cell_id,cell_id]]',
        '_apply': 'set')





divisions = {
    'tissue_forge_cell_id': 'child_id',
    'another_tf_id': 'other_child_id'}
