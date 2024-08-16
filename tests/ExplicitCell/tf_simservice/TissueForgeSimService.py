import random
import warnings

import numpy as np
from simservice.PySimService import PySimService
import tissue_forge as tf
from typing import Dict, List, Optional, Tuple


def_refinements = 4

Position = Tuple[float, float, float]
Domain = Tuple[List[Position], List[Position]]
ParentChildPair = Tuple[int, int]


class BoundaryType(tf.ParticleTypeSpec):
    radius = 0.1
    mass = 1E9
    dynamics = tf.Overdamped


class InternalType(tf.ParticleTypeSpec):
    radius = 0.1
    mass = 1E1


dpd = tf.Potential.dpd(alpha=100, gamma=10, sigma=1, cutoff=3 * InternalType.radius)
col = tf.Potential.harmonic(k=10000,
                            r0=BoundaryType.radius + InternalType.radius,
                            min=0,
                            max=BoundaryType.radius + InternalType.radius)


def generate_outline(cell_id: int, mask: np.ndarray, positions: Tuple[np.ndarray, np.ndarray]):

    mask_id = mask == cell_id

    mask_x = np.zeros_like(mask_id)
    mask_x[1:, :] = np.diff(mask_id, axis=0)
    nz_mask_x = mask_x[:, :-1] != 0
    mask_x[:, 1:][nz_mask_x] = mask_x[:, :-1][nz_mask_x]

    mask_y = np.zeros_like(mask_id)
    mask_y[:, 1:] = np.diff(mask_id, axis=1)
    nz_mask_y = mask_y[:-1, :] != 0
    mask_y[1:, :][nz_mask_y] = mask_y[:-1, :][nz_mask_y]

    outline_mask = (mask_x != 0) | (mask_y != 0)
    num_outline = np.count_nonzero(outline_mask)

    interm_mask_x_x = positions[0][:, :-1][nz_mask_x] - 0.5
    interm_mask_x_y = positions[1][:, :-1][nz_mask_x]
    interm_mask_y_x = positions[0][:-1, :][nz_mask_y]
    interm_mask_y_y = positions[1][:-1, :][nz_mask_y] - 0.5
    num_interm_x = interm_mask_x_x.shape[0]
    num_interm_y = interm_mask_y_y.shape[0]

    outline_pos = np.zeros((num_outline + num_interm_x + num_interm_y, 2))
    outline_pos[:].T[0][:num_outline] = positions[0][outline_mask] - 0.5
    outline_pos[:].T[1][:num_outline] = positions[1][outline_mask] - 0.5
    outline_pos[:].T[0][num_outline:num_outline+num_interm_x] = interm_mask_x_x
    outline_pos[:].T[1][num_outline:num_outline+num_interm_x] = interm_mask_x_y
    outline_pos[:].T[0][num_outline+num_interm_x:] = interm_mask_y_x
    outline_pos[:].T[1][num_outline+num_interm_x:] = interm_mask_y_y

    return outline_pos


def _outline_winding(positions: np.ndarray, result: List, result_idx=0, dist2_mat: np.ndarray = None):

    # Calculate distance matrix
    n_pos = positions.shape[0]

    if dist2_mat is None:

        x_mat = np.ndarray((n_pos, n_pos))
        y_mat = np.ndarray((n_pos, n_pos))
        for i in range(n_pos):
            x_mat[:, i] = positions.T[:][0]
            y_mat[:, i] = positions.T[:][1]

        # Pair by two nearest neighbors
        dist2_mat = (x_mat - x_mat.T) ** 2 + (y_mat - y_mat.T) ** 2

    ind = np.asarray(list(range(n_pos)))

    if result_idx == 0 and not result:
        result.append([])
        for i in range(n_pos):
            roi = dist2_mat[i, :]
            nz = roi != 0.0
            ind_min_nz = np.where(roi[nz] == roi[nz].min())
            nbs = [ind[nz][i] for i in ind_min_nz[0]]

            if len(nbs) != 2:
                continue

            result[result_idx].append((i, nbs[0]))
            return _outline_winding(positions, result, result_idx, dist2_mat)

    while True:

        completed_indices = [r[0] for r in result[result_idx]]
        current_ind = result[result_idx][-1][1]

        roi = dist2_mat[current_ind, :]
        nz = roi != 0.0
        ind_min_nz = np.where(roi[nz] == roi[nz].min())
        nbs = [ind[nz][i] for i in ind_min_nz[0] if ind[nz][i] not in completed_indices]
        if len(nbs) == 0:
            return
        elif len(nbs) == 1:
            result[result_idx].append((current_ind, nbs[0]))
        else:
            for i, n in enumerate(nbs[1:]):
                res_tmp = [result[result_idx].copy()]
                res_tmp[0].append((current_ind, n))
                _outline_winding(positions, res_tmp, 0, dist2_mat)
                result.extend(res_tmp)
            result[result_idx].append((current_ind, nbs[0]))


