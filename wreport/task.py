# Copyright (c) 2017 Nutanix Inc. All rights reserved.
#
# Author: gdowding@nutanix.com dan.small@nutanix.com
"""Task classes."""


class Tasks(object):
  """Class for grouping tasks by level for modules.

  The expected usage is that a module will create a global TASKS object, then
  use add_tasks as a decorator.

  Tasks with the same level may be run in parallel. The tasks for each level
  will be run serially in the order of the level.
  """

  def __init__(self):
    """Initialize Tasks."""
    self._tasks = {}

  def add_task(self, level):
    """Add decorated class to task lists with 'level'.

    Args:
      level (int): Integer specifying level for task.
    """
    def __wrapper(task):
      if level not in self._tasks:
        self._tasks[level] = []
      self._tasks[level].append(task)
      return task
    return __wrapper

  def get_tasks(self):
    """Get all tasks.

    Returns:
      dict where keys are integers and values are lists of tasks.
    """
    return self._tasks

  def sorted_tasks(self):
    """Get a list of tasks in level order."""
    __sorted_tasks = []
    for _, tasks in sorted(self._tasks.items()):
      __sorted_tasks.extend(tasks)
    return __sorted_tasks


class WReportTask(object):
  """Task interface."""

  _name = None

  def run(self):
    """Run task.

    Sub-classes must implement this method.
    """
    raise NotImplementedError()

  # pylint: disable=no-self-use
  def result(self):
    """Get result for running task.

    This is the default implementation which returns None. Sub-classes should
    override this method and document the return value if needed.

    Returns:
      None
    """
    return None

  # pylint: disable=no-self-use
  # pylint: disable=broad-except
  def _run_checks(self, checks):
    """Run a list of checks.

    Args:
      checks: A list of instantiated check instances.
    """
    results = {}
    for check in checks:
      try:
        check_result = check.run_check()
      except ZeroDivisionError:
        # Assumes no activity and defaults to pass.
        check_result = {"status" : 0, "criteria" : None}
      except Exception as e:
        # 3 is Unknown
        # FUTURE: need to fix this! This is causing silent failures
        # for things like NameError exceptions.
        # Uncomment out lines 94-95 to see all exceptions
        # import traceback
        # traceback.print_exc()
        check_result = {"status" : 3, "criteria" : "UNKNOWN", "exception" : e}
      results[check.__class__.__name__] = check_result
    return results

  @classmethod
  def name(cls):
    """Get name of Task.

    Returns:
      str: name of this task.
    """
    return cls._name

  @classmethod
  def get_jobs(cls, data_collection):
    """Default 'get_jobs' implementation

    Subclasses may override this method to split the work into separate jobs
    that can be run in parallel.

    This should be coordinated with 'run'.

    Args:
      data_dir: Path to location of data.
    """
    yield cls(data_collection)

