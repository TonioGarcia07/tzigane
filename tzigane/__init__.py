# -*- coding: utf-8 -*-

import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.NullHandler())

local_format = "{asctime} - {levelname} - {name}: {message}"
LOCAL_FORMATTER = logging.Formatter(local_format, style='{')
cloud_format = "{name}: {message}"
cloud_formatter = logging.Formatter(cloud_format, style='{')
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.INFO)
CONSOLE_HANDLER.setFormatter(LOCAL_FORMATTER)
LOGGER.addHandler(CONSOLE_HANDLER)
