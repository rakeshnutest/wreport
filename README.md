# Weather Report
The Weather Report is comprised of various performance related checks that are
used during performance troubleshooting to identify commonly encountered issues.

This tool can be installed and used as a python package and used as an import or
executed as a script.

## Weather Checks
Each check must have a TITLE and DOC class variable and a "run_check"  method.
The TITLE variable represents the display name for the check.  The DOC variable
provides a URL for documentation about the check.  The "run_check" method is
used as an entry point to execute the check.

Each check must return a dictionary containing the "status" and the "criteria".
The "criteria" is a string that provides context around why a check was flagged
as interesting or for investigation. The "status" is an integer that
represents the following statuses:
0. Likely not an issue.
1. Something of note.
2. Worth investigating.
3. Unknown

** If an exception is thrown while performing a check the status is given a
value of 3. This could be the result of missing data or a breakage in code.

Checks rely on gnosis objects and are grouped respectively. All checks that
apply to an object type are executed in the same process as a batch to mitigate
storage IO and to take advantage of cached data sets.

To add checks to a batch the check class is added to the appropriate check list,
which is a WeatherReport class constant. Currently there are four such lists:
* _VDISK_CHECKS
* _VM_CHECKS
* _NODE_CHECKS
* _CLUSTER_CHECKS

