# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
# Various oplog_store checks.
#
# Some of these checks are technically VDisk checks, however, the data is
# sourced from a node level dataset like hvars.
from wreport.checks import base


class NodeBusyOplogCount(base.BaseCheck):
  """Counts the number of heavily utilized  VDisk oplogs for the node.

  If only one VDisk's oplog is heavily utilized it may indicate a need to split
  those VDisks into multple.  If there are more than one and four or less, it's
  likely not an issue, but something to look at.
  """
  # TODO: This should be VM aware (PERF-875 and PERF-876)
  TITLE = "Busy Oplog Check"
  DOC = "some_url"
  _MSG = "Only {0} VDisk oplog(s) are heavily utilized."
  # If only one vdisk has a busy vdisk we should look at BPGs.
  _CNT_HRD_WTRMRK = 1
  # If only four vdisks are busy it may be interesting.
  _CNT_SFT_WTRMRK = 4
  # Both usuage and sample threshold used to define busy.
  _USAGE_WTRMRK = .85
  _SAMPLE_WTRMRK = .3

  def run_check(self):
    """Check how many utilized oplogs per node exceed the watermark."""
    oplog_max = int(self._obj.gflags.vdisk_distributed_oplog_max_dirty_MB)
    # Use the hvars VDisk counters.
    df = self._obj.datasets.hvars.df
    # Filter out the stuff we care about.
    df = df[(df.component == "vdisk") &
            (df.counter == "oplog_bytes")][["instance", "value"]]
    # Group into vdisk IDs.
    groups = df.groupby("instance", axis=0)
    over_cnt = 0
    for group_name, gdf in groups:
      # Skip the total instance.
      if group_name == "total":
        continue
      # Count the number of VDisks over the usage threshold.
      over = (gdf.value.astype("float64") / 1024 ** 2 \
          > oplog_max * self._USAGE_WTRMRK).sum()
      # Look at how often this is the case.  We probably don't care about
      # isolated instances.
      if over /  float(len(gdf.value)) > self._SAMPLE_WTRMRK:
        over_cnt += 1
    if over_cnt == self._CNT_HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(over_cnt)
    elif self._CNT_HRD_WTRMRK < over_cnt <= self._CNT_SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(over_cnt)
    else:
      self.result["status"] = 0
    return self.result


class VDiskLogicalOplogLimit(base.BaseCheck):
  """Logical Oplog Limit Check."""
  TITLE = "Virtual-Disk Logical Oplog Limit"
  DOC = "some_url"
  _MSG = "VDisk ID {0}: Within {1}% of logical limit {2} times."
  _WTRMRK = .90

  def __init__(self, node):
    """Instatiate a check instance and override BaseCheck."""
    self._node = node
    # Becasue this check is using node level data to checks VDisks we'll have
    # multiple results, so we make the critera a list to append to.
    self.result = {"status" : None, "criteria" : []}

  def run_check(self):
    """Check for VDisks that come close to the watermark."""
    oplog_max = int(self._node.gflags.vdisk_distributed_oplog_max_dirty_MB)
    df = self._node.datasets.hvars.df
    df = df[(df.component == "vdisk") &
            (df.counter == "oplog_bytes")][["instance", "value"]]
    groups = df.groupby("instance", axis=0)
    for group_name, gdf in groups:
      if group_name == "total":
        continue
      over = (gdf.value.astype("float64") / 1024 ** 2 > \
          oplog_max * self._WTRMRK).sum()
      if over:
        self.result["criteria"].append(self._MSG.format(
            group_name, self._WTRMRK * 100, over))
    if len(self.result["criteria"]) > 0:
      self.result["status"] = 2
    else:
      self.result["status"] = 0
    return self.result

