import os
import json
from pathlib import Path
from typing import Literal, Optional, TypedDict, Dict, Any, List, Tuple, Union
from abacustest.lib_model.model_013_inputs import PrepInput
from abacustest.lib_prepare.abacus import AbacusStru, ReadInput, WriteInput
from abacustest.lib_collectdata.collectdata import RESULT

from abacusagent.init_mcp import mcp

@mcp.tool()
def abacus_prepare(
    stru_file: Path,
    stru_type: Literal["cif", "poscar", "abacus/stru"] = "cif",
    pp_path: Optional[Path] = None,
    orb_path: Optional[Path] = None,
    job_type: Literal["scf", "relax", "cell-relax", "md"] = "scf",
    lcao: bool = True,
    extra_input: Optional[Dict[str, Any]] = None,
) -> TypedDict("results",{"job_path": Path}):
    """
    Prepare input files for ABACUS calculation.
    Args:
        stru_file: Structure file in cif, poscar, or abacus/stru format.
        stru_type: Type of structure file, can be 'cif', 'poscar', or 'abacus/stru'. 'cif' is the default. 'poscar' is the VASP POSCAR format. 'abacus/stru' is the ABACUS structure format.
        pp_path: The pseudopotential library path, if is None, will use the value of environment variable ABACUS_PP_PATH.
        orb_path: The orbital library path, if is None, will use the value of environment variable ABACUS_ORB_PATH.
        job_type: The type of job to be performed, can be 'scf', 'relax', 'cell-relax', or 'md'. 'scf' is the default.
        lcao: Whether to use LCAO basis set, default is True. If True, the orbital library path must be provided.
        extra_input: Extra input parameters for ABACUS. 
    
    Returns:
        A dictionary containing the job path.
    Raises:
        FileNotFoundError: If the structure file or pseudopotential path does not exist.
        ValueError: If LCAO basis set is selected but no orbital library path is provided.
        RuntimeError: If there is an error preparing input files.
    """
    
    if not os.path.isfile(stru_file):
        raise FileNotFoundError(f"Structure file {stru_file} does not exist.")
    
    # Check if the pseudopotential path exists
    pp_path = pp_path if pp_path is not None else os.getenv("ABACUS_PP_PATH")
    if pp_path is None or not os.path.exists(pp_path):
        raise FileNotFoundError(f"Pseudopotential path {pp_path} does not exist.")
    
    if orb_path is None and os.getenv("ABACUS_ORB_PATH") is not None:
        orb_path = os.getenv("ABACUS_ORB_PATH")
    
    if lcao and orb_path is None:
        raise ValueError("LCAO basis set is selected but no orbital library path is provided.")
    
    extra_input_file = None
    if extra_input is not None:
        # write extra input to the input file
        extra_input_file = "INPUT.tmp"
        WriteInput(extra_input, extra_input_file)
    
    try:
        _, job_path = PrepInput(
            files=str(stru_file),
            filetype=stru_type,
            jobtype=job_type,
            pp_path=pp_path,
            orb_path=orb_path,
            input_file=extra_input_file
        ).run()
    except Exception as e:
        raise RuntimeError(f"Error preparing input files: {e}")

    if len(job_path) == 0:
        raise RuntimeError("No job path returned from PrepInput.")
    
    return {"job_path": Path(job_path[0]).absolute()}

