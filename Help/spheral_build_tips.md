Tips for troubleshooting SPHERAL builds
---------------------------------------

It can be tricky to get SPHERAL to build correctly on some systems. The nominal
procedure described in [`../build_spheral.md`](../build_spheral.md) sometimes
fails, usually in the process of building one of the many third party libraries,
and always with cryptic unhelpful error messages. In this document we will keep
a cumulative record of errors encountered and workarounds found on various
systems.

##### HINDMOST
This is a desktop workstation at UCSC.

###### System
```
[nmovshov@hindmost ~]$ uname -smpior
Linux 2.6.32-573.22.1.el6.x86_64 x86_64 x86_64 x86_64 GNU/Linux
```
```
[nmovshov@hindmost ~]$ cat /etc/*-release
CentOS release 6.7 (Final)
LSB_VERSION=base-4.0-amd64:base-4.0-noarch:core-4.0-amd64:core-4.0-
noarch:graphics-4.0-amd64:graphics-4.0-noarch:printing-4.0-amd64:printing
-4.0-noarch
CentOS release 6.7 (Final)
CentOS release 6.7 (Final)
```

###### Special vars/hacks/tricks
None. The nominal build procedure works as expected. No runtime errors.

###### Environment (after applying tricks if any)
```
[nmovshov@hindmost ~]$ echo $SHELL
/bin/tcsh
```
```
[nmovshov@hindmost ~]$ which gcc
/usr/bin/gcc
[nmovshov@hindmost ~]$ which g++
/usr/bin/g++
[nmovshov@hindmost ~]$ gcc --version
gcc (GCC) 4.4.7 20120313 (Red Hat 4.4.7-16)
Copyright (C) 2010 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
```
```
[nmovshov@hindmost ~]$ which mpirun
/soft/openmpi_gcc_1.8.7/CentOS_6/bin/mpirun
[nmovshov@hindmost ~]$ mpirun --version
mpirun (Open MPI) 1.8.7

Report bugs to http://www.open-mpi.org/community/help/

[nmovshov@hindmost ~]$ which mpicc
/soft/openmpi_gcc_1.8.7/CentOS_6/bin/mpicc
[nmovshov@hindmost ~]$ which mpicxx
/soft/openmpi_gcc_1.8.7/CentOS_6/bin/mpicxx
[nmovshov@hindmost ~]$ mpicc --version
gcc (GCC) 4.4.7 20120313 (Red Hat 4.4.7-16)
Copyright (C) 2010 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
```
```
[nmovshov@hindmost ~]$ echo $LD_LIBRARY_PATH
/soft/scipy_0.13.0/CentOS_6/lib:/soft/cuda/CentOS_6/lib64:/soft/
openmpi_gcc_1.8.7/CentOS_6/lib:/soft/git_2.6.0/CentOS_6/lib
```

