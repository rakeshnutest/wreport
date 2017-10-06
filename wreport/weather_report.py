# Copyright (c) 2015 Nutanix Inc.  All rights reserved.
#
# Aurthor: Dan.Small@nutanix.com
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

from wreport.checks import cpu
from wreport.checks import health
from wreport.checks import metadata
from wreport.checks import oplog
from wreport.checks import storage


# Allows you to pass instance methods to processes.
def _pickle_method(method):
  if method.im_self is None:
    return getattr, (method.im_class, method.im_func.func_name)
  else:
    return getattr, (method.im_self, method.im_func.func_name)
copy_reg.pickle(types.MethodType, _pickle_method)


class WeatherReport(object):
  """Methods for executing checks and accessing their results."""
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

  def __init__(self, data_collection, proc_cnt=None, regen=False):
    """Create a Weather Report for a specfic data_collection.

    Args:
      data_collection: The path to the consolidated collect_perf data.
      proc_cnt: The number of processes to use when running checks. If None, all
        checks will be executed in a single thread.
      regen: Whether or not to regenerate the results if they already exist.
    """
    self._dc_path = data_collection
    self.cluster = xcluster.Cluster(data_collection=self._dc_path)
    self._pickled_results_path = os.path.join(self._dc_path, "wreport.p")
    self._proc_cnt = proc_cnt
    self._info = None
    # Try to read pickled data if there or regenerate it.
    if regen or not os.path.isfile(self._pickled_results_path):
      self._raw_results = None
    else:
      with open(self._pickled_results_path, "r") as pickled_wreport:
        self._raw_results = pickle.load(pickled_wreport)

  @property
  def info(self):
    """Return a dictionary of pertinent cluster information."""
    info = dict(cluster_id=self.cluster.cluster_id,
                cluster_name=self.cluster.cluster_name,
                aos_ver=self.cluster.release_version[:45],
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
    print "AOS Release: {0}".format(self.cluster.release_version[:45])
    print "{0} Nodes - {1} UVMs".format(
        len(self.cluster.nodes), len(self.cluster.vms))
    print "Hot/Cold Tier Size: {0} / {1}".format(
        self.cluster.hot_tier_size, self.cluster.cold_tier_size)

  @property
  def results(self):
    """Return a dictionry of results that are grouped by the check name.

    Checks that passed are filtered out.
    """
    # This is the primary use case for the weather report and these results are
    # intended to be passed to a jinja2 template.
    grouped_dict = {}
    # The raw results are a list of nested dictionaries.
    for obj_results_dict in self.raw_results:
      for obj_id, results_dict in obj_results_dict.items():
        # The results_dict is nested dictionary keyed by test name.
        for check_name, result in results_dict.items():
          # Filter out checks that passed.
          if result["status"] == 0:
            continue
          if check_name not in grouped_dict.keys():
            grouped_dict[check_name] = {}
          grouped_dict[check_name][obj_id] = result
    # Adds the title and documentation to the checks.
    for check in self._VDISK_CHECKS + self._VM_CHECKS + self._NODE_CHECKS + \
        self._CLUSTER_CHECKS:
      if check.__name__ in grouped_dict.keys():
        grouped_dict[check.__name__]["title"] = check.TITLE
        grouped_dict[check.__name__]["doc_link"] = check.DOC
    return grouped_dict

  @property
  def raw_results(self):
    """Runs and returns a list of dicts containing all unadulterated results."""
    if self._raw_results is None:
      if self._proc_cnt is not None:
        pool = mp.Pool(processes=self._proc_cnt)
        self._raw_results = pool.map(
            self._check_vdisk, self.cluster.vdisks.values())
        # self._raw_results.extend(
        #     pool.map(self._check_vm, self.cluster.vms.values()))
        self._raw_results.extend(
            pool.map(self._check_node, self.cluster.nodes.values()))
        pool.close()
        pool.join()
      else:
        self._raw_results = [self._check_vdisk(vdisk) for vdisk in \
            self.cluster.vdisks.values()]
        # self._raw_result.extend(
        #     [self._check_vms) for vm in self.cluster.vms.values()])
        self._raw_result.extend(
            [self._check_nodes(node) for node in self.cluster.nodes.values()])
      # Save our work.
      with open(self._pickled_results_path, "w") as pickled_wreport:
        pickle.dump(self._raw_results, pickled_wreport)
    return self._raw_results

  def _check_vdisk(self, vdisk):
    """Run all VDisk checks against an instance and return a dict of results.

    Args:
      vdisk: A gnosis.explore.vdisk.VDisk object.
    """
    checks = [check(vdisk) for check in self._VDISK_CHECKS]
    return {vdisk.vdisk_id : self._run_checks(checks)}

  def _check_vm(self, vm):
    """Run all VM checks against an instance and return a dict of results.

    Args:
      vm: A gnosis.explore.vm.Vm object.
    """
    checks = [check(vm) for check in self._VM_CHECKS]
    return {vm.name : self._run_checks(checks)}

  def _check_node(self, node):
    """Run all Node checks against an instance and return a dict of results.

    Args:
      node: A gnosis.explore.node.Node object.
    """
    checks = [check(node) for check in self._NODE_CHECKS]
    return {node.cvm_ip : self._run_checks(checks)}

  def _run_checks(self, checks):
    """Run a list of checks.

    Args:
      checks: A list of instantiated check instances.
    """
    result = {}
    for check in checks:
      try:
        check_result = check.run_check()
      except ZeroDivisionError:
        # Assumes no activity and defaults to pass.
        check_result = {"status" : 0, "criteria" : None}
      except Exception as e:
        # TODO: logging
        # 3 is Unknown
        check_result = {"status" : 3, "criteria" : "UNKNOWN", "exception" : e}
      result[check.__class__.__name__] = check_result
    return result

  def print_results(self):
    """Prettily prints the results."""
    for check, check_results in self.results.items():
      print check
      for obj, result in check_results.items():
        if obj == "doc_link":
          continue
        if isinstance(result, list):
          print "\t{0}: {1}".format(obj, "\n".join(result["criteria"]))
        elif isinstance(result, dict):
          print "\t{0}: {1}".format(obj, result["criteria"])
      print

if __name__ == "__main__":
  # limit default process count.
  PROC_COUNT = mp.cpu_count() / 2
  if PROC_COUNT < 1:
    PROC_COUNT = 1

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
    # This property will execute the checks if needed.
    results = report.raw_results
  else:
    report.print_info()
    print
    report.print_results()

