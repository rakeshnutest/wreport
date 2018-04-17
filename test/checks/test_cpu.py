# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock
import pandas as pd

from gnosis.utils import AttrDict
from wreport.checks import cpu


class TestNodeCvmCpuUsage(unittest.TestCase):
  def test_good(self):
    fake_obj = AttrDict(cvm_cpu_count=4,
        host_cvm_cpu_util=AttrDict(pct_used=pd.Series([100, 100, 200, 100])))
    chk = cpu.NodeCvmCpuUsage(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    fake_obj = AttrDict(cvm_cpu_count=4,
        host_cvm_cpu_util=AttrDict(pct_used=pd.Series([100, 100, 300, 100])))
    chk = cpu.NodeCvmCpuUsage(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_investigate(self):
    fake_obj = AttrDict(cvm_cpu_count=4,
        host_cvm_cpu_util=AttrDict(pct_used=pd.Series([100, 100, 375, 200])))
    chk = cpu.NodeCvmCpuUsage(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)


class TestNodeCvmCpuReady(unittest.TestCase):
  def test_good(self):
    fake_obj = AttrDict(cvm_cpu_count=4,
        host_cvm_cpu_util=AttrDict(pct_ready=pd.Series([1, 1, 5, 1])))
    chk = cpu.NodeCvmCpuReady(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    fake_obj = AttrDict(cvm_cpu_count=4,
        host_cvm_cpu_util=AttrDict(pct_ready=pd.Series([1, 1, 12, 1])))
    chk = cpu.NodeCvmCpuReady(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_investigate(self):
    fake_obj = AttrDict(cvm_cpu_count=4,
        host_cvm_cpu_util=AttrDict(pct_ready=pd.Series([1, 1, 20, 1])))
    chk = cpu.NodeCvmCpuReady(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)


class TestHostCpuUtilInbalance(unittest.TestCase):
  def setUp(self):
    self.dates = pd.date_range("20180101", periods=1, freq="S")

  def test_good(self):
    # Cv of .45 and .43
    fake_obj = AttrDict(host_pcpu_util=pd.DataFrame(
        dict(zip([i for i in range(16)], [20, 20, 20, 20, 50, 50, 50, 50,
                                          50, 40, 30, 20, 10, 20, 30, 40])),
        index=self.dates))
    chk = cpu.NodeHostCpuUtilInbalance(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    # Cv of .57 and .45
    fake_obj = AttrDict(host_pcpu_util=pd.DataFrame(
        dict(zip([i for i in range(16)], [15, 15, 15, 15, 50, 50, 50, 50,
                                          20, 20, 20, 20, 50, 50, 50, 50])),
        index=self.dates))
    chk = cpu.NodeHostCpuUtilInbalance(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_investigate(self):
    # Cv of .71 and .57
    fake_obj = AttrDict(host_pcpu_util=pd.DataFrame(
        dict(zip([i for i in range(16)], [10, 10, 10, 10, 50, 50, 50, 50,
                                          15, 15, 15, 15, 50, 50, 50, 50])),
        index=self.dates))
    chk = cpu.NodeHostCpuUtilInbalance(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)


class TestNodeHostCpuUtil(unittest.TestCase):
  def setUp(self):
    self.dates = pd.date_range(20180101, periods=4, freq="S")

  def test_good(self):
    fake_obj = AttrDict(host_pcpu_util=pd.DataFrame(
        [10, 20, 30, 20], index=self.dates))
    chk = cpu.NodeHostCpuUtil(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    fake_obj = AttrDict(host_pcpu_util=pd.DataFrame(
        [10, 20, 30, 75], index=self.dates))
    chk = cpu.NodeHostCpuUtil(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_investigate(self):
    fake_obj = AttrDict(host_pcpu_util=pd.DataFrame(
        [10, 20, 30, 90], index=self.dates))
    chk = cpu.NodeHostCpuUtil(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)
 
