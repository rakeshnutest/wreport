# Copyright (c) 2018 Nutanix Inc. All rights reserved.
#
# Author: dan.small@nutanix.com
#
import unittest

import mock

from gnosis.explore import cluster as xcluster
from wreport import weather_report as wrpt


# The weather report modules adds WReportTask objects to a dictionary based on
# level.  Level-0 for parallelizable tasks, level-0 for non-parallelizable.
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
    self.assertTrue(all([chk_name in chks for chk_name in chk_names])


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
