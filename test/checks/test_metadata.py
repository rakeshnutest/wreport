# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock
import pandas as pd

from gnosis.utils import AttrDict
from wreport.checks import metadata


class TestNodeMedusaLatCost(unittest.TestCase):
  def test_low_r_high_contrib(self):
    fake_data = [dict(timestamp="some_dt", stage="VdiskBlockmapLookupDone", 
                      avglatency_us=1000, latencypct_oftotal=50,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                 dict(timestamp="some_dt", stage="EgroupFinderOpDone",
                      avglatency_us=1000, latencypct_oftotal=30,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                  dict(timestamp="some_dt", stage="start",
                       avglatency_us=1000, atencypct_oftotal=20,
                       host="some_ip", op_type="nfs_reads",
                       component="vdisk_controller")]
    fake_obj = AttrDict(cvm_ip="some_ip", datasets=AttrDict(
        stargate_latency=AttrDict(df=pd.DataFrame(fake_data))))
    chk = metadata.NodeMedusaLatCost(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_high_r_low_contrib(self):
    fake_data = [dict(timestamp="some_dt", stage="VdiskBlockmapLookupDone", 
                      avglatency_us=10000, latencypct_oftotal=5,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                 dict(timestamp="some_dt", stage="EgroupFinderOpDone",
                      avglatency_us=10000, latencypct_oftotal=3,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                  dict(timestamp="some_dt", stage="start",
                       avglatency_us=1000, atencypct_oftotal=20,
                       host="some_ip", op_type="nfs_reads",
                       component="vdisk_controller")]
    fake_obj = AttrDict(cvm_ip="some_ip", datasets=AttrDict(
        stargate_latency=AttrDict(df=pd.DataFrame(fake_data))))
    chk = metadata.NodeMedusaLatCost(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    fake_data = [dict(timestamp="some_dt", stage="VdiskBlockmapLookupDone", 
                      avglatency_us=5000, latencypct_oftotal=20,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                 dict(timestamp="some_dt", stage="EgroupFinderOpDone",
                      avglatency_us=5000, latencypct_oftotal=10,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                  dict(timestamp="some_dt", stage="start",
                       avglatency_us=1000, atencypct_oftotal=20,
                       host="some_ip", op_type="nfs_reads",
                       component="vdisk_controller")]
    fake_obj = AttrDict(cvm_ip="some_ip", datasets=AttrDict(
        stargate_latency=AttrDict(df=pd.DataFrame(fake_data))))
    chk = metadata.NodeMedusaLatCost(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_investigate(self):
    fake_data = [dict(timestamp="some_dt", stage="VdiskBlockmapLookupDone", 
                      avglatency_us=5000, latencypct_oftotal=20,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                 dict(timestamp="some_dt", stage="EgroupFinderOpDone",
                      avglatency_us=5000, latencypct_oftotal=20,
                      host="some_ip", op_type="nfs_reads",
                      component="vdisk_controller"),
                  dict(timestamp="some_dt", stage="start",
                       avglatency_us=1000, atencypct_oftotal=20,
                       host="some_ip", op_type="nfs_reads",
                       component="vdisk_controller")]
    fake_obj = AttrDict(cvm_ip="some_ip", datasets=AttrDict(
        stargate_latency=AttrDict(df=pd.DataFrame(fake_data))))
    chk = metadata.NodeMedusaLatCost(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)

