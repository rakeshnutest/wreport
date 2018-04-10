# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock
import pandas as pd

from gnosis.utils import AttrDict
from wreport.checks import health


class TestNodeStargateRestarts(unittest.TestCase):
  def test_good(self):
    fake_obj = AttrDict(stargate_start_times=["some_date"])
    chk = health.NodeStargateRestarts(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_investigate(self):
    fake_obj = AttrDict(stargate_start_times=["some_date", "another"])
    chk = health.NodeStargateRestarts(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)

