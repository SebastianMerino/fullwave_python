from pathlib import Path

import numpy as np

import fullwave_simulation
from fullwave_simulation.conditions import PlaneWaveInitialCondition
from fullwave_simulation.constants.constant import Constant
from fullwave_simulation.domains import (
    AbdominalWall,
    Background,
    DomainOrganizer,
    PhantomLateral,
    Scatterer,
)
from fullwave_simulation.solvers import FullwaveSolver
from fullwave_simulation.transducers import (
    L125Transducer,
    LinearTxWaveTransmitter,
    SignalReceiver,
)
from fullwave_simulation.transducers.linear_receiver_map import LinearReceiverMap
from fullwave_simulation.transducers.linear_transmitter_map import LinearTransmitterMap
from fullwave_simulation.utils import MapViewer


class SimulationParams(Constant):
    """ 
    Class that handles simulation parameters as constants
    """
    # dummy parameter for a plane wave imaging
    focal_depth = 3e-2
    # actual spacing of L12-5 50mm = 0.1953e-4 [m]
    spacing_m = 1.953e-4
    # number of active txducer elements (each emit)
    txducer_aperture = 64
    # walking aperture, sequential txrx events
    nelements = 192
    # nevents = nelements - txducer_aperture

    # --- Basic variables / parameters ---
    # speed of sound (m/s)
    c0 = 1540  # [m/s]
    # frequency [MHz]
    # f0 = 6.25e6
    f0 = 1e6  # [Hz]
    # pressure in Pa.
    p0 = 1e5  # [Pa]

    # number of points per spatial wavelength
    ppw = 12
    # Courant-Friedrichs-Levi condition
    cfl = 0.4

    # width of simulation field (m). lateral dimension.
    wX = 3.0e-2  # [m]
    # depth of simulation field (m)
    wY = 5.0e-2  # [m]

    # duration of simulation (s).
    # the time how much you want to simulate the propagation (sec)
    dur = wY * 2.3 / c0

    # --- initial conditions ---
    # number of cycles in pulse
    ncycles = 2
    # exponential drop-off of envelope
    drop_off = 2

    # plane wave sequences
    n_angles = 11
    f_number = 1

    # --- aliases ---
    width = wX
    depth = wY
    modT = 7
    num_cycles = ncycles
    nevents = n_angles

    is_fsa = False
    d_theta = 1.75 * np.pi / 180

    @property
    def omega0(self):
        return 2 * np.pi * self.f0

    @property
    def lambda_(self):
        return self.c0 / self.f0


class MaterialProperties(Constant):
    """
    Class that handles material properties as constants.
        bovera: B/A or nonlinearity coeff.
        beta:   1 + (B/A)/2
        alpha:  Attenuation coeff. [dB/cm/MHz^gamma]
        ppower: Attenuation power law or gamma
        c0:     Sound speed [m/s]
        rho0:   Density
    """
    fat = {"bovera": 9.6, "alpha": 0.48, "ppower": 1.1, "c0": 1478, "rho0": 950}
    fat["beta"] = 1 + fat["bovera"] / 2

    liver = {"bovera": 7.6, "alpha": 0.5, "ppower": 1.0, "c0": 1570, "rho0": 1064}
    liver["beta"] = 1 + liver["bovera"] / 2

    muscle = {"bovera": 9, "alpha": 1.09, "ppower": 1.0, "c0": 1547, "rho0": 1050}
    muscle["beta"] = 1 + muscle["bovera"] / 2

    water = {"bovera": 5, "alpha": 0.005, "ppower": 2.0, "c0": 1480, "rho0": 1000}
    water["beta"] = 1 + water["bovera"] / 2

    skin = {"bovera": 8, "alpha": 2.1, "ppower": 1, "c0": 1498, "rho0": 1000}
    skin["beta"] = 1 + skin["bovera"] / 2

    tissue = {"bovera": 9, "alpha": 0.5, "ppower": 1, "c0": 1540, "rho0": 1000}
    tissue["beta"] = 1 + tissue["bovera"] / 2

    connective = {"bovera": 8, "alpha": 1.57, "ppower": 1, "c0": 1613, "rho0": 1120}
    connective["beta"] = 1 + connective["bovera"] / 2

    blood = {"bovera": 5, "alpha": 0.005, "ppower": 2.0, "c0": 1520, "rho0": 1000}
    blood["beta"] = 1 + blood["bovera"] / 2

    lung_fluid = {"bovera": 5, "alpha": 0.005, "ppower": 2.0, "c0": 1440, "rho0": 1000}
    lung_fluid["beta"] = 1 + lung_fluid["bovera"] / 2

    lung_air = {"bovera": 5, "alpha": 0.005, "ppower": 2.0, "c0": 340, "rho0": 1000}
    lung_air["beta"] = 1 + lung_air["bovera"] / 2

    c0 = 1540
    rho0 = 1000
    a0 = 0.5
    beta0 = 0