def outline_winding(positions: np.ndarray):
    res = []
    _outline_winding(positions, res, 0)
    for r in res:
        if len(r) == positions.shape[0] - 1:
            return [rr[0] for rr in r] + [r[-1][1]]
    raise ValueError('Could not identify winding')


def neighbor_points(positions: np.ndarray):
    # Calculate distance matrix
    n_pos = positions.shape[0]
    x_mat = np.ndarray((n_pos, n_pos))
    y_mat = np.ndarray((n_pos, n_pos))
    for i in range(n_pos):
        x_mat[:, i] = positions.T[:][0]
        y_mat[:, i] = positions.T[:][1]

    # Pair by two nearest neighbors
    dist2_mat = (x_mat - x_mat.T) ** 2 + (y_mat - y_mat.T) ** 2
    nbs = []
    ind = np.asarray(list(range(n_pos)))
    for i in range(n_pos):
        roi = dist2_mat[i, :]
        nz = roi != 0.0
        ind_min_nz = np.where(roi[nz] == roi[nz].min())
        nbs.append([ind[nz][i] for i in ind_min_nz[0]])
    return nbs


def refine_outline(positions: np.ndarray):
    n_pos = len(positions)
    nbs = neighbor_points(positions)

    # Generate intermediate points
    new_pts = set()
    for i in range(len(nbs)):
        pc = positions[i]
        for pn in [positions[n] for n in nbs[i]]:
            new_pts.add((pc[0] + 0.5 * (pn[0] - pc[0]),
                         pc[1] + 0.5 * (pn[1] - pc[1])))

    new_positions = np.zeros((n_pos + len(new_pts), 2))
    new_positions[:n_pos] = positions
    if len(new_pts) > 0:
        new_positions[n_pos:] = np.asarray(list(new_pts))
    return new_positions


def internal_positions(cell_id: int,
                       mask: np.ndarray,
                       positions: Tuple[np.ndarray, np.ndarray],
                       per_dim=2):

    where_ids = np.where(mask == cell_id)

    inc_x = np.zeros((per_dim * per_dim,))
    inc_y = np.zeros((per_dim * per_dim,))
    dz = 1.0 / per_dim
    z0 = dz / 2 - 0.5
    for i in range(per_dim):
        for j in range(per_dim):
            k = i * per_dim + j
            inc_x[k] = z0 + i * dz
            inc_y[k] = z0 + j * dz

    mask_pos_x = positions[0][where_ids]
    mask_pos_y = positions[1][where_ids]
    n_pos = len(mask_pos_x)

    int_pos = np.zeros((per_dim * per_dim * n_pos, 2))
    for i in range(per_dim * per_dim):
        dx, dy = inc_x[i], inc_y[i]
        for j in range(n_pos):
            k = i * n_pos + j
            int_pos[k][:] = mask_pos_x[j] + dx, mask_pos_y[j] + dy
    return int_pos


def discrete_positions(positions: List[tf.FVector3]) -> np.ndarray:
    result = np.ndarray((len(positions), 2), dtype=int)
    for i, p in enumerate(positions):
        result[i, :] = np.asarray(p.xy(), dtype=int)
    return result


def position_domains(positions: List[tf.FVector3], mask: np.ndarray) -> np.ndarray:
    dpos = discrete_positions(positions)
    return np.take(mask, np.ravel_multi_index(np.hsplit(dpos, 2), mask.shape))[:, 0]


def map_positions_by_domain(positions: List[tf.FVector3], mask: np.ndarray) -> Dict[int, List[int]]:
    tags = position_domains(positions, mask)
    unique_ids = np.nonzero(np.unique(mask))
    result = {i: [] for i in unique_ids}
    for i, t in enumerate(tags):
        result[t].append(i)
    return result


def find_positions_in_domain(positions: List[tf.FVector3], mask: np.ndarray, domain_int: int) -> List[int]:
    mask_copy = np.array(mask, dtype=int)
    mask_copy[mask_copy != domain_int] = 0
    return map_positions_by_domain(positions, mask_copy)[domain_int]


