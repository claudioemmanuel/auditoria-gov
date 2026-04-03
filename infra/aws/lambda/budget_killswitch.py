"""Budget kill-switch Lambda.

Triggered by SNS when CloudWatch billing alarm fires.
Stops all ECS services, RDS instance, and disables EventBridge schedules.
Manual restart required after trigger (intentional friction).
"""

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ecs = boto3.client("ecs")
rds = boto3.client("rds")
events = boto3.client("events")


def handler(event, context):
    cluster = os.environ["ECS_CLUSTER"]
    service = os.environ["ECS_SERVICE"]
    rds_id = os.environ["RDS_IDENTIFIER"]
    project = os.environ["PROJECT_NAME"]

    logger.info("BUDGET KILL-SWITCH TRIGGERED")
    logger.info("Event: %s", json.dumps(event))

    actions = []

    # 1. Stop ECS API service
    try:
        ecs.update_service(cluster=cluster, service=service, desiredCount=0)
        actions.append(f"ECS service {service} scaled to 0")
    except Exception as e:
        actions.append(f"Failed to stop ECS service: {e}")

    # 2. Stop running ECS tasks
    try:
        tasks = ecs.list_tasks(cluster=cluster)
        for task_arn in tasks.get("taskArns", []):
            ecs.stop_task(cluster=cluster, task=task_arn, reason="Budget kill-switch")
            actions.append(f"Stopped task {task_arn}")
    except Exception as e:
        actions.append(f"Failed to stop tasks: {e}")

    # 3. Stop RDS instance
    try:
        rds.stop_db_instance(DBInstanceIdentifier=rds_id)
        actions.append(f"RDS instance {rds_id} stopping")
    except Exception as e:
        actions.append(f"Failed to stop RDS: {e}")

    # 4. Disable EventBridge schedules
    try:
        rules = events.list_rules(NamePrefix=project)
        for rule in rules.get("Rules", []):
            events.disable_rule(Name=rule["Name"])
            actions.append(f"Disabled EventBridge rule {rule['Name']}")
    except Exception as e:
        actions.append(f"Failed to disable schedules: {e}")

    logger.info("Kill-switch actions: %s", actions)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Budget kill-switch executed",
            "actions": actions,
        }),
    }
