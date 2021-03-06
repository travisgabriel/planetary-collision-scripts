#! /proj/nmovshov_hindmost/collisions/SPHERAL/bin/python
#-------------------------------------------------------------------------------
# Run a polytropic fluid planet to hydrostatic equilibrium.
#
# This script demonstrates the interaction of gravity and hydrodynamics inside a
# planet sized body. Using an index 1 polytropic equation-of-state, the planet
# should converge to a known density profile. But some tricks need to be employed
# to help the inherently dynamic spheral reach a more-or-less static equilibrium.
#
# To run as an executable script, check that the shebang line points to the full
# path to spheral's python.
#-------------------------------------------------------------------------------
assert False, "NOT READY DO NOT USE!"
from math import *
import sys, os
import random
import mpi # Mike's simplified mpi wrapper
from SolidSpheral3d import *
from findLastRestart import findLastRestart
from VoronoiDistributeNodes import distributeNodes3d
from NodeHistory import NodeHistory
from GenerateNodeDistribution3d import GenerateNodeDistribution3d
pcsbase = '' # Edit this with full path to <pcs> if you see an ImportError.
sys.path += ['..',pcsbase,os.getenv('PCSBASE','')]
import shelpers # My module of some helper functions

#-------------------------------------------------------------------------------
# NAV SETUP
# Physical parameters are in MKS units unless otherwise specified.
#-------------------------------------------------------------------------------

# Job name and description
jobName = 'polystatic'
jobDesc = "Hydrostatic equilibrium of a polytropic planet."
print '\n', jobName.upper(), '-', jobDesc.upper()

# Planet parameters
rPlanet = 11.8             # Initial guess for radius of planet (earth radii)
mPlanet = 318              # Mass of planet (earth masses)
polytrope_n  = 1           # Polytropic index (n=1)
polytrope_K  = 2e5         # Polytropic constant (Pressure/density^n)
polytrope_mu = 2.2e-3      # Mean molecular weight (kg/mole)
mPlanet *= 5.972e24
rPlanet *= 6371.0e3
rhoPlanet = 3.0*mPlanet/(4.0*pi*rPlanet**3)
gravTime = 1/sqrt(MKS().G*rhoPlanet)

# Cooldown mechanism
cooldownMethod = 'dashpot' # 'dashpot' or 'stomp' 
cooldownPower = 1.0        # Dimensionless cooldown "strength" >=0
cooldownFrequency = 1      # Cycles between application (use 1 with dashpot)
                           # * With 'stomp' method, 0<=power<=1

# Times, simulation control, and output
nxPlanet = 20              # Nodes across diameter of planet (run "resolution")
steps = None               # None or advance a number of steps rather than to a time
goalTime = 20*gravTime     # Time to advance to (sec)
dtInit = 2.0               # Initial guess for time step (sec)
vizTime = 0.4*gravTime     # Time frequency for dropping viz files (sec)
vizCycle = None            # Cycle frequency for dropping viz files
outTime = vizTime          # Time between running output routine (sec)
outCycle = None            # Cycles between running output routine

# Node list parameters
nPerh = 1.51               # Nominal number of nodes per smoothing scale
hmin = 1.0e-6*rPlanet      # Lower bound on smoothing length
hmax = 1.0e-1*rPlanet      # Upper bound on smoothing length
rhomin = 0.001*rhoPlanet   # Lower bound on node density
rhomax = 4.0*rhoPlanet     # Upper bound on node density

# Gravity parameters
softLength = 1.0/nxPlanet  # Fraction of planet radius as softening length
opening = 1.0              # Dimensionless opening parameter for gravity tree walk
fdt = 0.1                  # Time step multiplier (dt=fdt*sqrt(softlength/a))
softLength *= rPlanet
G = MKS().G

# More simulation parameters
dtGrowth = 2.0             # Maximum growth factor for time step per cycle 
dtMin = 0                  # Minimum allowed time step (sec)
dtMax = 0.1*goalTime       # Maximum allowed time step (sec)
verbosedt = False          # Verbose reporting of the time step criteria per cycle
maxSteps = 1000            # Maximum allowed steps for simulation advance
statsStep = None           # Frequency for sampling conservation statistics and such
redistributeStep = 2000    # Frequency to load balance problem from scratch
restartStep = 200          # Frequency to drop restart files
restoreCycle = None        # If None, latest available restart cycle is selected
baseDir = jobName          # Base name for directory to store output in

