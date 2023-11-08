# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
"""Checks for issues related to systemic health."""

from wreport.checks import base


class NodeStargateRestarts(base.BaseCheck):
  """Stargate Restart check."""
  TITLE = "Stargate Restarts"
  DOC = """This check will indicate if any stargate restarts were encountered
  during the collection. If restarts were seen, the cluster health issues should
  be corrected before evaluating performance."""

  MSG = "Restarts seen during the collection at {}."

  def run_check(self):
    """Look for restarts."""
    restart_cnt = len(self._obj.stargate_start_times)
    if restart_cnt > 1:
      self.result["status"] = 2
      self.result["criteria"] = self.MSG.format(
          ", ".join(self._obj.stargate_start_times))
    else:
      self.result["status"] = 0
    return self.result
