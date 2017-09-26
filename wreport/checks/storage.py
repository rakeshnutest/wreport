# Copyright (c) 2017 Nutanix Inc. All rights reserved.
# Author: dan.small@nutanix.com
#
# Various storage related checks.
#
#
from wreport.checks import base


class VDiskColdTierReads(base.BaseCheck):
  """Check the ratio of cold to hot tier reads.

  Two watermarks are defined, a soft and a hard.  If the ratio of cold-tier
  reads exceeds the watermark and the frequency exceeds the same ratio the test
  criteria has been met."""
  TITLE = "Virtual-Disk Cold Tier Reads"
  DOC = "some_url"
  _MSG = "Exceeded {0}%, {1} times."
  # Warning watermark.
  _SFT_WTRMRK = .25
  # Failure watermark.
  _HRD_WTRMRK = .40

  def run_check(self):
    """Check the ratio of cold-tier to hot-tier reads.

    This check is based on the Arithmos virtual_disk_stats.
    """
    wanted = ["estore_hdd_mb", "estore_ssd_mb"]
    df = self._obj.read_source_df
    # Make sure the counters are there.
    for counter in wanted:
      if counter not in df.columns:
        # Throwing an exception will percolate up.
        raise Exception("read_source_df missing columns: {0}.".format(
            ", ".join(wanted)))
    hdd_ratio = df.estore_hdd_mb / (df.estore_hdd_mb + df.estore_ssd_mb)
    hdd_ratio.dropna(inplace=True)
    # Run the check.
    self._check_watermarks(hdd_ratio)
    # Return the result.
    return self.result

  def _check_watermarks(self, data):
    """Evaluate data against the watermarks and set the appropriate results.

    Args:
      data: The data to evaluate.
    """
    if len(data[data > self._HRD_WTRMRK]) / \
        float(len(data)) > self._HRD_WTRMRK:
      self.result["status"] = 2
      self.result["criteria"] = self._MSG.format(
        self._HRD_WTRMRK * 100, len(data[data > self._HRD_WTRMRK]))
    elif len(data[data > self._SFT_WTRMRK]) / \
        float(len(data)) > self._SFT_WTRMRK:
      self.result["status"] = 1
      self.result["criteria"] = self._MSG.format(
        self._SFT_WTRMRK * 100, len(data[data > self._SFT_WTRMRK]))
    else:
      self.result["status"] = 0

