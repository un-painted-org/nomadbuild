# conftest.py
# Copyright (c) 2025 marsmensch
# SPDX-License-Identifier: MIT
#
"""Shared pytest configuration to ensure project root is on sys.path for all tests."""
import sys
import os
from pathlib import Path

# Determine project root (two levels up from this file)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    # Insert at position 0 to give it precedence
    sys.path.insert(0, str(ROOT_DIR))

# ---------------------------------------------------------------------------
# Optional dependency stubbing: Selenium
# Some UI tests rely on the import succeeding but never actually use Selenium
# runtime objects.  If Selenium is not installed in the execution environment,
# we provide lightweight stub modules so the tests are not skipped.
# ---------------------------------------------------------------------------
import types

if 'selenium' not in sys.modules:
    selenium_stub = types.ModuleType('selenium')
    webdriver_stub = types.ModuleType('selenium.webdriver')
    common_stub = types.ModuleType('selenium.webdriver.common')
    by_stub = types.ModuleType('selenium.webdriver.common.by')
    support_stub = types.ModuleType('selenium.webdriver.support')
    ui_stub = types.ModuleType('selenium.webdriver.support.ui')
    ec_stub = types.ModuleType('selenium.webdriver.support.expected_conditions')

    # Insert minimal attributes that the tests might access
    webdriver_stub.Chrome = lambda *args, **kwargs: None
    setattr(by_stub, 'By', types.SimpleNamespace())

    # Register stubs in sys.modules so import machinery finds them
    sys.modules['selenium'] = selenium_stub
    sys.modules['selenium.webdriver'] = webdriver_stub
    sys.modules['selenium.webdriver.common'] = common_stub
    sys.modules['selenium.webdriver.common.by'] = by_stub
    sys.modules['selenium.webdriver.support'] = support_stub
    sys.modules['selenium.webdriver.support.ui'] = ui_stub
    sys.modules['selenium.webdriver.support.expected_conditions'] = ec_stub

    # Link nested modules for proper attribute traversal
    selenium_stub.webdriver = webdriver_stub
    webdriver_stub.common = common_stub
    webdriver_stub.support = support_stub
    common_stub.by = by_stub
    support_stub.ui = ui_stub
    support_stub.expected_conditions = ec_stub

    # Minimal placeholder objects used in tests
    class _Dummy:  # Generic dummy callable / class
        def __init__(self, *a, **k):
            pass
        def __call__(self, *a, **k):
            return None
    # Populate typical names
    ui_stub.WebDriverWait = _Dummy
    ec_stub.expected_conditions = _Dummy
    setattr(by_stub, 'By', types.SimpleNamespace()) 