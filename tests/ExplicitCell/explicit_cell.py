"""
Derived from the example available at https://github.com/tjsego/simservice/tree/develop/examples/ExplicitCell.

TODO
- get TissueForge output as input for ccc3
- create a step (manage_cells) to manage 1 TF process for every cell in CC3D. remove cells that have died and add new ones

# example cell manager spec
cell_manager = {
    'address': 'local:cell-manager',
    'config': {
        'processes': ['simservice:tissue-forge'],
        'process_config': {}
    },
    'inputs': {
        'cell_ids': ['cell_ids_store'],
    },
    'outputs': {
        'environment': ['tissue_forge_processes']
    }
}
"""
import os
from process_bigraph import Composite, ProcessTypes
import imageio.v2 as imageio
import io
import base64
from IPython.display import HTML, display
import numpy as np
from matplotlib import animation
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt
from matplotlib.collections import PathCollection
from matplotlib.image import AxesImage
from matplotlib.axis import Axis
from typing import Any, Dict, List, Optional, Tuple, Union

# these imports are done to import to registry
from cc3d_simservice.CC3DProcess import SERVICE_NAME as cc3d_service_name  # DO NOT REMOVE
from tf_simservice.TissueForgeProcess import SERVICE_NAME as tf_service_name  # DO NOT REMOVE
from tests.ExplicitCell import register_types

ColorData = Union[str, Tuple[float, float, float]]
ParticleData = List[Tuple[float, float, float]]

DEF_PARTICLE_COLOR_CYT = 'red'
"""Default color for cytosolic particles"""
DEF_PARTICLE_COLOR_MEM = 'blue'
"""Default color for membrane particles"""


def plot_cell_field(mask: np.ndarray,
                    im: AxesImage = None,
                    fig_ax: Tuple[plt.Figure, Axis] = None,
                    fig_kwargs: Dict[str, Any] = None,
                    plot_kwargs: Dict[str, Any] = None) -> Tuple[Optional[plt.Figure], Optional[Axis], AxesImage]:
    """Plot a cell field"""

    viz_tf = lambda x: np.flipud(np.transpose(x))
    if im is not None:
        im.set_array(viz_tf(mask))
        return None, None, im

    if fig_ax is None:
        if fig_kwargs is None:
            fig_kwargs = {}
        fig, ax = plt.subplots(1, 1, **fig_kwargs)
    else:
        fig, ax = fig_ax

    if plot_kwargs is None:
        plot_kwargs = {}
    im: AxesImage = ax.imshow(viz_tf(mask), **plot_kwargs)

    return fig, ax, im


def plot_cell_particles(
        particle_data: Union[Tuple[ParticleData, ParticleData], List[Tuple[ParticleData, ParticleData]]],
        sca: PathCollection = None,
        fig_ax: Tuple[plt.Figure, Axis] = None,
        colors: Union[Tuple[ColorData, ColorData], List[Tuple[ColorData, ColorData]]] = None,
        fig_kwargs: Dict[str, Any] = None,
        plot_kwargs: Dict[str, Any] = None) -> Tuple[Optional[plt.Figure], Optional[Axis], PathCollection]:
    """Plot the particles comprising one or more cells"""

    _particle_data = [particle_data] if isinstance(particle_data, tuple) else particle_data

    if colors is None:
        _colors = [(DEF_PARTICLE_COLOR_MEM, DEF_PARTICLE_COLOR_CYT)]
    else:
        _colors = [colors] if isinstance(colors, tuple) else colors

    colors_rgb = []
    for c in _colors:
        c0 = mcolors.to_rgb(c[0]) if isinstance(c[0], str) else c[0]
        c1 = mcolors.to_rgb(c[1]) if isinstance(c[1], str) else c[1]
        colors_rgb.append((c0, c1))

    num_particles = sum([len(d[0]) + len(d[1]) for d in _particle_data])
    particle_data_arr = np.ndarray((num_particles, 2), dtype=float)
    colors_arr = np.ndarray((num_particles, 3), dtype=float)
    idx = 0
    for i, cell_data in enumerate(_particle_data):
        colors_i = colors_rgb[i % len(colors_rgb)]
        for j, cd in enumerate(cell_data):
            num_particles_j = len(cd)
            particle_data_arr[idx:idx + num_particles_j, :] = np.asarray(cd, dtype=float)[:, :2]
            colors_arr[idx: idx + num_particles_j, :] = np.asarray([colors_i[j]] * num_particles_j, dtype=float)
            idx += num_particles_j

    if sca is not None:
        sca.set_offsets(particle_data_arr)
        sca.set_array(colors_arr)
        return None, None, sca

    if fig_ax is None:
        if fig_kwargs is None:
            fig_kwargs = {}
        fig, ax = plt.subplots(1, 1, **fig_kwargs)
    else:
        fig, ax = fig_ax

    if plot_kwargs is None:
        plot_kwargs = {}
    sca = ax.scatter(particle_data_arr[:, 0], particle_data_arr[:, 1], c=colors_arr, **plot_kwargs)

    return fig, ax, sca