@mcp.tool()
def abacus_modify_input(
    input_file: Path,
    modified_input_file: Path = Path("INPUT_NEW"),
    stru_file: Optional[Path] = None,
    dft_plus_u_settings: Optional[Dict[str, Union[float, Tuple[Literal["p", "d", "f"], float]]]] = None,
    extra_input: Optional[Dict[str, Any]] = None
) -> TypedDict("results",{"input_path": Path}):
    """
    Modify keywords in ABACUS INPUT file.
    Args:
        input_file: Path to the original ABACUS INPUT file.
        modified_input_file: Path to save the modified ABACUS INPUT file.
        stru_file: Path to the ABACUS STRU file, required for determining atom types in DFT+U settings.
        dft_plus_u_setting: Dictionary specifying DFT+U settings.  
            - Key: Element symbol (e.g., 'Fe', 'Ni').  
            - Value: A list with one or two elements:  
                - One-element form: float, representing the Hubbard U value (orbital will be inferred).  
                - Two-element form: [orbital, U], where `orbital` is one of {'p', 'd', 'f'}, and `U` is a float.
        extra_input: Additional key-value pairs to update the INPUT file.

    Returns:
        A dictionary containing the path of the modified INPUT file under the key `'input_path'`.
    Raises:
        FileNotFoundError: If path of given INPUT file does not exist
        RuntimeError: If write modified INPUT file failed
    """
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"INPUT file {input_file} does not exist.")
    
    input_param = ReadInput(input_file)
    for key, value in extra_input.items():
        input_param[key] = value
    
    # DFT+U settings
    main_group_elements = [
    "H", "He", 
    "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Nh", "Fl", "Mc", "Lv", "Ts", "Og" ]
    transition_metals = [
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn"]
    lanthanides_and_acnitides = [
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr"]

    orbital_corr_map = {'p': 1, 'd': 2, 'f': 3}
    if dft_plus_u_settings is not None:
        input_param['dft_plus_u'] = 1

        stru = AbacusStru.ReadStru(stru_file)
        elements = stru.get_element(number=False,total=False)
        
        orbital_corr_param, hubbard_u_param = '', ''
        for element in elements:
            if element not in dft_plus_u_settings:
                orbital_corr_param += ' -1 '
                hubbard_u_param += ' 0 '
            else:
                if type(dft_plus_u_settings[element]) is not float: # orbital_corr and hubbard_u are provided
                    orbital_corr = orbital_corr_map[dft_plus_u_settings[element][0]]
                    orbital_corr_param += f" {orbital_corr} "
                    hubbard_u_param += f" {dft_plus_u_settings[element][1]} "
                else: #Only hubbard_u is provided, use default orbital_corr
                    if element in main_group_elements:
                        default_orb_corr = 1
                    elif element in transition_metals:
                        default_orb_corr = 2
                    elif element in lanthanides_and_acnitides:
                        default_orb_corr = 3
                    
                    orbital_corr_param += f" {default_orb_corr} "
                    hubbard_u_param += f" {dft_plus_u_settings[element]} "
        
        input_param['orbital_corr'] = orbital_corr_param.strip()
        input_param['hubbard_u'] = hubbard_u_param.strip()

    try:
        WriteInput(input_param, modified_input_file)
        return {'input_path': Path(modified_input_file).absolute()}
    except Exception as e:
        raise RuntimeError("Error occured during writing modified INPUT file")

@mcp.tool()
def abacus_modify_stru(
    stru_file: Path,
    modified_stru_file: Path = Path("STRU_NEW"),
    pp: Optional[Dict[str, str]] = None,
    orb: Optional[Dict[str, str]] = None,
    fix_atoms_idx: Optional[List[int]] = None,
    movable_coords: Optional[List[bool]] = None,
    initial_magmoms: Optional[List[List[float]]] = None,
    angle1: Optional[List[float]] = None,
    angle2: Optional[List[float]] = None
) -> TypedDict("results",{"stru_path": Path}):
    """
    Modify pseudopotential, orbital, atom fixation, initial magnetic moments and initial velocities in ABACUS STRU file.
    Args:
        stru_file: Path to the original ABACUS STRU file.
        modified_stru_file: Path to save the modified STRU file.
        pp: Dictionary mapping element names to pseudopotential file paths.
            If not provided, the pseudopotentials from the original STRU file are retained.
        orb: Dictionary mapping element names to numerical orbital file paths.
            If not provided, the orbitals from the original STRU file are retained.
        fix_atoms_idx: List of indices of atoms to be fixed.
        movable_coords: For each fixed atom, specify which coordinates are allowed to move.
            Each entry is a list of 3 integers (0 or 1), where 1 means the corresponding coordinate (x/y/z) can move.
            Example: if `fix_atoms_idx = [1]` and `movable_coords = [[0, 1, 1]]`, the x-coordinate of atom 1 will be fixed.
        initial_magmoms: Initial magnetic moments for atoms.
            - For collinear calculations: a list of floats, shape (natom).
            - For non-collinear using Cartesian components: a list of 3-element lists, shape (natom, 3).
            - For non-collinear using angles: a list of floats, shape (natom), one magnetude of magnetic moment per atom.
        angle1: in non-colinear case, specify the angle between z-axis and real spin, in angle measure instead of radian measure
        angle2: in non-colinear case, specify angle between x-axis and real spin in projection in xy-plane , in angle measure instead of radian measure

    Returns:
        A dictionary containing the path of the modified ABACUS STRU file under the key 'stru_path'.
    Raises:
        ValueError: If `stru_file` is not path of a file
    """
    if stru_file.is_file():
        stru = AbacusStru.ReadStru(stru_file)
    else:
        raise ValueError(f"{stru_file} is not path of a file")
    
    # Set pp and orb
    if pp is not None:
        pplist = []
        for element in stru.get_element(number=False,total=False):
            pplist.append(pp[element])
        stru.set_pp(pplist)

    if orb is not None:
        orb_list = []
        for element in stru.get_element(number=False,total=False):
            orb_list.append(orb[element])
        stru.set_orb(orb_list)
    
    # Set atomic magmom for every atom
    if initial_magmoms is not None:
        stru.set_atommag(initial_magmoms)
    if angle1 is not None and angle2 is not None:
        stru.set_angle1(angle1)
        stru.set_angle2(angle2)
    
    # Set atom fixations
    # Atom fixations in fix_atoms and movable_coors will be applied to original atom fixation
    if fix_atoms_idx is not None:
        atom_move = stru.get_move()
        for fix_idx, atom_idx in enumerate(fix_atoms_idx):
            atom_move[atom_idx] = movable_coords[fix_idx]
        stru._move = atom_move
    
    stru.write(modified_stru_file)
    
    return {'stru_path': modified_stru_file.absolute()}

@mcp.tool()
def abacus_collect_data(
    abacusjob: Path,
    metrics: List[str] = ["normal_end", "scf_conv", "energy", "total_time"]
) -> TypedDict("results",{"collected_data": Path}):
    """
    Collect ABACUS calculation results.
    Args:
        abacusjob (str): Path to the directory containing the ABACUS job output files.
        metrics (List[str]): List of metric names to collect.  
                  metric_name  description
                      version: the version of ABACUS
                        ncore: the mpi cores
                      omp_num: the omp cores
                   normal_end: if the job is normal ending
                        INPUT: a dict to store the setting in OUT.xxx/INPUT
                          kpt: list, the K POINTS setting in KPT file
                     fft_grid: fft grid for charge/potential
                        nbase: number of basis in LCAO
                       nbands: number of bands
                       nkstot: total K point number
                         ibzk: irreducible K point number
                        natom: total atom number
                        nelec: total electron number
                   nelec_dict: dict of electron number of each species
                  point_group: point group
   point_group_in_space_group: point group in space group
                     converge: if the SCF is converged
                    total_mag: total magnetism (Bohr mag/cell)
                 absolute_mag: absolute magnetism (Bohr mag/cell)
                       energy: the total energy (eV)
                    energy_ks: the E_KohnSham, unit in eV
                     energies: list of total energy of each ION step
                       volume: the volume of cell, in A^3
                       efermi: the fermi energy (eV). If has set nupdown, this will be a list of two values. The first is up, the second is down.
              energy_per_atom: the total energy divided by natom, (eV)
                        force: list[3*natoms], force of the system, if is MD or RELAX calculation, this is the last one
                       forces: list of force, the force of each ION step. Dimension is [nstep,3*natom]
                       stress: list[9], stress of the system, if is MD or RELAX calculation, this is the last one
                       virial: list[9], virial of the system, = stress * volume, and is the last one.
                     pressure: the pressure of the system, unit in kbar.
                     stresses: list of stress, the stress of each ION step. Dimension is [nstep,9]
                      virials: list of virial, the virial of each ION step. Dimension is [nstep,9]
                    pressures: list of pressure, the pressure of each ION step.
             largest_gradient: list, the largest gradient of each ION step. Unit in eV/Angstrom
                         band: Band of system. Dimension is [nspin,nk,nband].
                  band_weight: Band weight of system. Dimension is [nspin,nk,nband].
                    band_plot: Will plot the band structure. Return the file name of the plot.
                     band_gap: band gap of the system
                   total_time: the total time of the job
                  stress_time: the time to do the calculation of stress
                   force_time: the time to do the calculation of force
                     scf_time: the time to do SCF
           scf_time_each_step: list, the time of each step of SCF
                   step1_time: the time of 1st SCF step
                    scf_steps: the steps of SCF
                    atom_mags: list of list, the magnization of each atom of each ion step.
                     atom_mag: list, the magnization of each atom. Only the last ION step.
                    atom_elec: list of list of each atom. Each atom list is a list of each orbital, and each orbital is a list of each spin
                atom_orb_elec: list of list of each atom. Each atom list is a list of each orbital, and each orbital is a list of each spin
                   atom_mag_u: list of a dict, the magnization of each atom calculated by occupation number. Only the last SCF step.
                  atom_elec_u: list of a dict with keys are atom index, atom label, and electron of U orbital.
                         drho: [], drho of each scf step
                    drho_last: drho of the last scf step
                      denergy: [], denergy of each scf step
                 denergy_last: denergy of the last scf step
                denergy_womix: [], denergy (calculated by rho without mixed) of each scf step
           denergy_womix_last: float, denergy (calculated by rho without mixed) of last scf step
             lattice_constant: a list of six float which is a/b/c,alpha,beta,gamma of cell. If has more than one ION step, will output the last one.
            lattice_constants: a list of list of six float which is a/b/c,alpha,beta,gamma of cell
                         cell: [[],[],[]], two-dimension list, unit in Angstrom. If is relax or md, will output the last one.
                        cells: a list of [[],[],[]], which is a two-dimension list of cell vector, unit in Angstrom.
                    cell_init: [[],[],[]], two-dimension list, unit in Angstrom. The initial cell
                   coordinate: [[],..], two dimension list, is a cartesian type, unit in Angstrom. If is relax or md, will output the last one
              coordinate_init: [[],..], two dimension list, is a cartesian type, unit in Angstrom. The initial coordinate
                      element: list[], a list of the element name of all atoms
                        label: list[], a list of atom label of all atoms
                 element_list: same as element
               atomlabel_list: same as label
                         pdos: a dict, keys are 'energy' and 'orbitals', and 'orbitals' is a list of dict which is (index,species,l,m,z,data), dimension of data is nspin*ne
                       charge: list, the charge of each atom.
                   charge_spd: list of list, the charge of each atom spd orbital.
                 atom_mag_spd: list of list, the magnization of each atom spd orbital.
               relax_converge: if the relax is converged
                  relax_steps: the total ION steps
               ds_lambda_step: a list of DeltaSpin converge step in each SCF step
                ds_lambda_rms: a list of DeltaSpin RMS in each SCF step
                       ds_mag: a list of list, each element list is for each atom. Unit in uB
                 ds_mag_force: a list of list, each element list is for each atom. Unit in eV/uB
                      ds_time: a list of the total time of inner loop in deltaspin for each scf step.
                      mem_vkb: the memory of VNL::vkb, unit it MB
                    mem_psipw: the memory of PsiPW, unit it MB

    Returns:
        A dictionary containing the path of a json file containing collected data of ABACUS calculation.
    Raises:
        IOError: If read abacus result failed
        RuntimeError: If error occured during collectring data using abacustest
    """
    try:
        abacusresult = RESULT(fmt="abacus", path=abacusjob)
    except:
        raise IOError("Read abacus result failed")
    
    collected_metrics = {}
    for metric in metrics:
        try:
            collected_metrics[metric] = abacusresult[metric]
        except Exception as e:
            raise RuntimeError(f"Error during collecting {metric}")
    
    metric_file_path = abacusjob / "metrics.json"
    with open(metric_file_path, "w", encoding="UTF-8") as f:
        json.dump(collected_metrics, f, indent=4)
    
    return {'collected_data': metric_file_path.absolute()}
