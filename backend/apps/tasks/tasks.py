import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _mark_processing(task_record_id: str):
    from .models import TaskRecord
    TaskRecord.objects.filter(id=task_record_id).update(
        status='processing', updated_at=timezone.now()
    )


def _mark_success(task_record_id: str, result: dict):
    from .models import TaskRecord
    TaskRecord.objects.filter(id=task_record_id).update(
        status='success',
        result=result,
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )


def _mark_failed(task_record_id: str, error: str, retry_count: int, max_retries: int):
    from .models import TaskRecord
    status = 'dead_letter' if retry_count >= max_retries else 'failed'
    TaskRecord.objects.filter(id=task_record_id).update(
        status=status,
        error=error,
        retry_count=retry_count,
        updated_at=timezone.now(),
    )
    return status


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def embed_document(self, document_id: str, task_record_id: str):
    _mark_processing(task_record_id)

    try:
        from apps.hr.models import Document
        from apps.agent.rag import RAGService

        doc = Document.objects.get(id=document_id)
        # idempotency guard — the task might be retried or re-queued by the nightly reindex job
        if doc.is_indexed:
            _mark_success(task_record_id, {'skipped': True, 'reason': 'already indexed'})
            return

        point_ids = RAGService.index_document(doc)
        doc.qdrant_point_ids = point_ids
        doc.is_indexed = True
        doc.save(update_fields=['qdrant_point_ids', 'is_indexed'])

        _mark_success(task_record_id, {'point_ids': point_ids, 'chunks': len(point_ids)})
        logger.info(f"Indexed document {document_id}: {len(point_ids)} chunks")

    except Exception as exc:
        from .models import TaskRecord

        record = TaskRecord.objects.filter(id=task_record_id).first()
        retry_count = self.request.retries + 1

        if self.request.retries < self.max_retries:
            # doubles each attempt: 30s → 60s → 120s
            # gives Qdrant/OpenAI time to recover without hammering a degraded service
            backoff = 2 ** self.request.retries * 30
            if record:
                _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)
            raise self.retry(exc=exc, countdown=backoff)
        else:
            if record:
                _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)
            logger.error(f"Document {document_id} hit dead-letter queue: {exc}")


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_agent_task(self, message: str, session_id: str, user_id: str, org_id: str, task_record_id: str):
    # runs the agent loop in a Celery worker so Django doesn't block a web worker
    # for the full Claude API round-trip (can be 5-30s on multi-tool chains)
    _mark_processing(task_record_id)

    try:
        from apps.core.models import User, Organization
        from apps.agent.agent import run_agent

        user = User.objects.get(id=user_id)
        org = Organization.objects.get(id=org_id)

        result = run_agent(message, session_id, user, org)
        _mark_success(task_record_id, result)

    except Exception as exc:
        from .models import TaskRecord

        record = TaskRecord.objects.filter(id=task_record_id).first()
        retry_count = self.request.retries + 1

        if self.request.retries < self.max_retries:
            backoff = 2 ** self.request.retries * 5
            if record:
                _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)
            raise self.retry(exc=exc, countdown=backoff)
        else:
            if record:
                _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)
            logger.error(f"Agent task {task_record_id} hit dead-letter: {exc}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_resume(self, resume_text: str, job_id: str, task_record_id: str):
    _mark_processing(task_record_id)

    try:
        import anthropic
        from django.conf import settings

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        from apps.hr.models import Job

        job = Job.objects.get(id=job_id)

        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1000,
            messages=[{
                'role': 'user',
                'content': (
                    f"Score this resume against the job requirements.\n\n"
                    f"Job: {job.title} - {job.department}\n"
                    f"Requirements: {job.requirements[:1000]}\n\n"
                    f"Resume:\n{resume_text[:2000]}\n\n"
                    f"Return JSON with: score (0-100), strengths (list), gaps (list), "
                    f"recommendation (hire/maybe/pass)"
                ),
            }],
        )

        result = {'raw': response.content[0].text, 'job_id': job_id}
        _mark_success(task_record_id, result)

    except Exception as exc:
        from .models import TaskRecord

        record = TaskRecord.objects.get(id=task_record_id)
        retry_count = self.request.retries + 1
        if self.request.retries < self.max_retries:
            backoff = 2 ** self.request.retries * 60
            _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)
            raise self.retry(exc=exc, countdown=backoff)
        else:
            _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)


@shared_task(bind=True, max_retries=5, default_retry_delay=10)
def send_notification(self, user_id: str, subject: str, body: str, task_record_id: str):
    # more retries than other tasks because a missed notification is a real user-visible failure,
    # while a missed embedding can be recovered by the nightly reindex job
    _mark_processing(task_record_id)
    try:
        logger.info(f"NOTIFICATION to user {user_id}: {subject}")
        _mark_success(task_record_id, {'sent': True, 'user_id': user_id})
    except Exception as exc:
        from .models import TaskRecord

        record = TaskRecord.objects.get(id=task_record_id)
        retry_count = self.request.retries + 1
        if self.request.retries < self.max_retries:
            _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)
            raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
        else:
            _mark_failed(task_record_id, str(exc), retry_count, record.max_retries)


@shared_task
def generate_report(report_types: list):
    logger.info(f"Generating nightly reports: {report_types}")


@shared_task
def reindex_stale_documents():
    # safety net for documents that failed embedding on first try —
    # catches transient qdrant/openai outages without needing manual intervention
    from apps.hr.models import Document

    stale = list(Document.objects.filter(is_indexed=False).exclude(content='')[:50])
    for doc in stale:
        embed_document.apply_async(
            kwargs={'document_id': str(doc.id), 'task_record_id': str(doc.id)},
            queue='embeddings',
        )
    logger.info(f"Queued {len(stale)} stale documents for re-indexing")
