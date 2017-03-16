import boto3
import time
from datetime import datetime, timedelta


# Function that will convert a EC2 object list to a dict format
def make_tag_dict(ec2_object):
    # Given an tagable ec2_object, return dictionary of existing tags
    # From https://github.com/boto/boto3/issues/264#issuecomment-148735429
    tag_dict = {}
    if ec2_object['Tags'] is None:
        return tag_dict
    for tag in ec2_object['Tags']:
        tag_dict[tag['Key']] = tag['Value']
    return tag_dict


# Delete Snapshot function
def delete_snapshots(ec2, aws_account_number):
    # Define function variables
    deletion_counter = 0
    size_counter = 0

    while True:
            try:
                snapshots = ec2.describe_snapshots(
                    DryRun=False,
                    OwnerIds=[
                        aws_account_number,
                    ],
                    Filters=[
                        {
                            'Name': 'tag:Delete_On',
                            'Values': [
                                '*',
                            ]
                        },
                    ]
                )['Snapshots']
                break
            except Exception as e:
                print(e)
                time.sleep(1)

    for ebs_snapshot in snapshots:
        ebs_snapshot_tags = make_tag_dict(ebs_snapshot)
        if ebs_snapshot_tags.get('Delete_On') <= datetime.utcnow().strftime('%Y-%m-%d'):
            print('Deleting {id}'.format(id=ebs_snapshot['Description']))
            print(ebs_snapshot['VolumeId'])
            deletion_counter += 1
            size_counter = size_counter + ebs_snapshot['VolumeSize']

            # Delete the actual snapshot
            while True:
                try:
                    ec2.delete_snapshot(
                        DryRun=False,
                        SnapshotId=ebs_snapshot['SnapshotId']
                    )
                    break
                except Exception as e:
                    print(e)
                    time.sleep(1)

    print(
        'Deleted {number} snapshots totalling {size} GB'.format(
            number=deletion_counter,
            size=size_counter))


# Lambda Handler function
def lambda_handler(event, context):
    # Build EC2 connection
    while True:
        try:
            ec2 = boto3.client(
                'ec2'
            )
            break
        except Exception as e:
            print(e)
            time.sleep(1)

    reservations = ec2.describe_instances().get(
        'Reservations', []
    )

    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
            ], [])

    print('Found', (len(instances)), 'instances')

    print('Executing Delete function, time is now', datetime.utcnow().strftime('%HH:%MM:%SS %m-%dd-%yy'))
    account_number = context.invoked_function_arn.split(':')[4]  # Used to find snapshots owned by this account
    print('Finding snapshots under account number:', account_number)
    delete_snapshots(ec2, account_number)