class LinearTransmitterMapMod(LinearTransmitterMap):
    """ Modified the input layer number """
    def _calculate_inmap(self) -> np.ndarray:
        in_map = np.zeros((self.num_x, self.num_y))
        in_map[:, 0:8] = 1  # changed the input layer num
        return in_map


class L125TransducerMod(L125Transducer):
    """ Modified the input layer number in transmitter """
    def _make_transducer_surface_map(self, nX, nY):
        transmitter_map = LinearTransmitterMapMod(
            num_x=nX,
            num_y=nY,
            ppw=self.ppw,
            material_properties=self.material_properties,
            simulation_params=self.simulation_params,
        )
        receiver_map = LinearReceiverMap(
            num_x=nX,
            num_y=nY,
            beam_spacing=self.beam_spacing,
            in_map=transmitter_map.in_map,
            ppw=self.ppw,
            material_properties=self.material_properties,
            simulation_params=self.simulation_params,
        )
        return transmitter_map, receiver_map


def main():
    # Define your work directory and make the directory.
    home_dir = Path(fullwave_simulation.__file__).parent.parent
    work_dir = home_dir / "outputs" / "exp_dir_20240603_test"
    work_dir.mkdir(exist_ok=True, parents=True)

    # Set the parameters with fullwave_simulation.constants classes.
    simulation_params = SimulationParams()
    material_properties = MaterialProperties()

    # Define the transducer properties using class in `fullwave_simulation.transducers`.
    l125_transducer = L125TransducerMod(simulation_params, material_properties)

    # Define the simulation domains using fullwave_simulation.domains classes.
    # Each domain has its own material properties like density, sound speed, attenuation, etc.
    # If you need to make a new simulational maps or domains such as abdmonial wall, lung, or liver,
    # you will write a class refer to these classes.
    background_domain_properties = "tissue"
    map_viewer = MapViewer(save_dir=work_dir / "input_maps")

    # In this example, background with scatter, abdominal wall, and phantom were defined.
    # First, download the abdominal wall data and put them to `fullwave_simulation/domains/data`
    # https://drive.google.com/file/d/1KMSlqcgXSzd9NGU2fauO9OJ6s8PPrA5P/view?usp=sharing
    abdominal_wall = AbdominalWall(
        num_x=l125_transducer.num_x,
        num_y=l125_transducer.num_y,
        crop_depth=0.8e-2,
        start_depth=0.0,
        dY=l125_transducer.dY,
        dX=l125_transducer.dX,
        transducer=l125_transducer,
        abdominal_wall_mat_path=Path(
            "fullwave_simulation/domains/data/abdominal_wall/i2365f_etfw1.mat"
        ),
        material_properties=material_properties,
        simulation_params=simulation_params,
        apply_tissue_deformation=False,
        apply_tissue_compression=True,
        use_smoothing=True,
        skip_i0=False,
        use_center_region=True,
        background_domain_properties=background_domain_properties,
        ppw=simulation_params.ppw,
        sequence_type="plane",
    )

    background = Background(
        abdominal_wall.geometry.shape[0],
        l125_transducer.num_y,
        material_properties,
        simulation_params,
        background_domain_properties=background_domain_properties,
    )
    scatterer = Scatterer(
        num_x=abdominal_wall.geometry.shape[0],
        num_y=l125_transducer.num_y,
        material_properties=material_properties,
        simulation_params=simulation_params,
        transducer=l125_transducer,
    )
    csr = 0.035     # 3.5% variation in density
    background.rho_map = background.rho_map - scatterer.rho_map * csr # adds scatterers to background
    phantom = PhantomLateral(
        num_x=abdominal_wall.geometry.shape[0],
        num_y=l125_transducer.num_y,
        material_properties=material_properties,
        simulation_params=simulation_params,
        dX=l125_transducer.dX,
        dY=l125_transducer.dY,
        base_circle_depth_in_meter=3e-2,
        lat_phantom_in_meter=abdominal_wall.geometry.shape[0] * l125_transducer.dX,
        depth_phantom_in_meter=simulation_params.wY,
        background_domain_properties=background_domain_properties,
    )

    # Next, register each domain classes into DomainOrganizer and construct a integrated domain.
    # The order of the domains is important.
    # The domain map will be constructed in a bottom-up fashion with DomainOrganizer like a sticker
    # using the registered domains.
    domain_organizer = DomainOrganizer(
        material_properties=material_properties,
        ignore_non_linearity=True,
        background_domain_properties=background_domain_properties,
    )
    domain_organizer.register_domains(
        [
            background,
            phantom,
            abdominal_wall,
        ],
    )
    domain_organizer.construct_domain()

    # you can view the constructed domain maps using MapViewer.
    for map_type in ["rho_map", "beta_map", "c_map", "a_map", "geometry", "air_map"]:
        map_viewer.view_map(
            domain_organizer.constructed_domain_dict[map_type].T,
            title=map_type,
            save_name_base=map_type,
            extent=[
                -abdominal_wall.geometry.shape[0] * l125_transducer.dX / 2 * 1e3,
                abdominal_wall.geometry.shape[0] * l125_transducer.dX / 2 * 1e3,
                simulation_params.wY * 1e3,
                0,
            ],
            # extent=None,
            aspect="equal",
        )

    # Now, define the wave transmitter and signal receiver.
    # WaveTransmitter is used to calculate the transmission pulse.
    # SignalReceiver does not have an effect at the moment.
    wave_transmitter = LinearTxWaveTransmitter(
        l125_transducer,
        simulation_params=simulation_params,
        material_properties=material_properties,
        is_fsa=simulation_params.is_fsa,
    )
    signal_receiver = SignalReceiver(
        l125_transducer,
        simulation_params=simulation_params,
        material_properties=material_properties,
    )

    # Define the initial condition.
    # InitialCondition class is used to generate the icmat,
    # which is the initial pressure in time space,
    # for each event based on the transmission pulse (icvec).
    # icvec will be generated by the wave_transmitter.
    initial_condition = PlaneWaveInitialCondition(
        transducer=l125_transducer,
        wave_transmitter=wave_transmitter,
        simulation_params=simulation_params,
    )

    # Finally, pass the above defined parameters to the solver and run the simulation.
    # genout_list contains numpy array version of the genout,
    # which is a Fullwave2's output file.
    # Each outputs will be exported in the work directory defined in a first step.
    fw_solver = FullwaveSolver(
        work_dir=work_dir,
        #
        simulation_params=simulation_params,
        #
        domain_organizer=domain_organizer,
        transducer=l125_transducer,
        wave_transmitter=wave_transmitter,
        signal_receiver=signal_receiver,
        #
        initial_condition=initial_condition,
        on_memory=False,
        sequence_type="plane",
    )
    genout_list = fw_solver.run()
    print()


if __name__ == "__main__":
    main()
