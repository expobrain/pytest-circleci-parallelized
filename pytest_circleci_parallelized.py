# -*- coding: utf-8 -*-
import collections
import subprocess

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("circleci-parallelized")
    group.addoption(
        "--circleci-parallelize",
        dest="circleci_parallelize",
        action="store_true",
        default=False,
        help="Enable parallelization across CircleCI containers.",
    )


def pytest_report_collectionfinish(config, startdir, items):
    return "running {} items due to CircleCI parallelism".format(len(items))


def get_class_name(item):
    class_name, module_name = None, None
    for parent in reversed(item.listchain()):
        if isinstance(parent, pytest.Class):
            class_name = parent.name
        elif isinstance(parent, pytest.Module):
            module_name = parent.module.__name__
            break

    if class_name:
        return "{}.{}".format(module_name, class_name)
    else:
        return module_name


def filter_tests_with_circleci(test_list):
    circleci_input = bytes("\n".join(test_list))
    p = subprocess.Popen(
        [
            "circleci",
            "tests",
            "split",
            "--split-by=timings",
            "--timings-type=classname",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    circleci_output, _ = p.communicate(circleci_input)
    return [line.strip() for line in circleci_output.decode("utf-8").split("\n")]


def pytest_collection_modifyitems(session, config, items):
    class_mapping = collections.defaultdict(list)
    for item in items:
        class_name = get_class_name(item)
        class_mapping[class_name].append(item)

    filtered_tests = filter_tests_with_circleci(class_mapping.keys())

    new_items = []
    for name in filtered_tests:
        new_items.extend(class_mapping[name])

    items[:] = new_items