def identify_outline_partners(current_positions: np.ndarray,
                              next_positions: np.ndarray):
    num_current = current_positions.shape[0]
    num_next = next_positions.shape[0]

    pos_x_current = np.zeros((num_current, num_next))
    pos_y_current = np.zeros_like(pos_x_current)
    pos_x_next = np.zeros_like(pos_x_current)
    pos_y_next = np.zeros_like(pos_x_current)

    for i in range(num_next):
        pos_x_current.T[i] = current_positions.T[:][0]
        pos_y_current.T[i] = current_positions.T[:][1]
    for i in range(num_current):
        pos_x_next[:][i] = next_positions.T[:][0]
        pos_y_next[:][i] = next_positions.T[:][1]

    dist2_mat: np.ndarray = (pos_x_current - pos_x_next) ** 2 + (pos_y_current - pos_y_next) ** 2

    map_unchanged = []
    map_changed = []
    for i in range(dist2_mat.shape[0]):
        di = dist2_mat[i, :]
        dim = di.min()
        if dim == 0:
            j = np.where(di == dim)[0][0]
            if map_unchanged and j != (map_unchanged[-1][1] + 1) % num_next and j != (map_unchanged[-1][1] - 1) % num_next:
                map_changed.append([map_unchanged[-1], [i, j]])
            map_unchanged.append([i, j])
    # Check for continuity at end
    if map_unchanged[0][0] not in [0, num_current] and map_unchanged[-1][0] not in [0, num_current]:
        map_changed.append((map_unchanged[-1], map_unchanged[0]))

    for i, mc in enumerate(map_changed):
        inda, indb = mc

        indaa, indab = inda
        indba, indbb = indb

        if indaa >= indba:
            indaa, indba = indba, indaa
        if indba - indaa < indaa + num_current - indba:
            x, y = indaa, indba
        else:
            x, y = indba, indaa + num_current
        idxa = [idx % num_current for idx in range(x + 1, y)]

        if indab >= indbb:
            indab, indbb = indbb, indab
        if indbb - indab < indab + num_next - indbb:
            x, y = indab, indbb
        else:
            x, y = indbb, indab + num_next
        idxb = [idx % num_next for idx in range(x, y + 1)]

        # Check for reversal
        idx_sample_current = idxa[0]
        idx_sample_next_0 = idxb[0]
        idx_sample_next_1 = idxb[-1]
        pos_sample_current = current_positions[idx_sample_current]
        pos_sample_next_0 = next_positions[idx_sample_next_0]
        pos_sample_next_1 = next_positions[idx_sample_next_1]
        dx2_0 = (pos_sample_current[0] - pos_sample_next_0[0]) ** 2 + (pos_sample_current[1] - pos_sample_next_0[1]) ** 2
        dx2_1 = (pos_sample_current[0] - pos_sample_next_1[0]) ** 2 + (pos_sample_current[1] - pos_sample_next_1[1]) ** 2
        if dx2_1 < dx2_0:
            idxa.reverse()

        map_changed[i] = idxa, idxb

    return map_unchanged, map_changed


def interp_changed(next_positions: np.ndarray,
                   map_changed: List[Tuple[List[int], List[int]]]):
    result = []
    for mcc, mcn in map_changed:
        num_c = len(mcc)
        num_n = len(mcn)
        pos_n = next_positions[mcn]

        interp_c = np.asarray([x / (num_c + 1) for x in range(1, num_c + 1)])
        interp_n = np.asarray([x / (num_n + 1) for x in range(1, num_n + 1)])

        result_mc = []

        for i, ic in enumerate(interp_c):
            if ic >= interp_n[-1]:
                idxnb = num_n - 1
            else:
                idxnb = np.where(interp_n > ic)[0][0]
            idxna = idxnb - 1

            ina = interp_n[idxna]
            inb = interp_n[idxnb]

            pos_na = pos_n[idxna]
            pos_nb = pos_n[idxnb]
            c = (ic - ina) / (inb - ina)

            pos_c_i = np.asarray([pos_na[0] + c * (pos_nb[0] - pos_na[0]),
                                  pos_na[1] + c * (pos_nb[1] - pos_na[1])])

            result_mc.append(pos_c_i)

        result.append(result_mc)

    return result


class DomainData:

    def __init__(self):

        self.boundary_ids: List[int] = []
        self.internal_ids: List[int] = []


