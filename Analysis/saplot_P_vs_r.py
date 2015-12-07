#!/soft/scipy_0.13.0/CentOS_6/bin/python
#-------------------------------------------------------------------------------
# Quick and dirty plot of pressure vs. radius of nodes read from .fnl file.
#-------------------------------------------------------------------------------
import sys, os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

if len(sys.argv)==1:
    sys.exit("ERROR: provide file name as first parameter.")

nodes = np.loadtxt(sys.argv[1])
if (nodes.ndim != 2) or (nodes.shape[1] != 15):
    sys.exit("{} does not appear to contain a valid flattened node list".format(
             sys.argv[1]))

print "Plotting nodes from file", sys.argv[1]
x = nodes[:,2]
y = nodes[:,3]
z = nodes[:,4]
r = np.sqrt(x**2 + y**2 + z**2)
P = nodes[:,10]
x = np.sort(r)
y = P[np.argsort(r)]

plt.figure()
plt.plot(x/1e3, y/1e9)
plt.xlabel('Radius [km]')
plt.ylabel('Pressure [GPa]')
plt.title(sys.argv[1])
plt.grid()
plt.show()
print "Done."
