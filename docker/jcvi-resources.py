#!/usr/bin/env python3
"""Use the same resource contract as the frozen host-side discovery module."""
import runpy

runpy.run_path('/opt/jcvi/share/resource_validation.py', run_name='__main__')
