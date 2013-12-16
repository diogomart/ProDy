# -*- coding: utf-8 -*-
"""This module defines a class and a function for rotating translating blocks
(RTB) calculations."""

import numpy as np

from prody import LOGGER
from prody.atomic import Atomic, AtomGroup
from prody.proteins import parsePDB
from prody.utilities import importLA, checkCoords

from .anm import ANM

__all__ = ['RTB']

class Increment(object):

    def __init__(self, s=0):

        self._i = s

    def __call__(self, i=1):

        self._i += i
        return self._i


class RTB(ANM):

    """Class for Rotations and Translations of Blocks (RTB) method ([FT00]_).

    .. [FT00] Tama F, Gadea FJ, Marques O, Sanejouand YH. Building-block
       approach for determining low-frequency normal modes of macromolecules.
       *Proteins* **2000** 41:1-7.

    """

    def buildHessian(self, coords, blocks, cutoff=15., gamma=1., **kwargs):
        """Build Hessian matrix for given coordinate set.

        :arg coords: a coordinate set or an object with ``getCoords`` method
        :type coords: :class:`numpy.ndarray`

        :arg blocks: a list or array of block identifiers
        :type blocks: list, :class:`numpy.ndarray`

        :arg cutoff: cutoff distance (Å) for pairwise interactions,
            default is 15.0 Å
        :type cutoff: float

        :arg gamma: spring constant, default is 1.0
        :type gamma: float"""


        try:
            coords = (coords._getCoords() if hasattr(coords, '_getCoords') else
                      coords.getCoords())
        except AttributeError:
            try:
                checkCoords(coords)
            except TypeError:
                raise TypeError('coords must be a Numpy array or an object '
                                'with `getCoords` method')

        LOGGER.timeit('_rtb')
        natoms = coords.shape[0]
        if natoms != len(blocks):
            raise ValueError('len(blocks) must match number of atoms')
        from collections import Counter, defaultdict
        i = Increment()
        d = defaultdict(i)
        blocks = np.array([d[b] for b in blocks], np.int64)

        counter = Counter(blocks)

        nblocks = len(counter)
        maxsize = 1
        while counter:
            _, size = counter.popitem()
            if size > maxsize:
                maxsize = size
        LOGGER.info('System has {} blocks largest containing {} of {} units.'
                    .format(nblocks, maxsize, natoms))
        nb6 = nblocks * 6

        coords = coords.T.copy()

        self._hessian = hessian = np.zeros((nb6, nb6), float)
        self._project = project = np.zeros((natoms * 3, nb6), float)

        from rtbtools import buildhessian
        buildhessian(coords, blocks, hessian, project,
                     natoms, nblocks, maxsize,
                     float(cutoff), float(gamma))

        LOGGER.report('Hessian was built in %.2fs.', label='_rtb')


    def calcModes(self, n_modes=20, zeros=False, turbo=True):
        """Calculate normal modes.  This method uses :func:`scipy.linalg.eigh`
        function to diagonalize the Hessian matrix. When Scipy is not found,
        :func:`numpy.linalg.eigh` is used.

        :arg n_modes: number of non-zero eigenvalues/vectors to calculate.
            If ``None`` is given, all modes will be calculated.
        :type n_modes: int or None, default is 20

        :arg zeros: If ``True``, modes with zero eigenvalues will be kept.
        :type zeros: bool, default is ``False``

        :arg turbo: Use a memory intensive, but faster way to calculate modes.
        :type turbo: bool, default is ``True``
        """

        super(TRB, self).calcModes(n_modes, zeros, turbo)

        # do the projection here


def test(pdb='2nwl-mem.pdb', blk='2nwl.blk'):

    from prody import parsePDB
    from numpy import zeros

    pdb = parsePDB(pdb, subset='ca')
    pdb.setData('block', zeros(len(pdb), int))

    with open(blk) as inp:
        for line in inp:
            if line.startswith('BLOCK'):
                _, b, n1, c1, r1, n2, c2, r2 = line.split()
                sel = pdb.select('chain {} and resnum {} to {}'
                                 .format(c1, r1, r2))
                if sel:
                    sel.setData('block', int(b))
    rtb = RTB('2nwl')
    rtb.buildHessian(pdb, pdb.getData('block'))

