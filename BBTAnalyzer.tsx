record_id,user_id,category,amount,timestamp
rec001,user001,groceries,125.50,2025-07-21T10:15:00Z
rec002,user001,electronics,899.99,2025-07-21T11:30:00Z
rec003,user002,clothing,59.90,2025-07-22T08:45:00Z

aws s3 cp .\data.csv s3://my-file-uploads-bucket/uploads/user001/data.csv --region ap-southeast-2

aws dynamodb put-item --table-name FileProcessingJobs --item '{
  "user_id": {"S": "user001"},
  "job_id": {"S": "job-001"},
  "status": {"S": "pending"},
  "filename": {"S": "data.csv"},
  "s3_path": {"S": "s3://my-file-uploads-bucket/uploads/user001/data.csv"},
  "created_at": {"S": "2025-07-22T10:00:00Z"}
}' --region ap-southeast-2

aws dynamodb delete-item --table-name FileProcessingJobs --key "{\"job_id\": {\"S\": \"job-001\"}, \"user_id\": {\"S\": \"user001\"}}" --region ap-southeast-2

aws dynamodb scan --table-name FileProcessingJobs --region ap-southeast-2