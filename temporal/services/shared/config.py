"""
Shared configuration for all Temporal services.
"""

# Task Queue Names
TASK_QUEUE_ORCHESTRATION = "orchestration-q"
TASK_QUEUE_UPLOAD_PDF = "upload-pdf-q"
TASK_QUEUE_SPLIT_PDF = "split-pdf-q"
TASK_QUEUE_EXTRACT_INVOICE = "extract-invoice-q"
TASK_QUEUE_AGGREGATE_INVOICE = "aggregate-invoice-q"

# Activity Timeouts (seconds)
ACTIVITY_TIMEOUT = 30
ACTIVITY_RETRY_MAX_ATTEMPTS = 3

# Temporal Server Addresses
TEMPORAL_ADDRESS_DOCKER = "temporal:7233"
TEMPORAL_ADDRESS_LOCAL = "localhost:7233"
