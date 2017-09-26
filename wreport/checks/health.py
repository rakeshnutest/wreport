# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
# Check for Stargate restarts.
#
# This is a pass fail check.
#
from wreport.checks import base


class NodeStargateRestarts(base.BaseCheck):
  """Cold-tier read check."""
  TITLE = "Stargate Restarts"
  DOC = "some_url"
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

