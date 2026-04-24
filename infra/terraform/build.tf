data "archive_file" "api_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/api"
  output_path = "${path.module}/.build/api.zip"
}

data "archive_file" "ingest_worker_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/worker"
  output_path = "${path.module}/.build/ingest_worker.zip"
}

data "archive_file" "schedule_stub_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/scheduled"
  output_path = "${path.module}/.build/schedule_stub.zip"
}
