README

1. Create a new IAM Role named Snapshot-Management from the Snapshot-Management.json file
2. Install the Snapshot-Create function and set the timeout to 1 minute - Python 2.7
3. Install the Snapshot-Delete function and set the timeout to 30 seconds - Python 2.7
4. Configure CloudWatch to schedule the lambda functions with this cron expression '0 2 * * ? *'
5. Select the targets of the CloudWatch schedule to Snapshot-Create & Snapshot-Delete
6. Name the CloudWatch event '2AM-UTC' with the description of 'Runs jobs at 2AM UTC'