class TissueForgeSimService(PySimService):

    def __init__(self,
                 dim: Tuple[float, float, float],
                 cells: Tuple[int, int, int],
                 per_dim=2,
                 num_steps=100,
                 num_refinements=def_refinements):

        super().__init__()

        self.dim = dim
        self.cells = cells
        self.per_dim = per_dim
        self.num_steps = num_steps
        self.num_refinements = num_refinements

        self.domains: Dict[int, DomainData] = {}
        self.growth_rates: Dict[int, int] = {}
        self.coords_y, self.coords_x = np.meshgrid(np.linspace(0.5, dim[1] - 0.5, int(dim[1])),
                                                   np.linspace(0.5, dim[0] - 0.5, int(dim[0])))

        self.next_mask: Optional[np.ndarray] = None

    def _run(self):
        # tf.Logger.enableConsoleLogging(tf.Logger.TRACE)
        tf.init(dim=list(self.dim),
                cells=list(self.cells),
                # dt=1.0 / self.num_steps,
                bc={'x': tf.BOUNDARY_FREESLIP, 'y': tf.BOUNDARY_FREESLIP, 'z': tf.BOUNDARY_FREESLIP},
                windowless=True,
                window_size=[800 * 6, 600 * 6]
                )

    def _init(self):
        tf.system.set_grid_color(tf.fVector3(0))

    def _start(self):
        boundary_type = BoundaryType.get()
        internal_type = InternalType.get()

        boundary_type.frozen_z = internal_type.frozen_z = True

        tf.bind.types(dpd, internal_type, internal_type)
        tf.bind.types(col, internal_type, boundary_type)

    def _step(self):
        if self.next_mask is None:
            return

        # Interpolate to next state

        new_pos = {}

        for cell_id, domain_data in self.domains.items():

            ol = np.ndarray((len(domain_data.boundary_ids), 2))
            for i, pid in enumerate(domain_data.boundary_ids):
                pos = tf.ParticleHandle(pid).position
                ol[i][:] = pos[0], pos[1]

            nol = generate_outline(cell_id, self.next_mask, (self.coords_x, self.coords_y))
            for _ in range(self.num_refinements):
                nol = refine_outline(nol)
            nol = nol[outline_winding(nol)]
            map_unchanged, map_changed = identify_outline_partners(ol, nol)
            mapped_positions = interp_changed(nol, map_changed)

            for bid in domain_data.boundary_ids:
                tf.ParticleHandle(bid).force_init = tf.FVector3(0)
            if map_changed:
                new_pos[cell_id] = [tf.FVector3(p[0], p[1], tf.Universe.center[2]) for p in nol]

            for i in range(len(map_changed)):
                ids_i = map_changed[i][0]
                pos_i = mapped_positions[i]
                for j in range(len(ids_i)):
                    ph = tf.ParticleHandle(domain_data.boundary_ids[ids_i[j]])
                    posc = ph.position
                    pos_ij = pos_i[j]
                    dpos = tf.FVector3(pos_ij[0], pos_ij[1], posc[2]) - posc
                    ph.force_init = dpos * ph.mass / self.num_steps / tf.Universe.dt

        tf.step(tf.Universe.dt * self.num_steps)

        # Apply growth rates
        for cell_id, growth_rate in self.growth_rates.items():
            if growth_rate == 0:
                continue

            num_internal = len(self.domains[cell_id].internal_ids)
            if growth_rate < 0 and growth_rate < -num_internal:
                growth_rate = max(growth_rate, -num_internal)

            if growth_rate < 0:
                if growth_rate < -num_internal:
                    growth_rate_actual = -num_internal
                else:
                    growth_rate_actual = growth_rate

                internal_ids_copy = self.domains[cell_id].internal_ids.copy()
                random.shuffle(internal_ids_copy)
                for pid in internal_ids_copy[:-growth_rate_actual]:
                    tf.ParticleHandle(pid).destroy()
                    self.domains[cell_id].internal_ids.remove(pid)
            elif growth_rate > 0:
                internal_ids_copy = self.domains[cell_id].internal_ids.copy()
                random.shuffle(internal_ids_copy)
                for pid in internal_ids_copy[:growth_rate]:
                    pp = tf.ParticleHandle(pid)
                    radius = pp.radius
                    angle = random.random() * np.pi * 2
                    direction = tf.FVector3(np.cos(angle), np.sin(angle), 0.0)
                    pc = pp.split(direction)
                    pp.radius = pc.radius = radius
                    self.domains[cell_id].internal_ids.append(pc.id)

        # Refresh boundaries
        boundary_type = BoundaryType.get()
        for cell_id in new_pos.keys():
            domain_data = self.domains[cell_id]
            for bid in domain_data.boundary_ids:
                tf.ParticleHandle(bid).destroy()
            domain_data.boundary_ids.clear()
            for pos in new_pos[cell_id]:
                domain_data.boundary_ids.append(boundary_type(position=pos, velocity=tf.FVector3(0)).id)

        self.next_mask = None

    def set_next_mask(self, mask: np.ndarray):
        """Sets the next mask"""
        self.next_mask = mask

    def add_domain(self, cell_id: int, mask: np.ndarray, growth_rate: int):
        """Adds a domain"""

        # Generate outline
        outline = generate_outline(cell_id, mask, (self.coords_x, self.coords_y))
        for _ in range(self.num_refinements):
            outline = refine_outline(outline)
        outline = outline[outline_winding(outline)]

        # Generate internal positions
        int_pos = internal_positions(cell_id, mask, (self.coords_x, self.coords_y), self.per_dim)
        print(f'No. internal particles: {int_pos.shape}')

        # Calculate centroid for cluster
        com = tf.FVector2(0)
        for pos in int_pos:
            com += tf.FVector2(pos[0], pos[1])
        com /= len(int_pos)

        # Create new cluster
        boundary_type = BoundaryType.get()
        internal_type = InternalType.get()
        domain_data = DomainData()

        # Generate boundary particles
        for p in outline:
            domain_data.boundary_ids.append(boundary_type(position=tf.FVector3(p[0], p[1], tf.Universe.center[2]),
                                                          velocity=tf.FVector3(0)).id)

        # Generate internal particles
        for p in int_pos:
            domain_data.internal_ids.append(internal_type(position=tf.FVector3(p[0], p[1], tf.Universe.center[2]),
                                                          velocity=tf.FVector3(0)).id)

        self.domains[cell_id] = domain_data
        self.growth_rates[cell_id] = growth_rate
        self.next_mask = mask

    def add_set_domain(self, cell_id: int, mask: np.ndarray, cell_domain: Domain, growth_rate: int):
        """
        Adds a cell with a given domain.

        todo: add check for consistency between given mask and domain

        :param cell_id: id of cell to add
        :param mask: current mask
        :param cell_domain: given domain to implement
        :param growth_rate: growth rate to assign
        """

        if cell_id in self.domains:
            warnings.warn(f'New domain clashes with known cell id: {cell_id}')
            return

        # Create new cluster
        boundary_type = BoundaryType.get()
        internal_type = InternalType.get()
        domain_data = DomainData()

        # Generate boundary and internal particles
        outline, int_pos = cell_domain
        for p in outline:
            domain_data.boundary_ids.append(boundary_type(position=tf.FVector3(p[0], p[1], tf.Universe.center[2]),
                                                          velocity=tf.FVector3(0)).id)
        for p in int_pos:
            domain_data.internal_ids.append(internal_type(position=tf.FVector3(p[0], p[1], tf.Universe.center[2]),
                                                          velocity=tf.FVector3(0)).id)

        self.domains[cell_id] = domain_data
        self.growth_rates[cell_id] = growth_rate
        self.next_mask = mask

    def equilibrate(self, num_steps=10000):
        """Equilibrates the simulation."""
        return tf.step(num_steps * tf.Universe.dt)

    def get_domains(self) -> Dict[str, Domain]:
        """Gets the boundary and internal particles of each domain"""
        result = {}
        for domain_id, domain_data in self.domains.items():
            boundary_pos = [tuple(tf.ParticleHandle(pid).position.as_list()) for pid in domain_data.boundary_ids]
            internal_pos = [tuple(tf.ParticleHandle(pid).position.as_list()) for pid in domain_data.internal_ids]
            # todo: process-bigraph requires keys to be strings: hierarchy_depth assumes that all keys are strings;
            #  probably not a conducive requirement for general interoperability.
            result[str(domain_id)] = boundary_pos, internal_pos
        return result

    def set_growth_rates(self, ids_rates_map: Dict[str, int]):
        """Set the growth rate of all cells"""
        for cell_id, growth_rate in ids_rates_map.items():
            # todo: assuming another case of process-bigraph using strings for keys as a requirement
            cell_id_int = int(cell_id)
            if cell_id_int not in self.growth_rates:
                print('Cell id not known:', cell_id_int)
                continue
            self.growth_rates[cell_id_int] = growth_rate

    def divide_cells(self, mask: np.ndarray, parent_child_map: List[ParentChildPair]):
        """
        Divides a cell and keeps all cellular particles in this service.

        Assumes that the growth rate of the child is the same as the parent.

        :param mask: cell mask to implement
        :param parent_child_map: parent-child id pairs from division to implement
        """

        boundary_type = BoundaryType.get()

        for parent_id, child_id in parent_child_map:

            parent_domain_data = self.domains[parent_id]
            child_domain_data = DomainData()

            # Generate outlines
            parent_outline = generate_outline(parent_id, mask, (self.coords_x, self.coords_y))
            child_outline = generate_outline(child_id, mask, (self.coords_x, self.coords_y))
            for _ in range(self.num_refinements):
                parent_outline = refine_outline(parent_outline)
                child_outline = refine_outline(child_outline)
            parent_outline = parent_outline[outline_winding(parent_outline)]
            child_outline = child_outline[outline_winding(child_outline)]

            # Generate new outline for parent and child based on new mask
            for pid in parent_domain_data.boundary_ids:
                tf.ParticleHandle(pid).destroy()
            parent_domain_data.boundary_ids.clear()
            for p in parent_outline:
                parent_domain_data.boundary_ids.append(boundary_type(position=tf.FVector3(p[0], p[1],
                                                                                          tf.Universe.center[2]),
                                                                     velocity=tf.FVector3(0)).id)
            for p in child_outline:
                child_domain_data.boundary_ids.append(boundary_type(position=tf.FVector3(p[0], p[1],
                                                                                         tf.Universe.center[2]),
                                                                    velocity=tf.FVector3(0)).id)

            # Find current internal particles and move to child as appropriate
            p_internal_positions = [tf.ParticleHandle(pid).position for pid in parent_domain_data.internal_ids]
            c_internal_pos_indices = find_positions_in_domain(p_internal_positions, mask, child_id)
            c_internal_pos_indices.sort()
            c_internal_pos_indices.reverse()
            child_domain_data.internal_ids = [parent_domain_data.internal_ids.pop(i) for i in c_internal_pos_indices]
            child_domain_data.internal_ids.reverse()

            self.domains[child_id] = child_domain_data
            self.growth_rates[child_id] = self.growth_rates[parent_id]

        self.next_mask = mask

    def divide_cell_and_take(self, mask: np.ndarray, parent_id: int, child_id: int) -> Domain:
        """
        Divides a cell and returns the domain of the implemented child cell. Ownership of the child is released.

        :param mask: cell mask to implement
        :param parent_id: id of parent cell
        :param child_id: id of child cell
        :return: domain of child cell
        """

        boundary_type = BoundaryType.get()

        parent_domain_data = self.domains[parent_id]

        # Generate outlines
        parent_outline = generate_outline(parent_id, mask, (self.coords_x, self.coords_y))
        child_outline = generate_outline(child_id, mask, (self.coords_x, self.coords_y))
        for _ in range(self.num_refinements):
            parent_outline = refine_outline(parent_outline)
            child_outline = refine_outline(child_outline)
        parent_outline = parent_outline[outline_winding(parent_outline)]
        child_outline = child_outline[outline_winding(child_outline)]
        child_boundary_positions = [(p[0], p[1], tf.Universe.center[2]) for p in child_outline]

        # Generate new outline for parent based on new mask
        for pid in parent_domain_data.boundary_ids:
            tf.ParticleHandle(pid).destroy()
        parent_domain_data.boundary_ids.clear()
        for p in parent_outline:
            parent_domain_data.boundary_ids.append(boundary_type(position=tf.FVector3(p[0], p[1],
                                                                                      tf.Universe.center[2]),
                                                                 velocity=tf.FVector3(0)).id)

        # Find current internal particles and release to child as appropriate
        p_internal_positions = [tf.ParticleHandle(pid).position for pid in parent_domain_data.internal_ids]
        c_internal_pos_indices = find_positions_in_domain(p_internal_positions, mask, child_id)
        c_internal_pos_indices.sort()
        child_internal_positions = [tuple(p_internal_positions[i].as_list()) for i in c_internal_pos_indices]
        c_internal_pos_indices.reverse()
        for i in c_internal_pos_indices:
            tf.ParticleHandle(parent_domain_data.internal_ids.pop(i)).destroy()

        self.next_mask = mask

        return child_boundary_positions, child_internal_positions
