import json
import os
from datatransform.models import Pipeline
from pipeline import pipeline
from config import settings
import pandas as pd
from tasks import prefect_tasks, prefect_json_transformations
from utils import update_resource, create_resource

mod = __import__('tasks', fromlist=settings.tasks.values())


def task_executor(pipeline_id, data_pickle, res_details, db_action, file_format):
    db_action = "update"
    print("inside te***")
    print("pipeline_id is ", pipeline_id)
    data = None
    try:
        if file_format == "CSV":
            try:
                data = pd.read_pickle(data_pickle)
                os.remove(data_pickle)
            except:
                pass
        elif file_format == "JSON":
            f = open(data_pickle, "rb")
            data = json.load(f)
            f.close()
            os.remove(data_pickle)
            if isinstance(data, str):
                data = json.loads(data)

        print(" got pipeline id...", pipeline_id)
        print("data before,,,%%%", data)
        pipeline_object = Pipeline.objects.get(pk=pipeline_id)
        task = list(pipeline_object.task_set.all().order_by("order_no"))[-1]
        new_pipeline = pipeline.Pipeline(pipeline_object, data)
        print("received tasks from POST request..for..", new_pipeline.model.pipeline_name)

        if getattr(task, "status") == "Created":
            new_pipeline.add(task)
        print(new_pipeline._commands)

        # def execution_from_model(task):
        #     new_pipeline.add(task)

        # [execution_from_model(task) for task in tasks]
        if res_details == "api_res" and file_format == "CSV":
            prefect_tasks.pipeline_executor(new_pipeline)
            return new_pipeline.data
        elif res_details == "api_res" and file_format == "JSON":
            prefect_json_transformations.json_pipeline_executor(new_pipeline)
            return new_pipeline.data
        new_pipeline.schema = res_details['data']['resource']['schema']

        if file_format == "CSV":
            prefect_tasks.pipeline_executor(new_pipeline)
        elif file_format == "JSON":
            prefect_json_transformations.json_pipeline_executor(new_pipeline)
        if new_pipeline.model.status == "Failed":
            raise Exception("There was an error while running the pipeline")
        if db_action == "update":
            fresh_schema = []
            for schema in new_pipeline.schema:
                if len(schema['key']) != 0:
                    fresh_schema.append(schema)
            new_pipeline.schema = fresh_schema
            update_resource(
                {'package_id': new_pipeline.model.output_id, 'resource_name': new_pipeline.model.pipeline_name,
                 'res_details': res_details, 'data': new_pipeline.data, 'schema': new_pipeline.schema,
                 "logger": new_pipeline.logger})
        if db_action == "create":
            for sc in new_pipeline.schema:
                sc.pop('id', None)

            fresh_schema = []
            for schema in new_pipeline.schema:
                # if found a schema with no key, no need to use it while creating
                if len(schema['key']) != 0:
                    fresh_schema.append(schema)
            new_pipeline.schema = fresh_schema
            id = create_resource(
                {'package_id': new_pipeline.model.output_id, 'resource_name': new_pipeline.model.pipeline_name,
                 'res_details': res_details, 'data': new_pipeline.data, 'schema': new_pipeline.schema,
                 "logger": new_pipeline.logger}
            )
            new_pipeline.model.resultant_res_id = id
            new_pipeline.model.save()
            print("res_id created at...", id)
        return

    except Exception as e:
        new_pipeline.model.err_msg = str(e)
        pipeline.model.save()
        raise e