#-------------------------------------------------------------------------------
# NAV Assertions
# This is a good place for a quick abort if some bad parameter choices are going
# to cause trouble later, in confusing ways. We assume that spheral constructors
# use their own assertions, so here we can validate just our own stuff. Another
# valid option would be to simply not worry about it, and let exceptions happen.
#-------------------------------------------------------------------------------
assert 0 <= cooldownPower, "cool DOWN not up"
if cooldownMethod is 'stomp':
    assert 0 <= cooldownPower <= 1.0, "stomp fraction is 0-1"
assert type(cooldownFrequency) is int and cooldownFrequency > 0, "very funny"
assert cooldownMethod in ['dashpot','stomp'], "unknown cooldown method"
assert (cooldownFrequency == 1) or (not(cooldownMethod is 'dashpot')),\
        "dashpot cooling method requires frequency=1"
assert (outTime is None) or (outCycle is None),\
        "output on both time and cycle is confusing"

#-------------------------------------------------------------------------------
# NAV Spheral hydro solver options
# These options for spheral's hydro mechanism are normally left alone.
#-------------------------------------------------------------------------------
HydroConstructor = ASPHHydro
Qconstructor = MonaghanGingoldViscosity
Cl = 1.0
Cq = 1.0
Qlimiter = False
balsaraCorrection = False
epsilon2 = 1e-2
negligibleSoundSpeed = 1e-4 # kind of arbitrary.
csMultiplier = 1e-4
hminratio = 0.1
limitIdealH = False
cfl = 0.5
useVelocityMagnitudeForDt = False
XSPH = True
epsilonTensile = 0.0
nTensile = 4
HEvolution = IdealH
densityUpdate = IntegrateDensity # (Sum|Integrate)Density
compatibleEnergyEvolution = True
rigorousBoundaries = False

#-------------------------------------------------------------------------------
# NAV Equation of state
# Here we construct the polytropic equation of state.
#-------------------------------------------------------------------------------
eosPlanet = PolytropicEquationOfStateMKS3d(polytrope_K,
                                           polytrope_n,
                                           polytrope_mu)
assert eosPlanet.valid(), "equation of state construction failed"

#-------------------------------------------------------------------------------
# NAV Restarts and output directories
# Here we create the output directories, and deal with restarted runs if any.
#-------------------------------------------------------------------------------
# Name directories and files.
jobDir = os.path.join(baseDir, 
                       'nxPlanet=%i' % nxPlanet,
                       )
restartDir = os.path.join(jobDir, 'restarts', 'proc-%04i' % mpi.rank)
vizDir = os.path.join(jobDir, 'viz')
outDir = os.path.join(jobDir, 'output')
restartName = os.path.join(restartDir, jobName)

# Check if the necessary directories exist.  If not, create them.
if mpi.rank == 0:
    if not os.path.exists(jobDir):
        os.makedirs(jobDir)
    if not os.path.exists(vizDir):
        os.makedirs(vizDir)
    if not os.path.exists(restartDir):
        os.makedirs(restartDir)
    if not os.path.exists(outDir):
        os.makedirs(outDir)
mpi.barrier()
if not os.path.exists(restartDir):
    os.makedirs(restartDir)
mpi.barrier()

# If we're restarting, find the set of most recent restart files.
if restoreCycle is None:
    restoreCycle = findLastRestart(restartName)

#-------------------------------------------------------------------------------
# NAV Node construction
# Here we create and populate a node list with initial conditions. In spheral, the
# construction order is as follows:
# 1. Create an empty node list with fields matching the size and type of problem.
# 2. Create a "generator" that will decide what values to give all field variables
#    of node i. Normally we start with one of the simple, stock generators, and
#    modify the x,y,z,vx,vy,vz,rho,U values to suit our initial conditions.
# 3. Distribute, using the (nodeList, generator) pair, among ranks. The generator
#    will be used to fill values in the node list, and then discarded. 
#-------------------------------------------------------------------------------
# Create the node list.
planet = makeFluidNodeList('planet', eosPlanet, 
                           nPerh = nPerh, 
                           xmin = -10.0*rPlanet*Vector.one, # (probably unnecessary)
                           xmax =  10.0*rPlanet*Vector.one, # (probably unnecessary)
                           hmin = hmin,
                           hmax = hmax,
                           rhoMin = rhomin,
                           rhoMax = rhomax,
                           hminratio = hminratio,
                           topGridCellSize = 10*rPlanet,
                           )
