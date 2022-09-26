import json
import os

import requests
from background_task import background

from datatransform.models import Pipeline


@background(queue="api_res_operation")
def api_resource_query_task(p_id, api_source_id, request_id):
    print(api_source_id)
    pipeline_object = Pipeline.objects.get(pk=p_id)
    pipeline_object.status = "In Progress"
    query = f"""{{
  api_resource(api_resource_id: {api_source_id}) {{
    id
    title
    description
    issued
    modified
    status
    masked_fields
    dataset {{
      id
      title
      description
      issued
      remote_issued
      remote_modified
      period_from
      period_to
      update_frequency
      modified
      status
      remark
      funnel
      action
      access_type
      License
      }}
    url_path
    api_source {{
      id
      title
      base_url
      description
      api_version
      headers
      auth_loc
      auth_type
      auth_credentials
      auth_token
      apiresource_set
      {{
        id
        title
        description
      }}
    }}
    auth_required
    response_type
    }}
  }}
"""
    headers = {}
    request = requests.post('https://idpbe.civicdatalab.in/graphql', json={'query': query}, headers=headers)
    response = json.loads(request.text)
    base_url = response['data']['api_resource']['api_source']['base_url']
    url_path = response['data']['api_resource']['url_path']
    # # headers = response['data']['api_source']['headers']
    auth_loc = response['data']['api_resource']['api_source']['auth_loc'] #- header/param?
    auth_type = response['data']['api_resource']['api_source']['auth_type']  #if token/uname-pwd
    param = {}
    header = {}
    if auth_loc == "HEADER":
        if auth_type == "TOKEN":
            auth_token = response['data']['api_source']['auth_token']
            header = {"access_token":auth_token}
        elif auth_type == "CREDENTIAL":
            # [{key:username,value:dc, description:desc},{key:password,value:pass, description:desc}]
            auth_credentials = response['data']['api_source']['auth_credentials']  # - uname pwd
            uname_key = auth_credentials[0]['key']
            uname = auth_credentials[0]["value"]
            pwd_key = auth_credentials[1]['key']
            pwd = auth_credentials[1]["value"]
            header = {uname_key: uname, pwd_key: pwd}
    if auth_loc == "PARAM":
        if auth_type == "TOKEN":
            auth_token = response['data']['api_source']['auth_token']
            param = {"access_token":auth_token}
        elif auth_type == "CREDENTIAL":
            auth_credentials = response['data']['api_source']['auth_credentials'] #- uname pwd
            uname_key = auth_credentials[0]['key']
            uname = auth_credentials[0]["value"]
            pwd_key = auth_credentials[1]['key']
            pwd = auth_credentials[1]["value"]
            param = {uname_key: uname, pwd_key:pwd}
    response_type = response['data']['api_resource']['response_type']

    api_request = requests.get(base_url + "/" + url_path, headers=header, params=param)
    api_response = api_request.text
    if response_type == "JSON":
        print("in if...")
        with open(str(p_id) + "-data.json", 'w') as f:
            f.write(api_response)
        file_path = str(p_id) + "-data.json"
    if response_type == "CSV":
        with open(str(p_id) + "-data.csv", 'w') as f:
            f.write(api_response)
        file_path = str(p_id) + "-data.csv"
    status = "FETCHED"
    files = [
        ('0', (file_path, open(file_path, 'rb'), response_type))
    ]
    variables = {"file": None}

    map = json.dumps({"0": ["variables.file"]})

    file_upload_query = f"""
  mutation($file: Upload!) {{update_data_request(data_request: {{
  id: "{request_id}",
  status: {status},
  file: $file
  }}) {{
    success
    errors
    data_request {{
      id
      status
      description
      remark
      purpose
      file
    }}
  }}
}}"""
    print(file_upload_query)
    operations = json.dumps({
        "query": file_upload_query,
        "variables": variables
    })
    headers = {}
    try:
        response = requests.post('https://idpbe.civicdatalab.in/graphql', data={"operations": operations, "map": map},
                                 files=files, headers=headers)
        print(response.text)
    except Exception as e:
        print(e)
    finally:
        files[0][1][1].close()
        os.remove(file_path)
        pipeline_object.status = "Done"

