from setuptools import setup, find_packages

setup(name="wreport",
      description="Illuminati Weather Report",
      url="http://gitlab.rtp.nutanix.com:ntnx/wreport.git",
      author="Dan Small",
      author_email="dan.small@nutanix.com",
      license="All Rights Reserved",
      packages=["wreport", "wreport.checks", "gnosis", "nutbuf"],
      dependency_links=[
        'git+ssh://git@gitlab-ee.rtp.nutanix.com/gdowding/nutbuf.git@master#egg=nutbuf',
        'git+ssh://git@gitlab.rtp.nutanix.com/ntnx/gnosis.git@master#egg=ntnx_gnosis'
      ],
      test_suite = "test.all_tests",
      install_requires=["pandas", "ntnx-gnosis", "plotly", "matplotlib"],
      tests_require=["mock"])