nodeSet = [planet]

# Unless restarting, create the generator and set initial field values.
if restoreCycle is None:
    # Start with the stock generator.
    planetGenerator = GenerateNodeDistribution3d(nxPlanet, nxPlanet, nxPlanet,
                                                 rhoPlanet,
                                                 distributionType = 'lattice',
                                                 xmin = (-rPlanet, -rPlanet, -rPlanet),
                                                 xmax = ( rPlanet,  rPlanet,  rPlanet),
                                                 rmin = 0.0,
                                                 rmax = rPlanet,
                                                 nNodePerh = nPerh)

    # We disturb the lattice symmetry to avoid artificial singularities.
    for k in range(planetGenerator.localNumNodes()):
        planetGenerator.x[k] *= 1.0 + random.uniform(-0.02, 0.02)
        planetGenerator.y[k] *= 1.0 + random.uniform(-0.02, 0.02)
        planetGenerator.z[k] *= 1.0 + random.uniform(-0.02, 0.02)
        pass


    # Fill node list using generators and distribute to ranks.
    print "Starting node distribution..."
    distributeNodes3d((planet, planetGenerator))
    nGlobalNodes = 0
    for n in nodeSet:
        print "Generator info for %s" % n.name
        print "   Minimum number of nodes per domain : ", \
              mpi.allreduce(n.numInternalNodes, mpi.MIN)
        print "   Maximum number of nodes per domain : ", \
              mpi.allreduce(n.numInternalNodes, mpi.MAX)
        print "               Global number of nodes : ", \
              mpi.allreduce(n.numInternalNodes, mpi.SUM)
        nGlobalNodes += mpi.allreduce(n.numInternalNodes, mpi.SUM)
    del n
    print "Total number of (internal) nodes in simulation: ", nGlobalNodes
    
    pass
# The spheral controller needs a DataBase object to hold the node lists.
db = DataBase()
for n in nodeSet:
    db.appendNodeList(n)
del n

#-------------------------------------------------------------------------------
# NAV Spheral's simulation structure
# Here we construct the objects that compose spheral's simulation hierarchy.
# These are:
#  * One or more physics packages (hydro, gravity, strength, damage)
#  * A time integrator of some flavor (usually a Runge-Kutta 2)
#  * The simulation controller
#-------------------------------------------------------------------------------
# Create the gravity package.
gravity = OctTreeGravity(G = G, 
                         softeningLength = softLength, 
                         opening = opening, 
                         ftimestep = fdt)

# Create the kernel function for SPH.
WT = TableKernel(BSplineKernel(), 1000) # one for normal hydro

# Create the artificial viscosity object.
q = Qconstructor(Cl, Cq)
q.limiter = Qlimiter
q.balsaraShearCorrection = balsaraCorrection
q.epsilon2 = epsilon2
q.negligibleSoundSpeed = negligibleSoundSpeed
q.csMultiplier = csMultiplier

# Create the hydro package.
hydro = HydroConstructor(W = WT,
                         Q = q,
                         cfl = cfl,
                         useVelocityMagnitudeForDt = useVelocityMagnitudeForDt,
                         compatibleEnergyEvolution = compatibleEnergyEvolution,
                         gradhCorrection = False,
                         densityUpdate = densityUpdate,
                         HUpdate = HEvolution,
                         XSPH = XSPH,
                         epsTensile = epsilonTensile,
                         nTensile = nTensile)

# Create the time integrator and attach the physics packages to it.
integrator = CheapSynchronousRK2Integrator(db)
integrator.appendPhysicsPackage(gravity)
integrator.appendPhysicsPackage(hydro)
integrator.lastDt = dtInit
integrator.dtMin = dtMin
integrator.dtMax = dtMax
integrator.dtGrowth = dtGrowth
integrator.verbose = verbosedt
integrator.rigorousBoundaries = rigorousBoundaries

