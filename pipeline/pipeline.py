import sys

import pandas as pd

# import os
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dataplatform.settings")
# import django
# django.setup()
import log_utils
from datatransform import models
from datatransform.models import Task


class Pipeline(object):
    def __init__(self, model: models.Pipeline, data_path: str):
        self.model = model
        self.data_path = data_path
        self._commands = list()
        self.schema = list()
        self.logger = log_utils.get_logger_for_existing_file(self.model.pipeline_id)

    def add(self, tasks):
        self._commands.append(tasks)
        return self


    #
    # def execute(self):
    #     self.model.status = 'In Progress'
    #     self.model.save()
    #     self._commands[0].set_data(self.data)
    #     self._commands[0].execute_chain()
    #     self.model.status = "Done"
    #     self.model.save()
