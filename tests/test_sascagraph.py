import pytest
from scale.attacks import SASCAGraph
import numpy as np
import os

def test_table():
    """
    Test Table lookup
    """
    fgraph = "graph_t.txt"
    nc = 16
    n = 100
    table = np.random.permutation(nc).astype(np.uint32)
    distri_x = np.random.randint(1,2048,(n,nc))
    distri_x = (distri_x.T / np.sum(distri_x,axis=1)).T

    with open(fgraph, "w") as fp:
        fp.write("""
PROPERTY y = table[x]
TABLE table
VAR MULTI x
VAR MULTI y
""")
    graph = SASCAGraph(fgraph,nc,n)
    graph.set_table("table",table)
    graph.set_distribution("x",distri_x)

    graph.run_bp(1)
    distri_y = graph.get_distribution("y")
    
    distri_y_ref = np.zeros(distri_x.shape)
    for x in range(nc):
        y = table[x]
        distri_y_ref[:,y] = distri_x[:,x]

    assert np.allclose(distri_y_ref,distri_y)
    os.remove(fgraph)

def test_xor_public():
    """
    Test XOR with public data
    """
    fgraph = "graph_xp.txt"
    nc = 16
    n = 100
    public = np.random.randint(0,nc,n,dtype=np.uint32)
    distri_x = np.random.randint(1,100,(n,nc))
    distri_x = (distri_x.T / np.sum(distri_x,axis=1)).T

    with open(fgraph, "w") as fp:
        fp.write("""
PROPERTY y = x ^ p
VAR MULTI y
VAR MULTI x
VAR MULTI p
""")
    graph = SASCAGraph(fgraph,nc,n)
    graph.set_public("p",public)
    graph.set_distribution("x",distri_x)

    graph.run_bp(1)

    distri_y = graph.get_distribution("y")
    distri_y_ref = np.zeros(distri_x.shape)
    for x in range(nc):
        y = x ^ public
        distri_y_ref[np.arange(n),y] = distri_x[np.arange(n),x]

    assert np.allclose(distri_y_ref,distri_y)
    os.remove(fgraph)

def test_xor():
    """
    Test XOR between distributions
    """
    fgraph = "graph_x.txt"
    nc = 16
    n = 100
    distri_x = np.random.randint(1,100,(n,nc))
    distri_x = (distri_x.T / np.sum(distri_x,axis=1)).T
    distri_y = np.random.randint(1,100,(n,nc))
    distri_y = (distri_y.T / np.sum(distri_y,axis=1)).T

    with open(fgraph, "w") as fp:
        fp.write("""
PROPERTY z = x^y
VAR MULTI x
VAR MULTI y
VAR MULTI z""")

    graph = SASCAGraph(fgraph,nc,n)
    graph.set_distribution("x",distri_x)
    graph.set_distribution("y",distri_y) 

    graph.run_bp(1)
    distri_z = graph.get_distribution("z")
    
    distri_z_ref = np.zeros(distri_z.shape)
    for x in range(nc):
        for y in range(nc):
            distri_z_ref[:,x^y] += distri_x[:,x] * distri_y[:,y]

    assert np.allclose(distri_z_ref,distri_z)
    os.remove(fgraph)
