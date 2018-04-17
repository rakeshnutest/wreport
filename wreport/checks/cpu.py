# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
"""Various CPU related checks."""
from wreport.checks import base


class NodeCvmCpuUsage(base.BaseCheck):
  """Checks the overall CVM CPU utilization.

  The evaluation is based on the upper quartile.
  """
  TITLE = "CVM CPU Usage"
  DOC = """This check evaluates the CVM's CPU utilization. If the CPU utization
  is excessive it could be a performance inhibior. Consider increasing the 
  CVM's vCPU allocation. Note, spanning NUMA boundaries generally not
  recommended."""
  _MSG = "Average utilization: {0:.1f}%, exceeded {1}% of total."
  _SFT_WTRMRK = .75
  _HRD_WTRMRK = .9

  def run_check(self):
    """Evaluate CVMs CPU utilization."""
    cpu_max = self._obj.cvm_cpu_count * 100
    pct_used = self._obj.host_cvm_cpu_util.pct_used
    avg = pct_used[pct_used >= pct_used.describe().ix[
        "75%"]].describe().ix["mean"]
    if avg >= cpu_max * self._HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(avg, self._HRD_WTRMRK * 100)
    elif avg >= cpu_max * self._SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(avg, self._SFT_WTRMRK * 100)
    else:
      self.result["status"] = 0
    return self.result


class NodeCvmCpuReady(base.BaseCheck):
  """Checks the overall CVM CPU ready time.

  The evaluation is based on the upper quartile.
  """
  TITLE = "CVM CPU Ready"
  DOC = """This check evaluates the percentage of time the CVM spent waiting to
  be scheduled (%Ready), but couldn't be due to contention. This is an
  indicator that the CVM may be getting starved for CPU time or that the CVM is
  consuming a lot of CPU time. Ensure the CVM's vCPUs are affinitized to one
  socket and consider moving busy VMs to less busy hosts.
  """
  _MSG = "Average % Ready: {0:.1f}%, exceeded {1}%."
  _SFT_WTRMRK = 3
  _HRD_WTRMRK = 5

  def run_check(self):
    """Evaluate CVMs CPU ready time."""
    pct_ready = self._obj.host_cvm_cpu_util.pct_ready
    avg = pct_ready[pct_ready >= pct_ready.describe().ix[
        "75%"]].describe().ix["mean"]
    if avg >= self._obj.cvm_cpu_count * self._HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(avg, self._HRD_WTRMRK)
    elif avg >= self._obj.cvm_cpu_count * self._SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(avg, self._SFT_WTRMRK)
    else:
      self.result["status"] = 0
    return self.result


class NodeHostCpuUtilInbalance(base.BaseCheck):
  """
  Checks for an inbalance in physical CPU utilization per-socket.
  """
  TITLE = "Host CPU Utilization Balance"
  DOC = """This check evaluates the balance of CPU utilization.  An inbalance of
  CPU utilization indicates a hot guest. The workload on the guest driving the
  utilization should be evaluated and split work across multiple VMs should be
  considered."""
  _MSG = "Mean utilizaiton: {0}, Cv: {1}, exceeded {2}."
  _SFT_WTRMRK = .5
  _HRD_WTRMRK = .7

  def run_check(self):
    """Check for inbalances in CPU utilization."""
    df = self._obj.host_pcpu_util
    mean_util = df.describe().loc["mean"]
    mean_util.index = mean_util.index.astype(int)
    mean_util.sort_index(inplace=True)
    # Run the check.
    self._check_watermarks(mean_util)
    # Return the result.
    return self.result

  def _check_watermarks(self, data):
    """Evaluate data against the watermarks and set the appropriate results.

    Args:
      data: The data series to evaluate.
    """
    # TODO: Mitigate false positives by comparing core utilizaiton between
    # sockets.  See: ENG-103593.
    group_len = len(data) / 2
    cv = 0
    for idx_slice in range(len(data))[0::group_len]:
      group = data[idx_slice:idx_slice+group_len]
      # Sample coefficient of variation
      group_cv = group.std() / group.mean()
      # Base evaluation on the most variation.
      if group_cv > cv:
        cv = group_cv
        avg = group.mean()
    if cv >= self._HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(avg, cv, self._HRD_WTRMRK)
    elif cv >= self._SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(avg, cv, self._SFT_WTRMRK)
    else:
      self.result["status"] = 0


class NodeHostCpuUtil(base.BaseCheck):
  """Check overall host CPU utilization.

  The evaluation is based on the upper quartile.
  """
  TITLE = "Host CPU Usage"
  DOC = """This check evaluates the host's CPU utilization. If the CPU utization
  is excessive it could be a limting factor to performance. If possible,
  consider moving some guests to another node."""
  _MSG = "Average utilization: {0:.1f}%, exceeded {1}%."
  _SFT_WTRMRK = 75
  _HRD_WTRMRK = 90

  def run_check(self):
    """Evaluate CPU utilization."""
    df = self._obj.host_pcpu_util
    df = df[df >= df.describe().ix["75%"]].describe()
    avg = df.ix["mean"].mean()
    if avg >= self._HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(avg, self._HRD_WTRMRK)
    elif avg >= self._SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(avg, self._SFT_WTRMRK)
    else:
      self.result["status"] = 0
    return self.result

