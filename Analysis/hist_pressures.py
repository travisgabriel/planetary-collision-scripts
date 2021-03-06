#! /proj/nmovshov_hindmost/collisions/SPHERAL/bin/python
#-------------------------------------------------------------------------------
# Quick histogram of pressure values of nodes read from .fnl file.
#-------------------------------------------------------------------------------
import sys, os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
pcsbase = '' # Edit this with full path to <pcs> if you see an ImportError.
sys.path += ['..',pcsbase,os.getenv('PCSBASE','')]
import shelpers

if len(sys.argv)==1:
    sys.exit("Please provide file name as first parameter")

nodes = np.loadtxt(sys.argv[1])
if (nodes.ndim != 2) or (nodes.shape[1] != shelpers.nb_fnl_columns):
    sys.exit("{} does not appear to contain a valid flattened node list".format(
             sys.argv[1]))

print "Plotting nodes from file", sys.argv[1]
P = nodes[:,10] * 1e-9 # pressure in GPa

plt.figure()
plt.hist(P,)
plt.xlabel('Pressure [GPa]')
plt.ylabel('Count')
plt.title(sys.argv[1])
plt.grid()
plt.show()
print "Done."

