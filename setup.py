from setuptools import setup, find_packages

setup(name="wreport",
      description="Illuminati Weather Report",
      url="http://gitlab.rtp.nutanix.com:ntnx/wreport.git",
      install_requires=["ntnx-gnosis"],
      dependency_links=["http://gitlab.rtp.nutanix.com/ntnx/gnosis.git"],
      license="Copyright (c) 2014-2017 Nutanix Inc.",
      maintainer="Nutanix Core Data Path Performance Engineering",
      maintainer_email="dan.small@nutanix.com",
      packages=find_packages(exclude=["doc"]),
      setup_requires=["setuptools_scm"],
      test_suite = "tests.all_tests",
      use_scm_version=True)
