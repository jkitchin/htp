#!/usr/bin/env python
from ase import *
from ase.calculators.jacapo import *

from htp.remote_dacapo import *

Jacapo.calculate = remote_dacapo
Jacapo.qsuboptions = '-l cput=23:59:00,mem=100mb'

co = Atoms([Atom('C',[0,0,0]),
            Atom('O',[1.2,0,0])],
            cell=(6.,6.,6.))

calc = Jacapo('1.2.1.1-co.nc',   #output filename
              nbands=6,
              pw=350,    
              ft=0.01,
              atoms=co)   

print co.get_potential_energy()
print co.get_forces()
