from celery import Celery, current_task
from pymongo.errors import PyMongoError
from .database import db, retry_with_backoff_mongo
from .cache import redis_client, retry_with_backoff
from .logger import logger
import time
import random
from redis import RedisError

celery_app = Celery('tasks', broker='redis://redis:6379/0')

# Set the max_retries for the broker connection to 0
# celery_app.conf.broker_transport_options = {'max_retries': 0}


def index_line_task(line_content, line_number, total_lines):
    word_count = len(line_content.split())
    time.sleep(random.randint(0, 5))  # Simulated processing time
    logger.debug(f"Processed line {line_number}/{total_lines} with {word_count} words")


@celery_app.task(bind=True)
def process_line(self, job_id, line_content, line_number, total_lines):
    try:
        # Simulate the processing of a line
        index_line_task(line_content, line_number, total_lines)

        # Update MongoDB with the processed line and calculate progress
        update_result = retry_with_backoff_mongo(
            db.jobs.update_one,
            {"_id": job_id},
            {"$inc": {"processed_lines": 1}}
        )

        if update_result.matched_count:
            job = retry_with_backoff_mongo(
                db.jobs.find_one,
                {"_id": job_id}
            )

            processed_lines = job.get("processed_lines", 0)
            progress = (processed_lines / total_lines) * 100 if total_lines else 0
            
            # Conditionally update progress in MongoDB to reduce update frequency
            # Example condition: every 10 lines or on completion
            if processed_lines % 10 == 0 or progress >= 100:
                retry_with_backoff_mongo(
                    db.jobs.update_one,
                    {"_id": job_id},
                    {"$set": {"progress": progress}}
                )

                if progress >= 100:
                    retry_with_backoff_mongo(
                        db.jobs.update_one,
                        {"_id": job_id},
                        {"$set": {"status": "completed"}}
                    )

                # Update progress in Redis with retry logic
                retry_with_backoff(
                    redis_client.hset,
                    f"job:{job_id}",
                    mapping={"progress": progress, "processed_lines": processed_lines}
                )
        else:
            logger.warning(f"Job with job_id: {job_id} not found in MongoDB.")

    except (PyMongoError, RedisError) as e:
        logger.error(f"Error processing line {line_number} for job_id {job_id}: {e}")
        # Optionally, update the task state to reflect the failure
        current_task.update_state(state='FAILURE', meta={'exc': str(e)})
        # Consider adding a retry mechanism here if the task should be retried under certain conditions

@celery_app.task
def process_file(job_id, file_path):
    try:
        # Open the file to count the total number of lines
        with open(file_path, 'r') as file:
            total_lines = sum(1 for _ in file)

        # Wrap the MongoDB update operation with retry_with_backoff_mongo
        retry_with_backoff_mongo(
            db.jobs.update_one,
            {"_id": job_id},
            {"$set": {"total_lines": total_lines, "processed_lines": 0, "progress": 0}},
            upsert=True
        )

        # Now that the MongoDB document is updated, it's safe to dispatch process_line tasks
        with open(file_path, 'r') as file:
            for line_number, line_content in enumerate(file, start=1):
                process_line.delay(job_id, line_content.strip(), line_number, total_lines)

    except IOError as e:
        logger.error(f"Failed to process file for job {job_id}. Error: {e}")
        # Also wrap the error update in MongoDB with retry_with_backoff_mongo
        retry_with_backoff_mongo(
            db.jobs.update_one,
            {"_id": job_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )