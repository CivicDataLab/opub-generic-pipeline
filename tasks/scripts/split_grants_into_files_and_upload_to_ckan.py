import json
import os
import re

import pandas as pd
import pika

from ckan_upload import CreateStatesDatasets

#from tasks.scripts.s3_utils import upload_result

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))

channel = connection.channel()
channel.exchange_declare(exchange='topic_logs', exchange_type='topic')
result = channel.queue_declare('', exclusive=False, durable=True)
queue_name = result.method.queue

print("queue name----", queue_name)
binding_key = "split_into_files_and_upload_to_ckan"

channel.queue_bind(exchange='topic_logs', queue=queue_name, routing_key=binding_key)


def split_into_files_and_upload_to_ckan(context, data_path):
    try:
        pattern = re.compile('[/$&()*^%#@!]+')
        data = pd.read_csv(data_path)
        print(data)
        data.to_csv("error-file.csv", index=False)
        is_exists = os.path.exists("Assam")
        print(is_exists, "***")
        if not is_exists:
            print("Inside existsststst")
            os.mkdir("Assam")
            os.mkdir("Assam/2023-24")
        file_path = "Assam/2023-24/"
        i = 0
        for grant in data['Grant Number'].unique():
            i += 1
            grant_num, grant_name = grant.split("-", 1)[0], grant.split("-", 1)[1]
            print(grant_num)
            print(grant_name)
            grant_name = grant_name.replace("-", " ")
            file_name = "Grant No. " + grant_num + "-" + grant_name
            file_name = pattern.sub('-', file_name).replace("- ", "-").replace(" -", "-")
            # Filter the dataframe using that column and value from the list

            data[data['Grant Number'] == grant].to_csv(file_path+file_name + ".csv", index=False)
            if i==1:
                break
        ckan_upload_obj = CreateStatesDatasets()
        print("created ckan obj.")
        ckan_upload_obj.create_docs_for_dir("https://openbudgetsindia.org/", "7e412837-f3ee-4f9d-b8ee-31f066acde5d",
                                     file_path, "assam")
    except Exception as e:
        return "Worker failed with an error - " + str(e)
    # return the transformed data
    return "Success"


def on_request(ch, method, props, body):
    # send the worker-alive message if the request message is -> get-ack
    if body.decode('utf-8') == 'get-ack':
        print("inside if..")
        ch.basic_publish(exchange="",
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(correlation_id=props.correlation_id, delivery_mode=2),
                         body='worker alive')
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        # if the message is other than "get-ack" then carryout the task
        task_details = json.loads(body)
        context = task_details["context"]
        data_path = task_details["data_path"]
        try:
            response = split_into_files_and_upload_to_ckan(context, data_path)
            # with open("xyz", "wb") as f:
            #     f.write(str(response_msg.text))
            #     s3_link = upload_result("xyz")
            ch.basic_publish(exchange="",
                             routing_key=props.reply_to,
                             properties=pika.BasicProperties(correlation_id=props.correlation_id,delivery_mode=2),
                             body=str(response))
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("[x] sent the response to the client..")
        except Exception as e:
            raise e


channel.basic_qos(prefetch_count=2)
channel.basic_consume(queue=queue_name, on_message_callback=on_request)

print(" [x] Awaiting RPC requests")

channel.start_consuming()
