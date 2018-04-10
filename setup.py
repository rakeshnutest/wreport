from setuptools import setup, find_packages

setup(name="wreport",
      description="Illuminati Weather Report",
      url="http://gitlab.rtp.nutanix.com:ntnx/wreport.git",
      author="Dan Small",
      author_email="dan.small@nutanix.com",
      license="All Rights Reserved",
      packages=["wreport", "wreport.checks"],
      test_suite = "test.all_tests",
      install_requires=["pandas", "ntnx-gnosis", "plotly"],
      tests_require=["mock"])