def adjust_particles(particles, dx, dy, dz=0):
    """Adjust particle positions by a given delta x (dx) and delta y (dy)."""
    adjusted_particles = []
    for particle_set in particles[0]:
        adjusted_set = [(x + dx, y + dy, z + dz) for (x, y, z) in particle_set]
        adjusted_particles.append(adjusted_set)
    return [adjusted_particles]


def generate_frames_and_save_gif(results, output_dir='frames', gif_filename='animation.gif'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    images = []
    for i in range(len(results) - 1):  # Stops before the last element
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        mask = results[i]['mask']
        adjusted_mask = np.rot90(np.flipud(mask), k=2)
        particles = list(results[i + 1]['domains'].values())
        adjusted_particles = adjust_particles(particles, dx=-0.5, dy=-0.5)

        # Plot cell field
        _, _, im_field = plot_cell_field(adjusted_mask, fig_ax=(fig, ax))

        # Plot particles over the cell field
        _, _, im_particles = plot_cell_particles(adjusted_particles, fig_ax=(fig, ax))

        # Save the current figure to a temporary buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        images.append(imageio.imread(buf))
        buf.close()
        plt.close(fig)

        # Create and save the GIF with loop=0 for infinite loop
    imageio.mimsave(gif_filename, images, duration=0.5, loop=0)

    # Optionally display the GIF in a Jupyter notebook
    with open(gif_filename, 'rb') as file:
        data = file.read()
        data_url = 'data:image/gif;base64,' + base64.b64encode(data).decode()
    display(HTML(f'<img src="{data_url}" alt="Simulation Results Animation" style="max-width:100%;"/>'))

    print(f'GIF saved as {gif_filename}')


class ResultsAnimator:
    """Animate results"""

    def __init__(self, results):
        self.results = results
        self.fig, self.axs = plt.subplots(1, 2, layout='compressed', figsize=(6.0, 3.0))
        self.stream = self.data_stream()
        self.ani = animation.FuncAnimation(self.fig, self.update,
                                           init_func=self.setup_plot,
                                           blit=True,
                                           interval=60)

    def data_stream(self):
        i = -1
        while True:
            i = (i + 1) % (len(self.results) - 1)
            yield self.results[i]['mask'], list(self.results[i + 1]['domains'].values())

    def setup_plot(self):
        im = plot_cell_field(self.results[0]['mask'], fig_ax=(self.fig, self.axs[0]))[2]
        sca = plot_cell_particles(list(self.results[1]['domains'].values()), fig_ax=(self.fig, self.axs[0]))[2]
        return im, sca

    def update(self, i):
        data = next(self.stream)

        im = plot_cell_field(data[0], fig_ax=(self.fig, self.axs[0]))[2]
        sca = plot_cell_particles(data[1], fig_ax=(self.fig, self.axs[1]))[2]

        return im, sca


def test_one_cell_one_direction(core):
    """
    Run a cell model that connects CC3D and TissueForge, with interactions going in one direction, from CC3D to TissueForge.
    """

    # Create the specs for a CC3D simulation
    dim = (30, 30, 30)
    cells = (6, 6, 6)

    # make an initial mask array
    initial_mask_array = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    initial_mask_array[10:20, 10:20] = 1

    # initial cell target volume
    init_cell_volume_target = 100.0

    # number of fluid particles is per_dim ** 2 * no. cell sites
    # per_dim = 5
    # no. cell sites = 100
    # result was 400
    # (5 * 10 - 2) ** 2

    # list of initial cell ids
    initial_cell_ids = [1]  # make this work for multiple cells

    # configure compucell3D
    compucell_config_dict = {
        'cc3d': {
            '_type': 'process',
            'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
            'config': {
                'dim': (dim[0], dim[1]),
                'initial_mask': initial_mask_array,
                'init_cell_volume_target': init_cell_volume_target,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
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

    # configure tissue forge
    tissue_forge_config_dict = {
        f'tissue-forge-{cell_id}': {
            '_type': 'process',
            'address': 'local:!tf_simservice.TissueForgeProcess.TissueForgeProcess',
            'config': {
                'cell_id': cell_id,
                'initial_mask': initial_mask_array,
                'growth_rate': 0,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
                'simservice_config': {
                    'dim': dim,
                    'cells': cells,
                    'per_dim': 5,
                    'num_steps': 1000,
                }
            },
            'inputs': {
                'mask': ['mask_store']
            },
            'outputs': {
                'domains': ['domains_store']
                # TODO map output to target_volumes
            }
        } for cell_id in initial_cell_ids
    }

    # configure the ram emitter
    ram_emitter_config = {
        'ram-emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'emit': {
                    'mask': {
                        '_type': 'array',
                        '_shape': (dim[0], dim[1]),
                        '_data': 'integer',
                    },
                    'domains': {
                        '_type': 'any',
                    }
                }
            },
            'inputs': {
                'mask': ['mask_store'],
                'domains': ['domains_store']
            }
        },
    }

    # combine all the specs
    composite = {
        **tissue_forge_config_dict,
        **compucell_config_dict,
        **ram_emitter_config
    }

    # initialize the composite
    sim = Composite(
        {'state': composite},
        core=core
    )

    # run it
    sim.run(5)
    results = sim.gather_results()
    # print(results)


def get_one_cell_two_direction_config(
    dim=(30, 30, 30),
    cells=(6, 6, 6),
    init_cell_volume_target=100.0,
    init_split_threshold=200.0
):
    # Create the specs for a CC3D simulation

    # make an initial mask array
    initial_mask_array = np.zeros(shape=(dim[0], dim[1]), dtype=int)
    initial_mask_array[10:20, 10:20] = 1

    # list of initial cell ids
    initial_cell_ids = [1]  # make this work for multiple cells

    # configure compucell3D
    compucell_config_dict = {
        'cc3d': {
            '_type': 'process',
            'address': 'local:!cc3d_simservice.CC3DProcess.CC3DProcess',
            # 'address': 'local:!cc3d_simservice.MorpheusProcess.MorpheusProcess',
            'config': {
                'dim': (dim[0], dim[1]),
                'initial_mask': initial_mask_array,
                'init_cell_volume_target': init_cell_volume_target,
                'init_split_threshold': init_split_threshold,
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
            },
            'inputs': {
                'target_volumes': ['target_volumes_store'],
                'split_threshold': ['split_threshold_store']
            },
            'outputs': {
                'cell_ids': ['cell_ids_store'],
                'mask': ['mask_store'],
                'divided_cell_ids': ['divided_cell_ids_store']
            }
        },
    }

    # configure tissue forge
    tissue_forge_config_dict = {
        f'tissue-forge-{cell_id}': {
            '_type': 'process',
            'address': 'local:!tf_simservice.TissueForgeProcess.TissueForgeProcess',
            'config': {
                'cell_id': cell_id,
                'initial_mask': initial_mask_array,
                'dim': dim,
                'cells': cells,
                'per_dim': 5,
                'num_steps': 1000,
                'growth_rate': 1.0,  # number of particles added every simulation step
                'process_config': {
                    'disable_ports': {
                        'inputs': [],
                        'outputs': []
                    }
                },
                'simservice_config': {
                    'dim': dim,
                    'cells': cells,
                }
            },
            'inputs': {
                'mask': ['mask_store']
            },
            'outputs': {
                'domains': ['domains_store']
            }
        } for cell_id in initial_cell_ids
    }

    # make a volume adapter that connects the fluid particles to the volume
    volume_config = {
        'volume_adapter': {
            '_type': 'step',
            'address': 'local:!tests.ExplicitCell.adapters.volume_from_particles.VolumeFromParticles',
            'config': {
                # TODO: calculate this from the initial fluid particles
                'optimal_density': 0.25
            },
            'inputs': {
                'domains': ['domains_store']
            },
            'outputs': {
                'volumes': ['target_volumes_store']
            }
        }
    }

    # configure the ram emitter
    ram_emitter_config = {
        'ram-emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'emit': {
                    'mask': {
                        '_type': 'array',
                        '_shape': (dim[0], dim[1]),
                        '_data': 'integer',
                    },
                    'domains': {
                        '_type': 'domains',
                    },
                    'volumes': 'map[float]',
                }
            },
            'inputs': {
                'mask': ['mask_store'],
                'domains': ['domains_store'],
                'volumes': ['target_volumes_store'],
            }
        },
    }

    # combine all the specs
    return {
        **tissue_forge_config_dict,
        **compucell_config_dict,
        **volume_config,
        **ram_emitter_config
    }


def test_one_cell_two_directions(core):
    composite = get_one_cell_two_direction_config()

    # initialize the composite
    sim = Composite(
        {'state': composite},
        core=core
    )

    # run it
    sim.run(60)
    results = sim.gather_results()

    # print(results)
    generate_frames_and_save_gif(results[('ram-emitter',)], output_dir='frames', gif_filename='animation.gif')

    # anim = ResultsAnimator(results[('ram-emitter',)])
    # plt.show()


if __name__ == '__main__':
    core = ProcessTypes()
    register_types(core)

    # test_one_cell_one_direction(core)
    test_one_cell_two_directions(core)
