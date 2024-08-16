

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

    core.register(
        'parent_child_ids',
        'list[tuple[int,int]]'
    )
