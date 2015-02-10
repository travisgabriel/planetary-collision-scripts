#---------------------------------------------------------------------------------
# bound_mass - a utility for finding the largest gravitationally bound mass in SPH
# output data. 
#
# Author: Naor Movshovitz (nmovshov at gee mail dot com)
#---------------------------------------------------------------------------------
import sys, os, shutil
import numpy as np
import argparse
import ahelpers
cout = sys.stdout.write

def _main():
    """Entry point when used as command line utility (recommended)."""

    # Parse command line arguments
    args = _PCL()
    
    # Load node list data
    cout("Reading file...")
    fnl = ahelpers.load_fnl(args.filename)
    cout("Done.\n")
    pos = np.vstack((fnl.x, fnl.y, fnl.z)).T
    vel = np.vstack((fnl.vx, fnl.vy, fnl.vz)).T
    m   = fnl.m
    print "Found {} particles (in {} node lists) totaling {} kg.".format(
        fnl.nbNodes, np.unique(fnl.id).size, sum(m))

    # Dispatch to the work method
    [M_bound, ind_bound] = bound_mass(pos, vel, m, args.method)

    # Report and exit
    print "Found {} bound particles totaling {} kg.".format(
        sum(ind_bound), M_bound)
    print "M_bound/M_tot = {}.".format(M_bound/sum(m))
    return

def bound_mass(pos, vel, m, method='jutzi', units=[1,1,1]):
    """Given cloud of particles return largest gravitationally bound mass.

    This function looks at a cloud of point masses with known positions and
    velocities and attempts to find the largest (by mass) subset that is
    gravitationally bound. There are different choices for the algorithm to use,
    and all algorithms are only approximations. The only sure way of finding the
    bound particles is to integrate the system in time for many gravitational time
    scales.

    The algorithm employed is chosen by the label supplied in the method argument.
    The choices implemented currently are:
      'kory' - In the RF of the particle with lowest potential return the
               particles return the particles wil negative total energy.
      'jutzi' - In the RF of the particle with lowest potential remove particles
                with positive total energy. Repeat until stable.
      'naor1' - Add particles bound to the particle with lowest potential. In the
                CM frame of this set, add particles bound to the set. Repeat until
                stable.
      'naor2' - Coming soon.

    This function is a dispatcher - the work is carried out in sub functions.

    Parameters
    ----------
    pos : n-by-3 numeric array
        Particle positions.
    vel : n-by-3 numeric array
        Particle velocities.
    m : n-by-1 numeric array
        Particle masses.
    units : numeric positive 3-vector, optional
        Length, mass, and time units, in mks, of the particle coordinates.
    method : string
        Algorithm to use.

    Returns
    -------
    M_bound : real positive scalar
        Mass of the largest bound clump
    ind_bound : logical nparray
        Indices of bound particles
    """

    # Some minimal assertions (NOT bullet-proof filter!)
    pos = np.array(pos)
    vel = np.array(vel)
    m   = np.array(m)
    units = np.array(units)
    assert pos.ndim == 2 and pos.shape[1] == 3 and np.all(np.isreal(pos))
    assert vel.ndim == 2 and vel.shape[1] == 3 and np.all(np.isreal(vel))
    assert m.ndim == 1 and np.all(np.isreal(m)) and np.all(m > 0)
    assert units.ndim == 1 and len(units) == 3 and np.all(units > 0)
    assert len(pos) == len(vel) == len(m)
    assert method in ['kory', 'jutzi', 'naor1', 'naor2']

    # Deal with units
    bigG = 6.67384e-11*units[0]**(-3)*units[1]*units[2]**2

    # Dispatch to sub functions by method
    if   method == 'kory':
        (M_bound, ind_bound) = _bm_kory(pos, vel, m, bigG)
        pass
    elif method == 'jutzi':
        (M_bound, ind_bound) = _bm_jutzi(pos, vel, m, bigG)
        pass
    elif method == 'naor1':
        (M_bound, ind_bound) = _bm_naor1(pos, vel, m, bigG)
        pass
    elif method == 'naor2':
        print method
        pass
    else:
        sys.exit("Unknown method") # this can't really happen
        pass

    return (M_bound, ind_bound)

def _bm_kory(pos, vel, m, bigG):
    """In RF of lowest potential node return nodes with negative energy."""
    U = bigG*_potential(pos[:,0],pos[:,1],pos[:,2],m);
    return (1, [True, False, False])
    pass

