import os
import uuid
from datetime import datetime

import boto3


DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]
SQS_QUEUE_NAME = os.environ["SQS_QUEUE_NAME"]


task_id = str(uuid.uuid4())
dynamodb_table = boto3.resource("dynamodb").Table(DYNAMODB_TABLE_NAME)
dynamodb_table.put_item(
    Item={
        "type": "initialization",
        "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task_id": task_id,
    },
)
sqs_resource = boto3.resource("sqs")
sqs_queue = sqs_resource.get_queue_by_name(QueueName=SQS_QUEUE_NAME)


def read_sqs_message_and_write_dynamodb_record():
    for message in sqs_queue.receive_messages(
        MaxNumberOfMessages=1, WaitTimeSeconds=10
    ):
        body = message.body
        print(
            "body:", body, flush=True
        )  # need flush=True or else print stays in buffer
        if "Error" in body:
            dynamodb_table.put_item(
                Item={
                    "type": "error",
                    "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "body": body,
                    "task_id": task_id,
                },
            )
            message.delete()
            raise eval(body)("raised exception")
        else:
            dynamodb_table.put_item(
                Item={
                    "type": "message",
                    "datetime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "body": body,
                    "task_id": task_id,
                },
            )
            message.delete()


def main():
    while True:
        read_sqs_message_and_write_dynamodb_record()


main()
