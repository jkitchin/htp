#!/usr/bin/env python
from ase import *
from ase.calculators.jacapo import *

from htp.remote_qn import *

Jacapo.calculate = remoteQN
Jacapo.qsuboptions = '-l cput=23:59:00,mem=100mb'
Jacapo.qnrelax_tags = [1]

co = Atoms([Atom('C',[0,0,0],tag=1),
            Atom('O',[1.2,0,0],tag=1)],
            cell=(6.,6.,6.))

calc = Jacapo('co-qn.nc',   #output filename
              nbands=6,
              pw=350,    
              ft=0.01,
              atoms=co)   

print co.get_potential_energy()
print co.get_forces()
