import boto3
import asyncio
from botocore.exceptions import ClientError

DYNAMODB_ENDPOINT = "http://localhost:8089"
AWS_REGION = "ap-northeast-2"
AWS_ACCESS_KEY = "dummy"
AWS_SECRET_KEY = "dummy"

def create_tables():
    ddb = boto3.resource(
        'dynamodb',
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    tables_to_create = [
        {
            "TableName": "team_chats",
            "KeySchema": [
                {'AttributeName': 'project_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}   # Sort key
            ],
            "AttributeDefinitions": [
                {'AttributeName': 'project_id', 'AttributeType': 'N'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            "ProvisionedThroughput": {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        },
        {
            "TableName": "chat_rooms",
            "KeySchema": [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'room_id', 'KeyType': 'RANGE'}
            ],
            "AttributeDefinitions": [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'room_id', 'AttributeType': 'N'}
            ],
            "ProvisionedThroughput": {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        }
    ]

    print(f"Connecting to DynamoDB at {DYNAMODB_ENDPOINT}...")

    existing_tables = []
    try:
        existing_tables = list(ddb.tables.all())
        existing_names = [t.name for t in existing_tables]
        print(f"Existing tables: {existing_names}")
    except Exception as e:
        print(f"Error listing tables: {e}")
        return

    for table_config in tables_to_create:
        name = table_config["TableName"]
        if name in existing_names:
            print(f"Table '{name}' already exists. Skipping.")
            continue
        
        print(f"Creating table '{name}'...")
        try:
            ddb.create_table(**table_config)
            print(f"✅ Table '{name}' created successfully.")
        except ClientError as e:
            print(f"❌ Failed to create table '{name}': {e}")

if __name__ == "__main__":
    create_tables()
