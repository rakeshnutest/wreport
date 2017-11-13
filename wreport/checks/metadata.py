# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
"""Metadata related checks."""

import pandas as pd

from wreport.checks import base


class NodeMedusaLatCost(base.BaseCheck):
  """Checks the percentage of time during reads for metadata resolution.

  There is a response time requirement that must be met in addition to two
  watermarks to evaluate the contribution to the total response time.
  """
  TITLE = "Metadata Resolution"
  DOC = """This check evaluates the contribution of metadata lookups to the
  overall response time. This is an indicator that the CVM's memory allocation
  may need to be increased, that the guests are reading a large working set, or
  tunning between the types of data being cached is needed."""
  _MSG = "Metadata resolution exceeded {0}MS and accounted for more than {1}%" \
      " of the total resposne time."
  # Response time threshold in usecs.
  _R_WTRMRK = 10000
  # Warning threshold percentage.
  _SFT_WTRMRK = 25
  # Failure threshold percentage.
  _HRD_WTRMRK = 40
  # stargate_latency stages related to metadata resolution.
  _STAGES = ["VdiskBlockmapLookupDone", "EgroupFinderOpDone"]

  def run_check(self):
    """Evaluate the contribution of medusa realted stages to latency."""
    df = self._obj.datasets.stargate_latency.df
    # Lean the DF down.
    df = df[(df.host == self._obj.cvm_ip) &
            (df.component == "vdisk_controller") &
            (df.op_type == "nfs_reads") &
            (df.stage.isin(self._STAGES))]
    # Pivot and sum the stages we care about and make a new DF.
    pdf = pd.DataFrame()
    pdf["avg_lat_usec"] = df.pivot(
        index="timestamp", columns="stage",
        values="avglatency_us").sum(axis=1)
    pdf["pct_total"] = df.pivot(
        index="timestamp", columns="stage",
        values="latencypct_oftotal").sum(axis=1)
    # Check if we exceeded both the response time and the percentage of the
    # overal total watermarks.
    if not pdf[(pdf.avg_lat_usec >= self._R_WTRMRK) &
               (pdf.pct_total >= self._HRD_WTRMRK)].empty:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(
          self._R_WTRMRK / 1000, self._HRD_WTRMRK)
    # If we didn't hit the hard watermark, check the soft.
    elif not pdf[(pdf.avg_lat_usec >= self._R_WTRMRK) &
                 (pdf.pct_total >= self._SFT_WTRMRK)].empty:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(
          self._R_WTRMRK / 1000, self._SFT_WTRMRK)
    else:
      self.result["status"] = 0
    return self.result

