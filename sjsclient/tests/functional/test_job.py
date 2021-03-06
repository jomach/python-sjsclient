# -*- coding: utf-8 -*-
import sys
import time
import uuid

from sjsclient import exceptions
from sjsclient.tests.functional import base

test_conf = {"param": "value"}


class TestFunctionalJob(base.TestFunctionalSJS):
    def setUp(self):
        super(TestFunctionalJob, self).setUp()

    def _create_app(self):
        app_name = str(uuid.uuid4())
        test_app = self.client.apps.create(app_name, self.jar_blob)
        return (app_name, test_app)

    def _create_job(self, app, class_path, conf=None, ctx=None):
        job = None
        while not job:
            try:
                job = self.client.jobs.create(app, class_path,
                                              conf=conf, ctx=ctx)
            except exceptions.HttpException as exc:
                if not ("NO SLOTS AVAILABLE" in str(exc)):
                    raise
        return job

    def test_job_create(self):
        (app_name, test_app) = self._create_app()
        class_path = "spark.jobserver.VeryShortDoubleJob"
        job = self._create_job(test_app, class_path,
                               ctx=self._get_functional_context())
        time.sleep(3)
        self.assertTrue(len(job.jobId) > 0)
        self.assertTrue(job.status == "STARTED")
        self._wait_till_job_is_done(job)

    def test_job_result(self):
        (app_name, test_app) = self._create_app()
        class_path = "spark.jobserver.VeryShortDoubleJob"
        job = self.client.jobs.create(test_app, class_path,
                                      ctx=self._get_functional_context())
        time.sleep(3)
        self._wait_till_job_is_done(job)
        job = self.client.jobs.get(job.jobId)
        self.assertEqual("FINISHED", job.status)
        self.assertEqual([2, 4, 6], job.result)

    def test_job_result_with_conf(self):
        (app_name, test_app) = self._create_app()
        conf = "stress.test.longpijob.duration = 1"
        class_path = "spark.jobserver.LongPiJob"
        job = self._create_job(test_app, class_path,
                               conf=conf,
                               ctx=self._get_functional_context())
        time.sleep(3)
        created_job = self.client.jobs.get(job.jobId)
        self.assertEqual(job.jobId, created_job.jobId)
        status = created_job.status
        self.assertTrue(status == "RUNNING" or status == "FINISHED")
        self._wait_till_job_is_done(created_job)
        job = self.client.jobs.get(job.jobId)
        self.assertEqual("FINISHED", job.status)
        sys.stderr.write("duration %s" % job.duration)
        self.assertTrue("1." in job.duration)

    def _wait_till_job_is_done(self, job):
        while job.status != "FINISHED":
            time.sleep(2)
            job = self.client.jobs.get(job.jobId)

    def test_job_delete(self):
        (app_name, test_app) = self._create_app()
        conf = "stress.test.longpijob.duration = 5"
        class_path = "spark.jobserver.LongPiJob"
        job = self.client.jobs.create(test_app, class_path,
                                      conf=conf,
                                      ctx=self._get_functional_context())
        time.sleep(3)
        resp = self.client.jobs.delete(job.jobId)
        self.assertEqual(200, resp.status_code)
        resp = resp.json()
        self.assertEqual("KILLED", resp["status"])

    def test_job_delete_non_existing(self):
        self.assertRaises(exceptions.NotFoundException,
                          self.client.jobs.delete, 'does-not-exist')

    def test_job_delete_completed_job(self):
        (app_name, test_app) = self._create_app()
        class_path = "spark.jobserver.VeryShortDoubleJob"
        job = self.client.jobs.create(test_app, class_path,
                                      ctx=self._get_functional_context())
        time.sleep(3)
        self._wait_till_job_is_done(job)
        self.assertRaises(exceptions.NotFoundException,
                          self.client.jobs.delete, job.jobId)
