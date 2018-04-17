# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock
import pandas as pd

from gnosis.utils import AttrDict
from wreport.checks import oplog


class TestNodeBusyOplogCount(unittest.TestCase):
  def test_good_all_low_usage(self):
    # Simulated two samples, two VDisks, low usage.
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=1000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=1000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=1000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=1000)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.NodeBusyOplogCount(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_good_one_disk_low_freq(self):
    # Simulated four samples, one VDisks, high usage, low frequency.
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=500000000),
                 dict(timestamp="dt_2", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=500000000),
                 dict(timestamp="dt_3", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=500000000)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.NodeBusyOplogCount(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_good_many_high_usage(self):
    # Simulated one samples, five VDisks, high usage.
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_2",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_3",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_4",
                      counter="oplog_bytes", value=6000000000)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.NodeBusyOplogCount(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    # Simulated one samples, four VDisks, high usage.
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_2",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_3",
                      counter="oplog_bytes", value=6000000000)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.NodeBusyOplogCount(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_investigate_high_freq(self):
    # Simulated four samples, one VDisks, high usage for 1/2.
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=5000000000),
                 dict(timestamp="dt_2", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_3", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=5000000000)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.NodeBusyOplogCount(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)


class TestVDiskLogicalOplogLimit(unittest.TestCase):
  def test_investigate(self):
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=6000000000)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.VDiskLogicalOplogLimit(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_investigate(self):
    fake_data = [dict(timestamp="dt_0", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=612032839680),
                 dict(timestamp="dt_0", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=1000000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_0",
                      counter="oplog_bytes", value=6000000000),
                 dict(timestamp="dt_1", component="vdisk", instance="vdisk_1",
                      counter="oplog_bytes", value=612032839680)]
    fake_obj = AttrDict(
        datasets=AttrDict(hvars=AttrDict(df=pd.DataFrame(fake_data))),
        gflags=AttrDict(vdisk_distributed_oplog_max_dirty_MB="6144"))
    chk = oplog.VDiskLogicalOplogLimit(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)

