# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
"""Various oplog_store checks.

Some of these checks are technically VDisk checks, however, the data is
sourced from a node level dataset like hvars.
"""

from wreport.checks import base
from wreport import node_utils


class NodeBusyOplogCount(base.BaseCheck):
  """Counts the number of heavily utilized  VDisk oplogs for the node."""
  # TODO: This should be VM aware (PERF-875 and PERF-876)
  TITLE = "Busy Oplog Check"
  DOC = """The main purpose of this test is to help identify cases where
  multiple vDisks might help to improve overall write throughput capabilities. 
  The test does this by checking for VDisks that are slightly over the 
  per-vDisk oplog draining threshold. Normally, this will be 85% of the max 
  vDisk oplog allocation of 6GB. On All-Flash systems with AES, this 
  per-vDisk oplog limit might grow, due to the new Dynamic Oplog feature. 

  This test will only consider cases where the check is true of 1-4 vDisks. 
  The reason being that when we only see 1 busy vDisk oplog, it might indicate 
  a failure to adhere to most of our BPG guidance, where most applications 
  are set up with multiple vDisks. When we see this occur for 2-4 vDisks, 
  it might indicate that multiple vDisks are being used, but maybe more 
  vDisks would be beneficial. Emphasis here on "maybe". In fact, 
  for configurations using VGLB (Volume Groups with Load Balancing), seeing 
  1-4 vDisks per CVM in this state could be quite normal and expected. 

  Key Points:
  - For vDisks that see steady random writes, or low concurrency sequential 
    writes, we will continue to grow its oplog usage until the low-water mark 
    is surpassed. 
  - As long as a vDisk continues to see random writes, or low concurrency 
    sequential writes, the rate of draining will be very conservative. This 
    is true, unless the per-CVM oplog limits are approaching an upper-bound. 

  That said, it's not uncommon to see 1-4 vDisks on a CVM where this test is 
  raised. Unless there is a throughput or latency concern with respect to 
  these VDisks, it's probably not an issue that needs to be resolved."""

  _MSG = "One of {0} heavily utilized VDisk Oplogs: {1}"
  # If only one vdisk has a busy vdisk we should look at BPGs.
  _CNT_HRD_WTRMRK = 1
  # If only four vdisks are busy it may be interesting.
  _CNT_SFT_WTRMRK = 4
  # Both usuage and sample threshold used to define busy.
  _SAMPLE_WTRMRK = .3

  def run_check(self):
    """Check how many utilized oplogs per node exceed the watermark."""

    oplog_max = int(self._obj.gflags.vdisk_distributed_oplog_max_dirty_MB)
    low_water = \
      int(self._obj.gflags.\
      vdisk_distributed_oplog_dynamic_draining_low_water_pct)
    low_water = low_water * 0.01
    # Use the hvars VDisk counters.
    df = self._obj.datasets.hvars.df
    # Use the stargate_hosted_active dataset to get vdisk name
    hosted_df = self._obj.datasets.stargate_hosted_active.df
    hosted_df['vdiskid'] = hosted_df['vdiskid'].apply(str)
    # Filter out the stuff we care about.
    df = df[(df.component == "vdisk") &
            (df.counter == "oplog_bytes")][["instance", "value"]]
    # Group into vdisk IDs.
    groups = df.groupby("instance", axis=0)
    over_ids = []
    # Count the number of VDisks over the usage threshold.
    for group_name, gdf in groups:
      # Skip the total instance.
      if group_name == "total":
        continue
      # Number of samples over the usage threshold.
      over = (gdf.value.astype("float64") / 1024 ** 2 \
          > oplog_max * low_water).sum()
      # Frequency.
      if over / float(len(gdf.value)) > self._SAMPLE_WTRMRK:
        vdisk_name = list((hosted_df[\
          (hosted_df.vdiskid == group_name)].vdiskname).unique())
        vmvg_info = node_utils.get_vmvg_info(self._obj,
                                             vdisk_name[0].split()[0])
        if vmvg_info['vms']:
          vmname = ','.join(vmvg_info['vms'])
        else:
          vmname = None
        if vmvg_info['vg'] is not None and vmname is not None:
          vdisk_string = "vdisk_id:" + group_name + " vm:" + vmname + \
                         " vg:" + vmvg_info['vg'] + " " + vdisk_name[0]
        elif vmvg_info['vg'] is not None:
          vdisk_string = "vdisk_id:" + group_name + " vg: "\
                         + vmvg_info['vg'] + " " + vdisk_name[0]
        elif vmname is not None:
          vdisk_string = "vdisk_id:" + group_name + " vm:" + vmname +\
                         " " + vdisk_name[0]
        else:
          vdisk_string = "vdisk_id:" + group_name + " " +\
                        vdisk_name[0]
        over_ids.append(vdisk_string)
    # Look at how often this is the case.  We probably don't care about
    # isolated instances.
    over_cnt = len(over_ids)
    if over_cnt == self._CNT_HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(over_cnt, over_ids[0])
    elif self._CNT_HRD_WTRMRK < over_cnt <= self._CNT_SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = []
      for over_id in over_ids:
        self.result["criteria"].append(
            self._MSG.format(over_cnt, over_id))
    else:
      self.result["status"] = 0
    return self.result


class VDiskLogicalOplogLimit(base.BaseCheck):
  """Logical Oplog Limit Check."""
  TITLE = "Virtual-Disk Logical Oplog Limit"
  DOC = """A VDisk reaching its logical limit indicates that a guest is
  writing a lot of data and/or the underlying disk system is unable to keep up.
  If there are no signs of disk pressure, consider splitting this disk into
  multiple."""
  _MSG = "{0}: Within {1}% of logical limit {2} times."
  _WTRMRK = .90

  # pylint: disable=super-init-not-called
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
    # Use the stargate_hosted_active dataset to get vdisk name
    hosted_df = self._node.datasets.stargate_hosted_active.df
    hosted_df['vdiskid'] = hosted_df['vdiskid'].apply(str)
    for group_name, gdf in groups:
      if group_name == "total":
        continue
      over = (gdf.value.astype("float64") / 1024 ** 2 > \
          oplog_max * self._WTRMRK).sum()
      if over:
        vdisk_name = list((hosted_df[\
          (hosted_df.vdiskid == group_name)].vdiskname).unique())
        vmvg_info = node_utils.get_vmvg_info(self._node,
                                             vdisk_name[0].split()[0])
        if vmvg_info['vms']:
          vmname = ','.join(vmvg_info['vms'])
        else:
          vmname = None
        if vmvg_info['vg'] is not None and vmname is not None:
          vdisk_string = "vdisk_id:" + group_name + " vm:" + vmname + \
                         " vg:" + vmvg_info['vg'] + " " + vdisk_name[0]
        elif vmvg_info['vg'] is not None:
          vdisk_string = "vdisk_id:" + group_name + " vg:" + vmvg_info['vg']\
                         + " " + vdisk_name[0]
        elif vmname is not None:
          vdisk_string = "vdisk_id:" + group_name + " vm:" + vmname + \
                         " " + vdisk_name[0]
        else:
          vdisk_string = "vdisk_id:" + group_name + " " + vdisk_name[0]
        self.result["criteria"].append(self._MSG.format(
            vdisk_string, self._WTRMRK * 100, over))
    if self.result["criteria"]:
      self.result["status"] = 2
    else:
      self.result["status"] = 0
    return self.result

