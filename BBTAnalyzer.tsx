aws dynamodb put-item `
  --table-name FileProcessingJobs `
  --item '{\"user_id\": {\"S\": \"user001\"}, \"job_id\": {\"S\": \"job-001\"}, \"status\": {\"S\": \"pending\"}, \"filename\": {\"S\": \"data.csv\"}, \"created_at\": {\"S\": \"2025-07-22T17:30:00Z\"}}' `
  --region ap-southeast-2