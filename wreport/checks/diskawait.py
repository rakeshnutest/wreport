# Copyright (c) 2022 Nutanix Inc. All rights reserved.
# Author: errol.fouquet@nutanix.com
#
"""Various Disk Latency related checks."""
import pandas as pd

from wreport.checks import base

class DiskWriteAwait(base.BaseCheck):
  """
  Checks for higher than expected w_await latency for SSD/NVMe disks.

  In cases where disk await exceeds a threshold, we will provide other
  disk iostat values to aide in diagnosis
  """
  TITLE = "Disk Write Await Check"
  DOC = """This check evaluates the w_await values for SSD/NVMe disks and
  provides alerts when values exceeds a threshold for a minimum of 2% of the 
  iostat samples.
  When we see write latency this high on SSD/NVMe disks, it might indicate an
  issue with xtrim support for the underlying drive. Refer to kb7654."""
  _MSG = ("Disk {0} w_await latency >= {1}ms {2} times {3:.2%} of {4} samples"
          " avg qusz {5:.2f} Cv {6:.2f} avg w/s {7:.2f} Cv {8:.2f}")
  _SFT_WTRMRK = .02
  _HRD_WTRMRK = .1
  _LATENCY_THRESHOLD = 10


  def run_check(self):
    """ Count/percentage times w_await >= 10ms per SSD/NVMe disk """

    # we need to make sure list_disks is part of the collection

    if "list_disks" not in self._obj.datasets:
      return self.result
    self.result["status"] = 0
    df = self._obj.datasets.list_disks.df
    iostat_df = self._obj.datasets.iostat.df
    serials = [disk.disk_serial_id for disk in self._obj.disks.values() \
                if "SSD" in disk.storage_tier]
    disks = []
    for serial in serials:
      disks.append(df.loc[df['serial'] == serial, \
        'disk'].iloc[0].split('/')[-1])
    for dev, df in iostat_df.groupby('device'):
      if dev in disks:
        count = 0
        qusz = []
        wps = []
        newdf = pd.DataFrame(df)
        for _, row in newdf.iterrows():
          if row['w_await'] >= self._LATENCY_THRESHOLD:
            count += 1
            qusz.append(row['aqu_sz'])
            wps.append(row['w_s'])
        val = float(count) / float(len(df.index))
        if count > 0:
          qusz_mean = pd.DataFrame(qusz).describe().loc["mean"][0]
          qusz_stddev = pd.DataFrame(qusz).describe().loc["std"][0]
          wps_mean = pd.DataFrame(wps).describe().loc["mean"][0]
          wps_stddev = pd.DataFrame(wps).describe().loc["std"][0]
        if val >= self._HRD_WTRMRK:
          self.result["status"] = max(self.result["status"], 2)
          if self.result["criteria"] is None:
            self.result["criteria"] = []
          self.result["criteria"].append(self._MSG.format(
              dev,
              self._LATENCY_THRESHOLD,
              count,
              val,
              len(df.index),
              qusz_mean,
              qusz_stddev / qusz_mean,
              wps_mean,
              wps_stddev / wps_mean,
          ))
        elif val >= self._SFT_WTRMRK:
          self.result["status"] = max(self.result["status"], 1)
          if self.result["criteria"] is None:
            self.result["criteria"] = []
          self.result["criteria"].append(self._MSG.format(
              dev,
              self._LATENCY_THRESHOLD,
              count,
              val,
              len(df.index),
              qusz_mean,
              qusz_stddev / qusz_mean,
              wps_mean,
              wps_stddev / wps_mean,
          ))
    return self.result
