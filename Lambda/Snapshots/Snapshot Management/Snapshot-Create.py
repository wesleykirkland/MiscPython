import boto3
import time
from datetime import datetime, timedelta

# Define Global variables
retention_days = 30  # How long to maintain backups


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


# Snapshot create function
def create_snapshots(instances, ec2):
    for instance in instances:
        instance_tags = make_tag_dict(instance)

        for device in instance['BlockDeviceMappings']:
            # Check and make sure the device type is Ebs so we can snapshot it
            if device.get('Ebs', None) is None:
                continue

            # Define variables for the device loop
            volume_id = device['Ebs']['VolumeId']
            snap_name = instance_tags.get('Name') + '(' + device['DeviceName'] + '-' + volume_id + ')'
            description = 'Created by autosnap script, volume %s on instance %s on %s' % (
                volume_id, instance['InstanceId'],
                datetime.utcnow().strftime('%d-%m-%Y %H:%M:%S')
            )

            print('Found EBS volume %s on instance %s' % (volume_id, instance['InstanceId']))

            # Get more detailed volume information
            device_info = ec2.describe_volumes(
                DryRun=False,
                VolumeIds=[
                    device['Ebs']['VolumeId']
                ]
            )

            if 'Tags' in device_info['Volumes'][0].keys():
                device_tags = make_tag_dict(device_info['Volumes'][0])  # Get the device tags
                # Check and see if the volume is not supposed to be snapshotted
                if device_tags.get('Snapshot'):
                    if device_tags.get('Snapshot').upper() == 'FALSE':
                        print(volume_id, 'is scheduled to not be snapshotted, moving onto the next device')
                        continue

            while True:
                try:
                    snapshot = ec2.create_snapshot(VolumeId=volume_id, Description=description)
                    break
                except Exception as e:
                    print(e)
                    time.sleep(1)

            print('Retaining snapshot %s of volume %s from instance %s for %d days' % (
                snapshot['SnapshotId'],
                volume_id,
                instance['InstanceId'],
                retention_days,
            )
                  )

            # Apply the Name, Retention_Days, Delete on tag(s)
            while True:
                try:
                    ec2.create_tags(
                        Resources=[snapshot['SnapshotId']],
                        Tags=[
                            {'Key': 'Name', 'Value': snap_name},
                            {'Key': 'Retention_Days', 'Value': str(retention_days)},
                            {'Key': 'Delete_On', 'Value': datetime.strftime(datetime.utcnow() + timedelta(days=retention_days), '%Y-%m-%d')},
                        ]
                    )
                    break
                except Exception as e:
                    print(e)
                    time.sleep(1)


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

    print('Executing Backup function, time is now', datetime.utcnow().strftime('%HH:%MM:%SS %m-%dd-%yy'))
    create_snapshots(instances, ec2)
