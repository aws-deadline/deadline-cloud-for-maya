# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging as _logging
import sys as _sys

from openjobio_adaptor_runtime import EntryPoint as _EntryPoint

from .adaptor import MayaAdaptor

__all__ = ["main"]
_logger = _logging.getLogger(__name__)


def main():
    _logger.info("About to start the MayaAdaptor")

    package_name = vars(_sys.modules[__name__])["__package__"]
    if not package_name:
        raise RuntimeError(f"Must be run as a module. Do not run {__file__} directly")

    try:
        _EntryPoint(MayaAdaptor).start()
    except Exception as e:
        _logger.error(f"Entrypoint failed: {e}")
        _sys.exit(1)

    _logger.info("Done MayaAdaptor main")


if __name__ == "__main__":
    main()
