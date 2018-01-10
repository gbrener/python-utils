#!/usr/bin/env python

"""
Utilities for working with prime numbers.

Should work in both Python 2 and Python 3.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import base64
import numba
import numpy as np
from six.moves import range
import subprocess



@numba.njit
def primes(n):
    """Return an array of prime numbers that are less than n. Uses the "Sieve of
    Eratosthenes" algorithm.
    """
    s = np.arange(3, n, 2)
    for m in range(3, int(n ** 0.5) + 1, 2):
        if s[(m - 3) // 2]:
            s[((m * m) - 3) // 2::m] = 0
    res = s[s > 0]
    res_cpy = np.empty(res.shape[0] + 1, s.dtype)
    res_cpy[0] = 2
    res_cpy[1:] = res
    return res_cpy



def decode(co_msg):
    """Sample usage of ``primes()``, for decoding and decrypting a string of
    data. This is a bad example of cryptography, and should not be used in
    production.
    """
    with open('msg.enc', 'wb') as fp:
        fp.write(base64.b64decode(co_msg))
    keyf = 'msg.key'
    with open(keyf, 'w') as fp:
        fp.write(str(np.sum(primes(1000))))
    msg = subprocess.check_output('openssl aes-256-cbc -d -in msg.enc -pass file:{}'.format(keyf), shell=True, universal_newlines=True)
    print(msg)
    return msg