# Create the controller.
control = SpheralController(integrator, WT,
                            statsStep = statsStep,
                            restartStep = restartStep,
                            redistributeStep = redistributeStep,
                            restartBaseName = restartName,
                            restoreCycle = restoreCycle,
                            vizBaseName = jobName,
                            vizDir = vizDir,
                            vizStep = vizCycle,
                            vizTime = vizTime)

#-------------------------------------------------------------------------------
# NAV Periodic, mid-run actions
# Here we register optional work to be done mid-run. Mid-run processes can be time
# or cycle based. Here we use:
#  * cooldown() - slow and cool internal nodes [cycle based]
#  * output() - a generic access routine, usually a pickle of node list or some
#               calculated value of interest [cycle or time based]
#-------------------------------------------------------------------------------
def mOutput(stepsSoFar,timeNow,dt):
    mFileName="{0}-{1:04d}-{2:g}.{3}".format(
              jobName, stepsSoFar, timeNow, 'fnl.gz')
    shelpers.pflatten_node_list_list(nodeSet, outDir + '/' + mFileName)
    pass
if not outCycle is None:
    control.appendPeriodicWork(mOutput,outCycle)
if not outTime is None:
    control.appendPeriodicTimeWork(mOutput,outTime)

def cooldown(stepsSoFar,timeNow,dt):
    nbGlobalNodes = mpi.allreduce(sum([nl.numInternalNodes for nl in nodeSet]),
                                  mpi.SUM)
    massScale = mPlanet/nbGlobalNodes
    timeScale = 0.1*gravTime
    dashpotParameter = cooldownPower*massScale/timeScale
    for nl in nodeSet:
        v = nl.velocity()
        m = nl.mass()
        u = nl.specificThermalEnergy()
        if cooldownMethod == 'dashpot':
            for k in range(nl.numInternalNodes):
                v[k] *= 1.0 - min(dashpotParameter*dt/m[k], 1)
                u[k] *= 0.0 #TODO: maybe improve this
                pass
            pass
        elif cooldownMethod == 'stomp':
            for k in range(nl.numInternalNodes):
                v[k] *= 1.0 - cooldownPower
                u[k] *= 0.0 #TODO maybe improve this
                pass
            pass
        pass
    pass
control.appendPeriodicWork(cooldown,cooldownFrequency)

#-------------------------------------------------------------------------------
# NAV Launch simulation
# The simulation can be run for a specified number of steps, or a specified time
# in seconds.
#-------------------------------------------------------------------------------
if not steps is None:
    control.step(steps)
    control.dropRestartFile()
else:
    control.advance(goalTime, maxSteps)
    control.dropRestartFile()
    control.dropViz()

#-------------------------------------------------------------------------------
# NAV Post processing tasks
# Here we can include tasks that will happen once, if and when the run is completed
# successfully. Things like saving flattened node lists and/or computed quantities.
#-------------------------------------------------------------------------------
# Save final state in a flattened node list (.fnl) file.
mOutput(control.totalSteps, control.time(), control.lastDt())

# Print current planet's vitals and compare to expected solution.
if polytrope_n == 1:
    # Approximate planet's vitals via nearest node
    mdict = shelpers.spickle_node_list(planet,silent=True)
    plan_arr = max([hypot(x[0],hypot(x[1],x[2])) for x in mdict['x']])
    plan_arr += max([max(x) for x in mdict['h']])
    plan_rho = max(mdict['rho'])
    plan_pee = max(mdict['p'])
    # Calculate derived polytrope vitals
    alfa = sqrt(polytrope_K/(2*pi*G))
    poly_arr = pi*alfa
    poly_rho = mPlanet/(4.0/3.0*pi*poly_arr**3) * (pi**2/3.0)
    poly_pee = polytrope_K * poly_rho**2
    cout = sys.stdout.write
    cout("\nbenchmark report card\n".upper())
    cout("               | Planet     | n=1 polytrope | \n")
    cout("R [m]          | {:.4e} | {:.4e}    | \n".format(plan_arr,poly_arr))
    cout("rho_c [kg/m^3] | {:.4e} | {:.4e}    | \n".format(plan_rho,poly_rho))
    cout("P_c [Pa]       | {:.4e} | {:.4e}    | \n".format(plan_pee,poly_pee))


#-------------------------------------------------------------------------------
# NAV Final thoughts
# Here we may print a message if desired, or do any final action.
#-------------------------------------------------------------------------------
print "\n", jobName.upper(), "completed."
