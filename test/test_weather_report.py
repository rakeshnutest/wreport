# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock

from gnosis.utils import AttrDict
from wreport import weather_report as wrpt


# This is not a unittest for the Tasks object, rather, a safe-gaurd to ensure
# things are added to that queue appropriately.
class TestTASKS(unittest.TestCase):
  def setUp(self):
    self.tasks = wrpt.TASKS.get_tasks()

  def test_task_levels(self):
    self.assertIn(0, self.tasks.keys())
    self.assertIn(1, self.tasks.keys())
    self.assertTrue(all([type(key) == int for key in self.tasks.keys()]))

  def test_tasks_list(self):
    chks = ["VDisk", "VM", "Node", "Cluster"]
    chk_names = []
    for lvl in self.tasks.values():
      for chk in lvl:
        chk_names.append(chk.name())
    self.assertTrue(all([chk_name in chks for chk_name in chk_names]))


# The CheckVDisk, CheckNode, and CheckVM classes all have a generator method
# that yields a task for each of the respective objects being checked (vdisk,
# node, vm).
class TestGetJobs(unittest.TestCase):
  @mock.patch("gnosis.explore.cluster.Cluster")
  def test_CheckNode(self, mock_Cluster):
    mock_Cluster.return_value = AttrDict(
        nodes=dict(n1="node_obj", n2="node_obj"))
    self.assertEqual(len(
        [node for node in wrpt.CheckNode.get_jobs("some_path")]), 2)

  @mock.patch("gnosis.explore.cluster.Cluster")
  def test_CheckVM(self, mock_Cluster):
    mock_Cluster.return_value = AttrDict(
        vms=dict(vm1="vm_obj", vm2="vm_obj"))
    self.assertEqual(len(
        [vm for vm in wrpt.CheckVM.get_jobs("some_path")]), 2)

  @mock.patch("gnosis.explore.cluster.Cluster")
  def test_CheckVDisk(self, mock_Cluster):
    mock_Cluster.return_value = AttrDict(
        vdisks=dict(vdisk_1="vdisk_obj", vdisk_2="vdisk_obj"))
    self.assertEqual(len(
        [vdisk for vdisk in wrpt.CheckVDisk.get_jobs("some_path")]), 2)


class TestWeatherReport(unittest.TestCase):
  def setUp(self):
    cluster_patcher = mock.patch("gnosis.explore.cluster.Cluster",
                                 return_value={})
    self.mock_cluster = cluster_patcher.start()
    self.wrpt = wrpt.WeatherReport("/some/path")
    self.wrpt._raw_results = [
        {"obj_0" : {"all_good": {"status" : 0}}},
        {"obj_0" : {"all_unknown": {"status" : 3}}},
        {"obj_0" : {"all_interesting": {"status" : 1}}},
        {"obj_0" : {"all_investigate": {"status" : 2}}},
        {"obj_0" : {"mix_good_unknown": {"status" : 0}}},
        {"obj_0" : {"mix_good_interesting": {"status" : 0}}},
        {"obj_0" : {"mix_good_investigate": {"status" : 0}}},
        {"obj_0" : {"mix_interesting_investigate": {"status" : 1}}},
        {"obj_1" : {"all_good": {"status" : 0}}},
        {"obj_1" : {"all_unknown": {"status" : 3}}},
        {"obj_1" : {"all_interesting": {"status" : 1}}},
        {"obj_1" : {"all_investigate": {"status" : 2}}},
        {"obj_1" : {"mix_good_unknown": {"status" : 3}}},
        {"obj_1" : {"mix_good_interesting": {"status" : 1}}},
        {"obj_1" : {"mix_good_investigate": {"status" : 2}}},
        {"obj_1" : {"mix_interesting_investigate": {"status" : 2}}}]

  def test_init(self):
    self.assertEqual(self.wrpt._dc_path, "/some/path")
    self.assertEqual(self.wrpt._pickled_results_path, "/some/path/wreport.p")

  # The group results method will group results by check, where each object has
  # a status.
  @mock.patch("wreport.weather_report.WeatherReport")
  def test_group_results(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(isinstance(grp_res, dict))
    chk_groups = ["all_good", "all_unknown", "all_interesting",
                  "all_investigate", "mix_good_unknown", "mix_good_interesting",
                  "mix_good_investigate", "mix_interesting_investigate"]
    self.assertTrue(all([key in chk_groups for key in grp_res.keys()]))
    chk_dict_keys = ["obj_0", "obj_1", "status_list", "group_status"]
    for chk_dict in grp_res.values():
      self.assertTrue(all([key in chk_dict_keys for key in chk_dict.keys()]))

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_all_good(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["all_good"]["group_status"] == 0)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_all_interesting(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["all_interesting"]["group_status"] == 1)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_all_investigate(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["all_investigate"]["group_status"] == 2)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_all_unknown(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["all_unknown"]["group_status"] == 3)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_mix_good_unknown(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["mix_good_unknown"]["group_status"] == 0)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_mix_good_interesting(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["mix_good_interesting"]["group_status"] == 1)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_mix_good_investigate(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["mix_good_investigate"]["group_status"] == 2)

  @mock.patch("wreport.weather_report.WeatherReport")
  def test_grp_res_mix_interesting_investigate(self, mock_WeatherReport):
    grp_res = self.wrpt._group_results()
    self.assertTrue(grp_res["mix_interesting_investigate"]["group_status"] == 2)