def _bm_naor2(pos, vel, m, length_scale, units=[1,1,1]):
    """Given cloud of particles return largest gravitationally bound mass.

    This function looks at a cloud of point masses with known positions and 
    velocities and attempts to find the largest subset (clump) that is 
    gravitationally bound. That is, the largest (by mass) clump where the kinetic
    energy of each particle, relative to the center of mass of the clump, is
    smaller than the gravitational energy binding it to the other particles in
    the clump. This is NOT a rigorous test. I can easily think of many cases where
    it would fail. But I think it should work for the case of a target losing some
    mass in a collision, if the collision was simulated in the target frame.
    
    Parameters
    ----------
    pos : n-by-3 numeric array
        Particle positions.
    vel : n-by-3 numeric array
        Particle velocities.
    m : n-by-1 numeric array
        Particle masses.
    length_scale : numeric positive scalar
        Physical length scale of the system. Used to define "closeness" in
        the clustering algorithm.
    units : numeric positive 3-vector, optional
        Length, mass, and time units, in mks, of the particle coordinates.

    Returns
    -------
    M_bound : real positive scalar
        Mass of the largest bound clump
    ind_bound : logical nparray
        Indices of bound particles
    """
    
    # Some minimal assertions (NOT bullet-proof filter!)
    pos = np.array(pos)
    vel = np.array(vel)
    m   = np.array(m)
    units = np.array(units)
    assert pos.ndim == 2 and pos.shape[1] == 3 and np.all(np.isreal(pos))
    assert vel.ndim == 2 and vel.shape[1] == 3 and np.all(np.isreal(vel))
    assert m.ndim == 1 and np.all(np.isreal(m)) and np.all(m > 0)
    assert np.isscalar(length_scale) and np.isreal(length_scale) and length_scale > 0
    assert units.ndim == 1 and len(units) == 3 and np.all(units > 0)
    assert len(pos) == len(vel) == len(m)
    
    # First, find the largest clump based on euclidean proximity. Note that this
    # is the time consuming part of the process, using an n^2 algorithm for
    # neighbor finding.
    labels = fast_clumps(pos.tolist(), length_scale)
    labels = np.array(labels)
    c_labels = np.unique(labels)
    c_masses = [sum(m[labels == c_labels[k]]) for k in range(len(c_labels))]
    c_major_label = c_labels[np.argmax(c_masses)]
    
    # Ok. All nodes labeled c_major_label belong to the biggest geometrical
    # clump. Let's find the center of mass of this clump.
    cmask = labels == c_major_label
    POS = pos[cmask]
    VEL = vel[cmask]
    M = m[cmask]
    R_com = np.dot(POS.T, M)/sum(M)
    V_com = np.dot(VEL.T, M)/sum(M)

    # Ok. Now pretend each node outside the largest clump feels a point-mass
    # potential from the clump, and test its energy in the clump frame.
    M_bound = M.sum()
    ind_bound = cmask
    G = 6.67384e-11*units[0]**(-3)*units[1]*units[2]**2
    GM = G*M_bound
    for k in range(len(pos)):
        if ind_bound[k]:
            continue
        U = -GM/np.sqrt(np.dot(pos[k], pos[k]))
        K = np.dot(vel[k], vel[k])
        if U + K < 0:
            M_bound += m[k]
            ind_bound[k] = True
            pass
        pass

    # That's it.
    return (M_bound, ind_bound)

def fast_clumps(pos, L):
    """Partition a cloud of point masses into distinct clumps based on proximity.

    This is the optimized version of nr3.eclazz functions, which partitions any
    set (tree) into equivalence classes (connected components). See nr3.eclazz for
    details of the algorithm. This function is a specialized version for the case
    where the set is a cloud of particles with (x,y,z) coordinates and the
    connectivity test is a simple euclidean distance threshold.

    Parameters
    ----------
    pos : numpy.ndarray or list
      An n-by-3 array of coordinates. A list of lists seems to work best.
    L : float, positive
      The distance threshold for the proximity test.

    Returns
    -------
    labels : list of ints
        A vector of integer labels. labels[k] is the clump that pos[k] belongs to.
        There are len(np.unique(labels)) such clumps.
    """
    
    # Some minimal assertions
    assert isinstance(pos, (list, np.ndarray))
    assert np.isreal(L) and np.isscalar(L) and L >= 0
    if type(pos) is np.ndarray:
        assert(pos.ndim == 2 and pos.shape[1] == 3)
        pass

    # Prepare
    labels = [-1]*len(pos)
    L2 = L**2
    
    # This is the nr3 algorithm, specialized to a euclidean distance test
    labels[0] = 0;
    for j in range(1, len(pos)):
        labels[j] = j
        pj = pos[j]
        for k in range(0,j):
            labels[k] = labels[labels[k]]
            pk = pos[k]
            if (pj[0] - pk[0])**2 + (pj[1] - pk[1])**2 + (pj[2] - pk[2])**2 < L2:
                labels[labels[labels[k]]] = j
                pass
            pass
        pass
    for j in range(len(pos)):
        labels[j] = labels[labels[j]]
        pass
    
    # That's it
    return labels

def _PCL():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help="name of file containing node list data")
    parser.add_argument('-m','--method', help="choice of algorithm",
                                         choices=['kory', 'jutzi', 'naor1', 'naor2'],
                                         default='jutzi')
    args = parser.parse_args()
    return args

def _potential(x, y, z, m, mask=None):
    if mask is None:
        mask = np.array(len(x)*[True])
    U = np.zeros(x.shape)
    for j in range(len(x)):
        if mask[j]:
            for k in range(j):
                dx = x[j] - x[k]
                dy = y[j] - y[k]
                dz = z[j] - z[k]
                dr = np.sqrt(dx*dx + dy*dy + dz*dz)
                U[j] = U[j] - m[k]/dr
                U[k] = U[k] - m[j]/dr
                pass
            pass
        pass

    return U

if __name__ == "__main__":
    _main()
    pass
