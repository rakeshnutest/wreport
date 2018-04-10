# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock
import pandas as pd

from gnosis.utils import AttrDict
from wreport.checks import storage


class TestVDiskColdTierReads(unittest.TestCase):
  def test_good(self):
    dates = pd.date_range("20180101", periods=4, freq="S")
    df = pd.DataFrame(index=dates)
    df["estore_hdd_kb"] = [10, 10, 10, 10]
    df["estore_ssd_kb"] = [90, 90, 90, 90]
    fake_obj = AttrDict(read_source_df=df)
    chk = storage.VDiskColdTierReads(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_interesting(self):
    dates = pd.date_range("20180101", periods=4, freq="S")
    df = pd.DataFrame(index=dates)
    df["estore_hdd_kb"] = [10, 10, 10, 30]
    df["estore_ssd_kb"] = [90, 90, 90, 70]
    fake_obj = AttrDict(read_source_df=df)
    chk = storage.VDiskColdTierReads(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 1)

  def test_interesting_low_freq(self):
    dates = pd.date_range("20180101", periods=5, freq="S")
    df = pd.DataFrame(index=dates)
    df["estore_hdd_kb"] = [10, 10, 10, 10, 30]
    df["estore_ssd_kb"] = [90, 90, 90, 90, 70]
    fake_obj = AttrDict(read_source_df=df)
    chk = storage.VDiskColdTierReads(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

  def test_investigate(self):
    dates = pd.date_range("20180101", periods=4, freq="S")
    df = pd.DataFrame(index=dates)
    df["estore_hdd_kb"] = [10, 10, 60, 60]
    df["estore_ssd_kb"] = [90, 90, 40, 40]
    fake_obj = AttrDict(read_source_df=df)
    chk = storage.VDiskColdTierReads(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 2)

  def test_investigate_low_freq(self):
    dates = pd.date_range("20180101", periods=5, freq="S")
    df = pd.DataFrame(index=dates)
    df["estore_hdd_kb"] = [10, 10, 10, 10, 60]
    df["estore_ssd_kb"] = [90, 90, 90, 90, 40]
    fake_obj = AttrDict(read_source_df=df)
    chk = storage.VDiskColdTierReads(fake_obj)
    self.assertTrue(chk.run_check()["status"] == 0)

