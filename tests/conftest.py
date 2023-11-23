import os
import numpy as np
import random

import pytest


@pytest.fixture(autouse=True)
def seed_random():
    init1 = 73848304  # random.SystemRandom().randrange(0, 2**32) random.seed(73848304); np.random.seed(3992167176)
    init2 = 3992167176  # random.SystemRandom().randrange(0, 2**32)
    print(f"Random seeds: random.seed({init1}); np.random.seed({init2})")
    random.seed(init1)
    np.random.seed(init2)
