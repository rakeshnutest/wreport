#!/usr/bin/env python
# Copyright (c) 2015-2017 Nutanix Inc.  All rights reserved.
#
# Aurthor: Dan.Small@nutanix.com, GDowding@nutanix.com
#
"""The Weather Report tool.

The Weather Report is a tool that runs various performance related checks in
an effort to identify common issues that have a known impact on performance.
"""
import argparse
import copy_reg
import multiprocessing as mp
import os
import pickle
import types

from gnosis.explore import cluster as xcluster

from wreport import task
from wreport.checks import cpu
from wreport.checks import health
from wreport.checks import metadata
from wreport.checks import oplog
from wreport.checks import storage

# ------------------------------------------------------------------------------
# The checks to perform based on their respecitve objects.
_VDISK_CHECKS = [storage.VDiskColdTierReads]
_VM_CHECKS = []
_NODE_CHECKS = [health.NodeStargateRestarts,
                oplog.NodeBusyOplogCount,
                oplog.VDiskLogicalOplogLimit,
                metadata.NodeMedusaLatCost,
                cpu.NodeHostCpuUtil,
                cpu.NodeHostCpuUtilInbalance,
                cpu.NodeCvmCpuReady,
                cpu.NodeCvmCpuUsage]
_CLUSTER_CHECKS = []
# ------------------------------------------------------------------------------
# Global task container.
TASKS = task.Tasks()
# Limit default process count. Used when called as script.
PROC_COUNT = mp.cpu_count() / 2
if PROC_COUNT < 1:
  PROC_COUNT = 1

# Allows you to pass instance methods to processes.
# pylint: disable=no-else-return
def _pickle_method(method):
  if method.im_self is None:
    return getattr, (method.im_class, method.im_func.func_name)
  else:
    return getattr, (method.im_self, method.im_func.func_name)
copy_reg.pickle(types.MethodType, _pickle_method)


@TASKS.add_task(0)
class CheckVDisk(task.WReportTask):
  """Methods for executing checks against a VDisk object."""

  _name = "VDisk"

  def __init__(self, vdisk):
    """Initialize a task to run checks."""
    self.vdisk = vdisk
    self._result = {}

  def run(self):
    """Execute the VDisk checks."""
    checks = [check(self.vdisk) for check in _VDISK_CHECKS]
    self._result = self._run_checks(checks)

  def result(self):
    """Return the result of the task."""
    return {self.vdisk.uuid : self._result}

  @classmethod
  def get_jobs(cls, data_collection):
    """Get the jobs for checking a VDisks.

    This generator will return a job for each VDisk object within the cluster.

    Args:
      data_collection: The data path.
    """
    cluster = xcluster.Cluster(data_collection=data_collection)
    for vdisk in cluster.vdisks.values():
      yield CheckVDisk(vdisk)


@TASKS.add_task(0)
class CheckVM(task.WReportTask):
  """Methods for executing checks against a VM object."""

  _name = "VM"

  def __init__(self, vm):
    """Initialize a task to run checks."""
    self.vm = vm
    self._result = {}

  def run(self):
    """Execute the VM checks."""
    checks = [check(self.vm) for check in _VM_CHECKS]
    self._result = self._run_checks(checks)

  def result(self):
    """Return the result of the task."""
    return {self.vm.name : self._result}

  @classmethod
  def get_jobs(cls, data_collection):
    """Get the jobs for checking a VM.

    This generator will return a job for each VM object within the cluster.

    Args:
      data_collection: The data path.
    """
    cluster = xcluster.Cluster(data_collection=data_collection)
    for vm in cluster.vms.values():
      yield CheckVM(vm)


@TASKS.add_task(0)
class CheckNode(task.WReportTask):
  """Methods for executing checks against a Node object."""

  _name = "Node"

  def __init__(self, node):
    """Initialize a task to run checks."""
    self.node = node
    self._result = {}

  def run(self):
    """Execute the Node checks."""
    checks = [check(self.node) for check in _NODE_CHECKS]
    self._result = self._run_checks(checks)

  def result(self):
    """Return the result of the task."""
    return {self.node.cvm_ip : self._result}

  @classmethod
  def get_jobs(cls, data_collection):
    """Get the jobs for checking a Node.

    This generator will return a job for each Node object within the cluster.

    Args:
      data_collection: The data path.
    """
    cluster = xcluster.Cluster(data_collection=data_collection)
    for node in cluster.nodes.values():
      yield CheckNode(node)