##### HYADES
[This](https://pleiades.ucsc.edu/hyades/Hyades_QuickStart_Guide) is a
supercomputer cluster at UCSC Astrophysics.

###### System
```
[nmovshov@hyades ~]$ uname -smpior
Linux 2.6.32-504.16.2.el6.x86_64 x86_64 x86_64 x86_64 GNU/Linux
```
```
[nmovshov@hyades ~]$ cat /etc/*-release
CentOS release 6.6 (Final)
LSB_VERSION=base-4.0-amd64:base-4.0-noarch:core-4.0-amd64:core-4.0-noarch:graphics-4.0-amd64:graphics-4.0-noarch:printing-4.0-amd64:printing-4.0-noarch
CentOS release 6.6 (Final)
Rocks release 6.2 (SideWinder)
CentOS release 6.6 (Final)
```

###### Special vars/hacks/tricks
Hyades uses the Environment Modules tool to manage users' environments. By
defaul the Intel Compilers and Intel MPI modules are loaded. So far I am unable
to build spheral using the intel compilers. I replace the loaded modules by
```
module swap intel_mpi openmpi-x86_64
```
Then I have to make sure serial compilers are matched with MPI compilers:
```
setenv OMPI_CC gcc
setenv OMPI_CXX g++
setenv I_MPI_CC icc
setenv I_MPI_CXX icc
```
But that's not all. At this point the build will succeed but I get runtime
errors. Something in the version of `mpirun` is off. Luckily, Anaconda python
ships with an MPI setup. So after
```
module load python/Anaconda-2.1.0
```
I get the version of `mpirun` that works.

In addition, to use `SciPy` I need to build a local copy of `LAPACK` in
my home direcory and point `LD_LIBRARY_PATH` to it. This is not required to run
spheral but some analysis scripts may use it.

###### Environment (after applying tricks if any)
```
[nmovshov@hyades ~]$ echo $SHELL
/bin/tcsh
```
```
[nmovshov@hyades ~]$ which gcc
/usr/bin/gcc
[nmovshov@hyades ~]$ which g++
/usr/bin/g++
[nmovshov@hyades ~]$ gcc --version
gcc (GCC) 4.4.7 20120313 (Red Hat 4.4.7-11)
Copyright (C) 2010 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
```
```
[nmovshov@hyades ~]$ which mpirun
/pfs/sw/python/Anaconda-2.1.0/bin/mpirun
[nmovshov@hyades ~]$ mpirun --version
HYDRA build details:
    Version:                                 1.4.1p1
    Release Date:                            Thu Sep  1 13:53:02 CDT 2011
    CC:                              gcc
    CXX:                             c++
    F77:                             gfortran
    F90:                             f95
    Configure options:                       '--enable-shared' '--prefix=/opt/anaconda1anaconda2anaconda3' '--disable-option-checking' 'CC=gcc' 'CFLAGS= -O2' 'LDFLAGS= ' 'LIBS=-lrt -lpthread ' 'CPPFLAGS= -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpl/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpl/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/openpa/src -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/openpa/src -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/common/datatype -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/common/datatype -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/common/locks -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/common/locks -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/channels/nemesis/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/channels/nemesis/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/channels/nemesis/nemesis/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/channels/nemesis/nemesis/include -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/channels/nemesis/nemesis/utils/monitor -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/mpid/ch3/channels/nemesis/nemesis/utils/monitor -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/util/wrappers -I/home/ilan/aroot/work/mpich2-1.4.1p1/src/util/wrappers'
    Process Manager:                         pmi
    Launchers available:                      ssh rsh fork slurm ll lsf sge manual persist
    Topology libraries available:              hwloc plpa
    Resource management kernels available:    user slurm ll lsf sge pbs
    Checkpointing libraries available:
    Demux engines available:                  poll select
```
```
[nmovshov@hyades ~]$ which mpicc
/pfs/sw/python/Anaconda-2.1.0/bin/mpicc
[nmovshov@hyades ~]$ which mpicxx
/pfs/sw/python/Anaconda-2.1.0/bin/mpicxx
[nmovshov@hyades ~]$ mpicc --version
gcc (GCC) 4.4.7 20120313 (Red Hat 4.4.7-11)
Copyright (C) 2010 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
```
```
[nmovshov@hyades ~]$ echo $LD_LIBRARY_PATH
/home/nmovshov/LAPACK:/opt/intel/composer_xe_2013_sp1.1.106/compiler/lib/intel64:/opt/intel/composer_xe_2013_sp1.1.106/ipp/lib/intel64:/opt/intel/composer_xe_2013_sp1.1.106/mkl/lib/intel64:/opt/intel/composer_xe_2013_sp1.1.106/tbb/lib/intel64:/opt/intel/composer_xe_2013_sp1.1.106/debugger/lib/intel64:/usr/lib64/openmpi/lib:/opt/python/lib
```

##### Comet
This is a supercomputer cluster ar SwRI.

###### System

###### Special vars/hacks/tricks

###### Environment (after applying tricks if any)

##### Cholla (This is the planetary group cluster ar ASU.)

Download the most bleeding edge version
```hg clone http://hg.code.sf.net/p/spheral/code spheral```

Use the following compiler flags
```./configure --with-compilers=gnu --without-opensubdiv```
 
NOTE: 'opensubdiv' is a dependency of one of the thirdpartypackages. It is developed by Pixar and has its own dependencies on 3D modeling/graphics software like Maya and, strangely enough, another piece of software developed by Warner Brothers Studios.
 
You may still get errors about a non-existant compiler "mpig++". In this case, alter the config line to use "mpic++" in place of "mpig++".

After install, when running test files you may get this error:
 ```
 [root@headnode benchmark]# /home/gabrt/bin/spheral/src/BUILD/Linux_x86_64/bin/python -i Noh-spherical-3d-benchmark.py
/home/gabrt/bin/spheral/src/BUILD/Linux_x86_64/lib/python2.7/site-packages/Spheral/mpi.py:8: RuntimeWarning: compiletime version 2.6 of module 'mpi4py.MPI' does not match runtime version 2.7
  from mpi4py import MPI
Traceback (most recent call last):
  File "Noh-spherical-3d-benchmark.py", line 13, in <module>
    import loadmpi
ImportError: No module named loadmpi
>>>
```
Run the test files this way instead:
```
../../spheral/src/BUILD/Linux_x86_64/bin/ats -e ../../spheral/src/BUILD/Linux_x86_64/bin/python integration.ats
```

###### System

###### Special vars/hacks/tricks

###### Environment (after applying tricks if any)
