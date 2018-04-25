# The Weather Report
The Weather Report is a tool used to check for commonly encountered issues that
may impact performance.  After installing the Python package, this tool can be
imported or used as a script.

Note, you'll need access to the illuminati data.  Fortunately, the
[jupyterhub](https://jupyterhub.rtp.nutanix.com/) servers do.  Otherwise, you'll
want to mount the collect_perf repository.

## Weather Checks
Checks rely on [gnosis](http://gitlab.rtp.nutanix.com/ntnx/gnosis) objects
(`VDisk`, `Vm`, `Node`, or `Cluster`) and are grouped respectively. All checks
that apply to an object are executed in the same process as a batch.  This
mitigates storage IO and to take advantage of cached data sets.  These batches
are executed against multiple instances simultaneously using a task queue.

Each check must return a dictionary containing the `status` and the `criteria`.
The `criteria` is a string that provides context around why a check was flagged
as interesting or as something to investigate. The `status` is an integer that
represents the following:
* 0: Good - Likely not an issue.
* 1: Interesting - Something of note, but not necessarily a problem.
* 2: Investigate - Worth investigating.
* 3: Unknown - The check failed.
  * If an exception is thrown while performing a check the status is given value
of 3. This could be the result of missing data or code breakage.  The exception
will be stored as the `criteria`.

Additionally, a check has a `TITLE` and `DOC` class-variable,  as well as a
`run_check`  method.
* The `TITLE` variable represents the display name for the check, which can be
* used in things like Illuminati reports.
* The `DOC` variable provides context around the check and some suggested
action.
* The `run_check` method is used as an entry point to execute the check.

## About the Task Queue
The `weather_report` module contains a global `TASK` object.  This is really
just a dictionary that organizes the execution of the tasks.  There are two
levels, level-0 and level-1.  Level-0 tasks can be executed in parallel, while
level-1 are serialized and executed following all the level-0 tasks.

When imported, a `wreport.task.WReportTask` object is added to its defined
level.  When the `get_jobs` class-method is ran these tasks act as generators,
yielding a job for each of the respective `gnosis` objects.
* This was modeled from George Dowding's task queue implementation in the
illuminati consolidation.

If the number of processors is greater than one, a multiprocessing pool is
created and the level-0 tasks are executed in parallel.

# Install.
`$ pip install git+http://gitlab.rtp.nutanix.com/ntnx/wreport.git`

However, if developing is your goal you may wish to perform a git clone and install an
editable version.
```
$ git clone git@gitlab.rtp.nutanix.com:ntnx/wreport.git
$ pip install -e wreport
```

# Python Examples
Once the `wreport` package is installed you can simply import it and point at an
illuminati directory:
```
from wreport import weather_report as wrpt
report = wrpt.WeatherReport(<path_to_illuminati_data>)
```

The various checks return nested dictionaries containing the results, which get
added to a list of raw results.  Every check will return a status.  This list
can be accessed through the `raw_results` property.

Building on the example above, `report.raw_results` returns:
```
[{'501856:6000C29d-cc1e-7329-51ea-582f3c6e992d': {'VDiskColdTierReads': {'criteria': 'UNKNOWN',
    'exception': Exception('read_source_df missing columns: estore_hdd_kb, estore_ssd_kb.'),
    'status': 3}}},
...
 {'503e12:6000C290-0313-89b0-a151-ba6f100bda1c': {'VDiskColdTierReads': {'criteria': 'UNKNOWN',
    'exception': Exception('read_source_df missing columns: estore_hdd_kb, estore_ssd_kb.'),
    'status': 3}}}
]
```

After running, the results are pickled and stored in the root of the path
provided as `wreport.p` and subsequent accesses will read that pickled data.
To run the weather report anew, instantiate the instance with the `regen=True`
option.  For example:
`report = wrpt.WeatherReport(<path_to_illuminati_data>, regen=True)`

Additionally, the `proc_cnt` option can be used to control how many processes
are used to generate the results.

The `raw_results` can be grouped by check name. When this is performed the
check's `DOC` and `TITLE` attributes are added to the returned dictionary.  This
also sets an overall `group_status` for the check based on the highest status
seen.

Group Status Codes:
  * 3: The check failed against all objects. This is likely a systemic data or
    code related issue.
  * 2: The test executed and at least one object warrents further
    investigation.
  * 1: The test executed and at least one object was flagged as interesting.
    This status is also used when some objets failed to execute while others
    passed. When this occures it it likely the result of that specific
    objects data set instead of a systemic data or test issue.
  * 0: The test executed and all objects tested passed, or some passed while
    others threw an exception.
    * The later happens when some objects are missing data.  E.g. a partial
collection, or a storage only node with no hosted VDisks.

Further, these results can be filtered, using the `status_filter` option.
For example, `report.get_results(status_filter=[2])` will return a dictionary of
results, grouped by the check name and only containing checks with a
global status of `2`.
```
{'NodeCvmCpuUsage': {u'10.210.205.5': {'criteria': 'Average utilization: 736.3%, exceeded 90.0% of total.',
   'status': 2},
  'doc': "This check evaluates the CVM's CPU utilization. If the CPU utization\n  is excessive it could be a performance inhibior. Consider increasing the \n  CVM's vCPU allocation. Note, spanning NUMA boundaries generally not\n  recommended.",
  'group_status': 2,
  'status_list': [1, 1, 2, 1],
  'title': 'CVM CPU Usage'}}
```

For readability, this data can also be prettily printed:
```
report.print_info()
print
report.print_results()
```
Will have an output like:
```
Cluster ID: 54899 - Name: DCPSPNTNXINFRA
AOS Release: el6-release-euphrates-5.1.4-stable-cf11e89977
4 Nodes - 180 UVMs
Hot/Cold Tier Size: 4 / 79

VDiskLogicalOplogLimit: No Issues Found
NodeBusyOplogCount: No Issues Found
VDiskColdTierReads
  503e12:6000C290-0313-89b0-a151-ba6f100bda1c: UNKNOWN
  5009e1:6000C293-077f-d594-e3f2-208a91079b3f: Exceeded 40.0%, 2 times.
  501850:6000C293-fb9a-34a3-4d99-1d4ed6253f74: UNKNOWN
  503e12:6000C298-9043-e063-91af-dd8a43cb5263: UNKNOWN
...
```

# Adding Checks
The easiest way to get started by referencing the existing checks and to inherit
from the `BaseCheck` object.  Checks are currently organized by their resource.
For example, all CPU related checks are in the `cpu` module.  The currently
available modules can be found in `wreport.checks`.

Checks are expected to:
* Have `TITLE` and `DOC` class-variables
  * `TITLE` should be a friendly name, e.g. "CVM CPU Usage".
  * `DOC` should be an explanation of what is being checked and why it's
important.  If possible, corrective actions should be included.
* Have `run_check` method
* A `result` attribute that returns a dictionary containing a `status` key and a
`criteria` key.
  * The `status` value should be an integer 0, 1, 2.  A status of 3 will be
assigned automatically if an exception in thrown.
  * The `criteria` should provide the reason this object was flagged and what
threshold(s) was exceeded.
* Have a corollary unit test

To add checks to a batch, add it to the appropriate check list, which is a
`WeatherReport` class constant. Currently there are four such lists:

_VDISK_CHECKS
_VM_CHECKS
_NODE_CHECKS
_CLUSTER_CHECKS

# Troubleshooting
Because the Weather Report relies on various `gnosis` objects, you'll want to
instantiate a instance of the object for the respecrtive check.  Here's an crude
example of executing a specific check against a specific `Node` instance.
```
from wreport import weather_report as wrpt
from wreport.checks.cpu import NodeCvmCpuReady

report = wrpt.WeatherReport(<path_to_illuminati_data>)
# When the WeatherReport instance is instantiated, you get a gnosis cluster
# instance too.
n = report.cluster.nodes.R22_A
c = NodeCvmCpuReady(n)
c.run_check()
```
