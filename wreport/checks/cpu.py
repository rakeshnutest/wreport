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
    group_len = int(len(data) / 2)
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


class NodeCvmSustThreadUtil(base.BaseCheck):
  """Check for sustained thread utilizaiton.

  The evaulation is based on the upper quartile of samples.
  """
  TITLE = "CVM Thread Utilization"
  DOC = """This check attempts to identify threads with sustained utilization.
  When threads are identified, try understanding what is driving that usage
  before taking action and avoid adding threads arbitrarily. Start by ensuring
  the cluster health from both a service and network perspective.

  If Stargate, or other CDP related threads are identified, consider spreading
  workload to less busy controllers. If an epoll thread is identified on ESX
  consider adding a container and balancing the workload between the two."""
  _MSG = "{0} - Mean: {1:.2f} exceeded {2:.2f}%, Max: {3:.2f}, Cv: {4:.5f}, " \
    "Count: {5}, Runs: {6}"
  _SFT_WTRMK = 60
  _HRD_WTRMK = 75

  # pylint: disable=no-self-use
  def _count_runs(self, ts_pd):
    """Count the number of times consecutive timestamps were seen.

    This is used to filter out threads with intermittent usuage.

    Args:
      ts_pd: A timeseries Pandas DataFrame w/ a timestamp column of type
        pd.DateTime.
    """
    # Because `top` can be sampled at various lengths we need to normalize the
    # diffs.  Doing two diffs seems to be the easiest, however, we lose the
    # first two samples (can't diff on nothing).  This is probably okay.
    diff = ts_pd.timestamp.diff().astype("timedelta64[s]")[1:]
    diff = diff.diff()[1:].astype('timedelta64[s]').astype(int)
    run_len = 0
    runs = 0
    for val in diff.values:
      if val <= 0:
        run_len += 1
      else:
        if run_len > 2:
          runs += 1
          run_len = 0
    # This catches instances where the series ends in a run.
    if run_len > 2:
      runs += 1
    return runs

  def run_check(self):
    self.result["status"] = 0
    df = self._obj.datasets.top.df.copy()
    df = df[["pid", "pctcpu", "command", "timestamp"]]
    df["thread"] = df.pid.astype(str).str.cat(df.command, sep=":")
    groups = df.groupby("thread")
    for thread, t_df in groups:
      util = t_df[t_df.pctcpu >= t_df.pctcpu.describe().loc["75%"]]
      runs = self._count_runs(util)
      if runs == 0:
        continue
      desc = util.pctcpu.describe()
      # Coefficient of variation.
      cov = desc.loc["std"] / desc.loc["count"]
      if desc.loc["mean"] >= self._HRD_WTRMK:
        wtrmrk = self._HRD_WTRMK
        self.result["status"] = 2
      elif desc.loc["mean"] >= self._SFT_WTRMK:
        wtrmrk = self._SFT_WTRMK
        if self.result["status"] != 2:
          self.result["status"] = 1
      else:
        continue
      if self.result["criteria"] is None:
        self.result["criteria"] = []
      self.result["criteria"].append(
          self._MSG.format(thread, desc.loc["mean"], wtrmrk,
                           desc.loc["max"], cov, desc.loc["count"], runs))
    return self.result

