# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
"""A base check for others to inherit from, or use as a template.

All checks require a TITLE and DOC constant, and a run_check method.
"""

class BaseCheck(object):
  """The base check structure."""
  # The display name for the check.
  TITLE = ""
  # A URL for linked documentation.
  DOC = ""
  # The message to display, ideally with the criteria used.
  _MSG = ""

  # If overwritten, the result property is expected.
  def __init__(self, obj):
    """Instantiates a check instance.
    Args:
      obj: The object (vdisk, vm, node, etc.) to check.

    Return a dictionary containing the check status and criteria:
      status:
        None: Unable to perform check.
        0: Likely not an issue.
        1: Something of note.
        2: Worth investigating.
      criteria: A text string that provides context around the evaluation.
    """
    self._obj = obj
    # This is a required attribute.
    self.result = {"status" : None, "criteria" : None}

  # All Checks should include a run_check method that returns the result.
  def run_check(self):
    """Execute the check and return the expected dictionary."""
    return self.result

