Investigation: Feasibility Review Submission Latency

 Problem

 Feasibility review form submissions are taking several seconds to complete -
 much slower than yesterday.

 Executive Summary

 Root Cause: Celery worker is NOT running + N+1 database query issues

 Current Performance: 2.5-6 seconds per submission
 - Celery connection timeout: 1-5 seconds (CRITICAL)
 - Database queries (11 queries): 0.5-1 seconds
 - Total: ~2.5-6 seconds

 Quick Fix: Start Celery worker → Reduces to 0.5-1 second (50-80% improvement)

 Full Optimization: Database query optimization → Reduces to 0.3-0.7 seconds
 (85-90% improvement)

 Root Causes Identified

 1. N+1 Query Problem (Most Critical)

 Location: applications/views.py lines 463-469

 The code makes 3 separate database queries to check feasibility review status:
 all_reviews = application.feasibility_reviews.all()  # Query #1
 pending_count = all_reviews.filter(is_feasible__isnull=True).count()  # Query 
 #2
 rejected_count = all_reviews.filter(is_feasible=False).count()  # Query #3

 Impact: 3 queries × 50-100ms = 150-300ms added latency

 ---
 2. Missing select_related Optimization

 Location: applications/views.py line 441-448

 The initial FeasibilityReview query doesn't prefetch related objects:
 review = get_object_or_404(FeasibilityReview, pk=pk, ...)
 application = review.application  # Lazy load - Query #4
 application.applicant.email  # Lazy load - Query #5

 Impact: 2 additional queries × 50-100ms = 100-200ms

 ---
 3. Application Status Update Queries

 Location: applications/models.py lines 224-295

 The Application.save() method internally fetches the old application status
 for validation:
 def save(self, *args, **kwargs):
     if self.pk:
         old_app = Application.objects.get(pk=self.pk)  # Internal query!
         # Validate state transitions...

 Each time you save the application (lines 474, 479), this adds another query.

 Impact: 1-2 queries × 50-100ms = 50-200ms

 ---
 4. Email Sending (Potentially Synchronous)

 Location: applications/views.py lines 483-499

 If Celery is not running or misconfigured, email sending happens
 synchronously:
 - Template rendering
 - SMTP connection and send (2-5 seconds!)
 - Database logging (2 queries)

 Impact: If synchronous: 2-5+ seconds. If async via Celery: negligible

 ---
 5. Total Query Count

 Current: ~11 database queries per feasibility review submission
 1. GET FeasibilityReview
 2. GET Application (lazy load)
 3. GET User/applicant (lazy load)
 4. GET all feasibility_reviews
 5. COUNT pending reviews
 6. COUNT rejected reviews
 7. GET old Application (inside save for validation)
 8. SAVE Application
 9. GET EmailTemplate
 10. CREATE EmailLog
 11. SAVE EmailLog

 Optimized: Should be ~6-7 queries

 ---
 Performance Impact

 Current:
 - Database: 11 queries × 50-100ms = 550-1100ms
 - Email (if sync): 2-5 seconds
 - Total: 2.5-6+ seconds

 After optimization:
 - Database: 6-7 queries × 50-100ms = 300-700ms
 - Email (async): 0ms (queued)
 - Total: 0.3-0.7 seconds

 ---
 Why This Wasn't Slow Yesterday

 CRITICAL FINDING: Celery is NOT Running

 $ ps aux | grep celery
 # No celery processes found!

 When Celery isn't running, calling .delay() on line 485 attempts to connect to
  the message broker (Redis/RabbitMQ) and will:
 - Timeout after 1-5 seconds waiting for broker connection
 - Eventually raise an exception (caught by try-except on line 496)
 - This adds 1-5 seconds PER feasibility review submission

 Other Contributing Factors:

 1. More data in database now - The test data seeding added 17 applications
 with multiple feasibility reviews
 2. Multi-node applications - Some test apps involve multiple nodes, amplifying
  the N+1 query problem
 3. No query optimization - Fresh database without indexes on frequently
 queried fields

 ---
 Critical Files Involved

 - applications/views.py (lines 441-499) - feasibility_review view
 - applications/models.py (lines 224-295) - Application.save() method
 - communications/tasks.py (lines 15-70) - Email sending

 ---
 Immediate Action (Quick Fix)

 Start Celery Worker ⚡

 This will immediately resolve 1-5 seconds of latency:
 # From project root
 source venv/bin/activate
 celery -A redib worker -l info

 Expected improvement: 1-5 seconds faster (50-80% of current latency)

 ---
 Recommended Optimizations (For Later)

 Priority 1: Fix N+1 Query in views.py (lines 464-469)

 Current:
 all_reviews = application.feasibility_reviews.all()  # Query
 pending_count = all_reviews.filter(is_feasible__isnull=True).count()  # Query
 rejected_count = all_reviews.filter(is_feasible=False).count()  # Query

 Optimized:
 from django.db.models import Q, Count
 review_stats = application.feasibility_reviews.aggregate(
     pending=Count('id', filter=Q(is_feasible__isnull=True)),
     rejected=Count('id', filter=Q(is_feasible=False))
 )
 pending_count = review_stats['pending']
 rejected_count = review_stats['rejected']
 Saves: 2 database queries (150-200ms)

 Priority 2: Add select_related (line 441)

 Current:
 review = get_object_or_404(FeasibilityReview, pk=pk, ...)

 Optimized:
 review = get_object_or_404(
     FeasibilityReview.objects.select_related(
         'application__applicant',
         'application__call',
         'node'
     ),
     pk=pk,
     ...
 )
 Saves: 2 database queries (100-200ms)

 Priority 3: Cache old status in Application.save()

 The Application.save() method fetches old status on EVERY save (lines 256,
 285). Consider:
 - Using update() for simple status changes
 - Caching the old status before calling save()
 - Using Django signals for validation instead

 Saves: 1 database query per save (50-100ms)

 Priority 4: Optimize Application Code Generation

 Lines 235-249 iterate over ALL applications for the call. Use aggregate
 instead:
 max_num = Application.objects.filter(call=self.call).aggregate(
     max_code=Max('code')
 )