@TASKS.add_task(1)
class CheckCluster(task.WReportTask):
  """Methods for executing checks against the cluster.

  Some of these may be dependent on Node, VM, or VDisk checks, so they should be
  ran after those checks.
  """

  _name = "Cluster"

  def __init__(self, data_collection):
    """Initialize a task to run checks."""
    self.cluster = xcluster.Cluster(data_collection=data_collection)
    self._result = {}

  def run(self):
    """Execute the Cluster checks."""
    checks = [check(self.cluster) for check in _CLUSTER_CHECKS]
    self._result = self._run_checks(checks)

  def result(self):
    """Return the result of the task."""
    return {"Cluster" : self._result}


class WeatherReport(object):
  """Methods for executing checks and accessing their results."""


  def __init__(self, data_collection, proc_cnt=None, regen=False):
    """Create a Weather Report for a specfic data_collection.

    Args:
      data_collection: The path to the consolidated collect_perf data.
      proc_cnt: The number of processes to use when running checks. If None or
        1, all checks will be executed in a single thread.
      regen: Whether or not to regenerate the results if they already exist.
    """
    self._dc_path = data_collection
    self.cluster = xcluster.Cluster(data_collection=self._dc_path)
    self._pickled_results_path = os.path.join(self._dc_path, "wreport.p")
    self._proc_cnt = proc_cnt
    self._info = None
    # Try to read pickled data if there or regenerate it.
    if regen or not os.path.isfile(self._pickled_results_path):
      self._raw_results = []
    else:
      with open(self._pickled_results_path, "r") as pickled_wreport:
        self._raw_results = pickle.load(pickled_wreport)

  # pylint: disable=no-self-use
  def _process_job(self, job):
    """Executation wrapper for Running a job."""
    job.run()
    return job.result()

  def _job_callback(self, result):
    """Callback used by jobs to update the results."""
    self._raw_results.append(result)

  @property
  def raw_results(self):
    """Runs and returns a list of dicts containing all unadulterated results."""
    if not self._raw_results:
      tasks = TASKS.get_tasks()
      for level in sorted(tasks.keys()):
        if self._proc_cnt is not None and self._proc_cnt > 1:
          pool = mp.Pool(processes=self._proc_cnt)
          for task_obj in tasks[level]:
            for job in task_obj.get_jobs(self._dc_path):
              pool.apply_async(
                  self._process_job, (job,), callback=self._job_callback)
          pool.close()
          pool.join()
        else:
          for task_obj in tasks[level]:
            for job in task_obj.get_jobs(self._dc_path):
              job.run()
              self._raw_results.append(job.result())
      # Save our work.
      with open(self._pickled_results_path, "w") as pickled_wreport:
        pickle.dump(self._raw_results, pickled_wreport)
    return self._raw_results

  @property
  def info(self):
    """Return a dictionary of pertinent cluster information."""
    info = dict(cluster_id=self.cluster.cluster_id,
                cluster_name=self.cluster.cluster_name,
                aos_ver=str(self.cluster.release_version)[:45],
                node_count=len(self.cluster.nodes),
                hot_tier_size=self.cluster.hot_tier_size,
                cold_tier_size=self.cluster.cold_tier_size,
                vm_count=len(self.cluster.vms),
                dc_path=self._dc_path)
    return info

  def print_info(self):
    """Print cluster information."""
    print "Cluster ID: {0} - Name: {1}".format(
        self.cluster.cluster_id, self.cluster.cluster_name)
    print "AOS Release: {0}".format(str(self.cluster.release_version)[:45])
    print "{0} Nodes - {1} UVMs".format(
        len(self.cluster.nodes), len(self.cluster.vms))
    print "Hot/Cold Tier Size: {0} / {1}".format(
        self.cluster.hot_tier_size, self.cluster.cold_tier_size)

  def _group_results(self):
    """Group the raw results by name and determine the overall status code.

    Group Status Codes:
      3: The check failed against all objects. This is likely a systemic data or
        code related issue.
      2: The test executed and at least one object warrents further
        investigation.
      1: The test executed and at least one object was flagged as interesting.
        This status is also used when some objets failed to execute while others
        passed. When this occures it it likely the result of that specific
        objects data set instead of a systemic data or test issue.
      0: The test executed and all objects tested passed, or some passed while
        others threw an exception.
    """
    grouped_dict = {}
    # The raw results are a list of nested dictionaries.
    for obj_results_dict in self.raw_results:
      for obj_id, results_dict in obj_results_dict.items():
        # The results_dict is nested dictionary keyed by test name.
        for check_name, result in results_dict.items():
          if check_name not in grouped_dict.keys():
            grouped_dict[check_name] = {"status_list" : []}
          grouped_dict[check_name]["status_list"].append(result["status"])
          grouped_dict[check_name][obj_id] = result
    for results_dict in grouped_dict.values():
      results_dict["group_status"] = max(results_dict["status_list"])
      # Complete failure of test across all objects.
      if all([status == 3 for status in results_dict["status_list"]]):
        results_dict["group_status"] = 3
      # At least one object was found to be worth investigation.
      elif any([status == 2 for status in results_dict["status_list"]]):
        results_dict["group_status"] = 2
      # At least one object was found to be interesting.
      elif any([status == 1 for status in results_dict["status_list"]]):
        results_dict["group_status"] = 1
      # Everything passed, or some threw an exception. This can happen when data
      # is missing form some objects, e.g., a node without vdisks data in hvars.
      else:
        results_dict["group_status"] = 0
    return grouped_dict

  def get_results(self, status_filter=None):
    """Return a filtered dict of results that are grouped by the check name.

    Args:
      status_filter (list): Only return results with these status codes.
    """
    grouped_dict = self._group_results()
    # Maybe filter results.
    if status_filter is not None:
      for check, results_dict in grouped_dict.items():
        if results_dict["group_status"] not in status_filter:
          grouped_dict.pop(check)
        for obj, result in results_dict.items():
          if not isinstance(result, dict):
            continue
          if result["status"] not in status_filter:
            results_dict.pop(obj)
    # Adds the title and documentation to the checks.
    for check in _VDISK_CHECKS + _VM_CHECKS + _NODE_CHECKS + _CLUSTER_CHECKS:
      if check.__name__ in grouped_dict.keys():
        grouped_dict[check.__name__]["title"] = check.TITLE
        grouped_dict[check.__name__]["doc"] = check.DOC
    return grouped_dict

  def print_results(self):
    """Prettily prints the results."""
    for check, check_results in self.get_results().items():
      if check_results["group_status"] == 0:
        print "{0}: No Issues Found".format(check)
        continue
      elif check_results["group_status"] == 3:
        print "{0}: All Unknown".format(check)
        continue
      print check
      for obj, result in check_results.items():
        if obj == "doc":
          continue
        if isinstance(result, dict):
          if not result.has_key("criteria"):
            continue
          if isinstance(result["criteria"], list):
            print "\t{}".format("\t".join("\n".join(result["criteria"])))
          if result["criteria"] is not None:
            print "\t{0}: {1}".format(obj, result["criteria"])
      print


def main():
  """Main function used when executing as a script."""
  parser = argparse.ArgumentParser(
      prog="Weather Report",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="The Weather Report is a tool that performs checks against a"\
      "data collection to identify known issues.",
      fromfile_prefix_chars="@")
  parser.add_argument(
      "data_collection_path",
      help="The location of the data to run the report against.")
  parser.add_argument(
      "-p", "--proc_cnt", default=PROC_COUNT,
      help="The number of processes to use.")
  parser.add_argument(
      "-r", "--regen", action="store_true",
      help="Do not rely on the saved data, instead, re-run the report.")
  parser.add_argument(
      "-q", "--quiet", action="store_true",
      help="Silently run the report.")
  args = parser.parse_args()
  report = WeatherReport(args.data_collection_path,
                         proc_cnt=int(args.proc_cnt),
                         regen=args.regen)
  if args.quiet:
    # Just execute the checks.
    report.get_results()
  else:
    report.print_info()
    print
    report.print_results()

if __name__ == "__main__":
  main()

