""" Tests for molecule creation and file i/o
"""
import collections

import numpy
import pytest

import moldesign as mdt
mdt.compute.config.engine_type = 'docker'
from moldesign import units as u

from .helpers import get_data_path


@pytest.fixture
def bipyridine_sdf():
    return mdt.read(get_data_path('bipyridine.sdf'))


@pytest.fixture
def bipyridine_xyz():
    return mdt.read(get_data_path('bipyridine.xyz'))


@pytest.fixture
def bipyridine_mol2():
    return mdt.read(get_data_path('bipyridine.mol2'))


@pytest.fixture
def bipyridine_iupac():
    return mdt.from_name('bipyridine')


@pytest.fixture
def bipyridine_smiles():
    return mdt.from_smiles('c1ccnc(c1)c2ccccn2')

ATOMDATA = {  # (symbol, valence, mass)
    1: ('H', 1, 1.008 * u.amu),
    6: ('C', 4, 12.000 * u.amu),
    7: ('N', 3, 14.003 * u.amu),
    8: ('O', 2, 15.995 * u.amu)}


@pytest.mark.parametrize('key', 'mol2 xyz sdf iupac smiles'.split())
def test_read_bipyridine_from_format(key, request):
    mol = request.getfuncargvalue('bipyridine_'+key)

    atomcounts = collections.Counter(atom.symbol for atom in mol.atoms)
    assert len(atomcounts) == 3
    assert atomcounts['C'] == 10
    assert atomcounts['N'] == 2
    assert atomcounts['H'] == 8

    assert mol.charge == 0
    assert abs(mol.mass - 156.069*u.amu) < 0.001 * u.amu
    for atom in mol.atoms:
        assert atom.formal_charge == 0.0
        symb, val, mss = ATOMDATA[atom.atnum]
        assert atom.symbol == symb
        assert atom.valence == val
        assert abs(atom.mass - mss) < 0.001 * u.amu

    assert mol.num_bonds == 21
    bondorders = collections.Counter(bond.order for bond in mol.bonds)
    assert bondorders[2] == 6
    assert bondorders[1] == 15
    assert len(bondorders) == 2


@pytest.fixture
def dna_pdb():
    return mdt.read(get_data_path('ACTG.pdb'))


@pytest.fixture
def dna_mmcif():
    return mdt.read(get_data_path('ACTG.cif'))


@pytest.fixture
def dna_sequence():
    return mdt.build_bdna('ACTG')


@pytest.fixture
def pdb_1kbu():
    return mdt.read(get_data_path('1KBU.pdb'))


@pytest.fixture
def mmcif_1kbu():
    return mdt.read(get_data_path('1KBU.cif'))


@pytest.mark.parametrize('key', 'pdb mmcif sequence'.split())
def test_read_dna_from_format(key, request):
    if key == 'mmcif':
        pytest.xfail(reason='Known mmcif parser bug, fix this by 0.7.4')
    mol = request.getfuncargvalue('dna_'+key)


@pytest.mark.parametrize('key', 'mmcif pdb'.split())
def test_1kbu_assembly_data(key, request):
    mol = request.getfuncargvalue('%s_1kbu' % key)

    assert len(mol.properties.bioassemblies) == 1
    assert '1' in mol.properties.bioassemblies
    assembly = mol.properties.bioassemblies['1']

    assert len(assembly.transforms) == 2
    assert set(assembly.chains) == set(c.name for c in mol.chains)

    # first transform is identity
    numpy.testing.assert_allclose(assembly.transforms[0],
                                  numpy.identity(4))

    # second transform's rotation is unitary
    rot = assembly.transforms[1][:3,:3]
    numpy.testing.assert_allclose(rot.dot(rot.T),
                                  numpy.identity(3))


@pytest.mark.parametrize('key', 'mmcif pdb'.split())
def test_1kbu_assembly_build(key, request):
    asym = request.getfuncargvalue('%s_1kbu' % key)

    original = mdt.Molecule(asym)

    assembly = asym.properties.bioassemblies['1']

    rot = assembly.transforms[1][:3,:3]
    move = assembly.transforms[1][:3,3] * u.angstrom

    mol = mdt.build_assembly(asym, 1)
    assert mol.num_chains == 2 * asym.num_chains

    # test that original is unaffected
    assert original == asym

    testchain = assembly.chains[0]
    new_chain_pos = mol.chains[testchain].positions.T.ldot(rot).T + move[None, :]
    numpy.testing.assert_allclose(new_chain_pos.defunits_value(),
                                  mol.chains[asym.num_chains].positions.defunits_value())
