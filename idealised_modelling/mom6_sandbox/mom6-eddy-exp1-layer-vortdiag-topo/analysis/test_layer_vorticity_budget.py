"""Manufactured Cartesian circulation tests, including unequal grid spacing."""
import numpy as np
from layer_vorticity_budget import curl


def test_rotation_and_gradient():
    n, dx, dy = 8, 5., 7.
    xh, yh = (np.arange(n)+.5)*dx, (np.arange(n)+.5)*dy
    area = np.full((n+1,n+1),dx*dy)
    def faces(a,b):
        return (np.broadcast_to(a*yh[:,None],(n,n+1)),
                np.broadcast_to(b*xh[None,:],(n+1,n)))
    u,v=faces(-2.,3.)
    actual=curl(u,v,dx,dy,area)
    np.testing.assert_allclose(actual[1:-1,1:-1],5.)
    assert np.isnan(actual[0]).all() and np.isnan(actual[:,-1]).all()
    # Gradient of phi=x*y: both derivatives are nonzero and cancel.
    u,v=faces(1.,1.)
    np.testing.assert_allclose(curl(u,v,dx,dy,area)[1:-1,1:-1],0.,atol=1e-15)
