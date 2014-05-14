# -*- coding: utf-8 -*-
"""
    tests/test_email_queue.py

    :copyright: (C) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys
import time
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
import unittest
import threading
import Queue

from mock import patch
from pretend import stub
from faker import Faker

from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from trytond import backend
import trytond.tests.test_tryton


class TestEmailQueue(unittest.TestCase):
    '''
    Test Email Queue
    '''

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('email_queue')

    @patch("smtplib.SMTP")
    def test_0010_send_mails(self, mock_smtp):
        """
        Tests send_mails functionality.
        """
        EmailQueue = POOL.get('email.queue')

        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            # Put some emails in queue
            f = Faker()
            for item in xrange(10):
                EmailQueue.queue_mail(f.email(), f.email(), f.text())

            transaction.cursor.commit()

            self.assertEqual(EmailQueue.search([], count=True), 10)
            self.assertEqual(
                EmailQueue.search([('state', '=', 'outbox')], count=True), 10
            )

        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            # Run cron method to send mails
            EmailQueue.send_all()

        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            self.assertEqual(
                EmailQueue.search([('state', '=', 'sent')], count=True), 10
            )

    def test_9999_transaction_safety(self):
        """
        Test the transaction safety of email sender.

        * This test is expected to work only on postgres
        * This should be the last test since this breaks the rule to commit
          within the test creating records
        """
        EmailQueue = POOL.get('email.queue')

        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            # Put some emails in queue
            f = Faker()
            for item in xrange(10):
                EmailQueue.queue_mail(f.email(), f.email(), f.text())

            transaction.cursor.commit()

        # A queue is used to handle the ones which errored.
        searialization_error_q = Queue.Queue(3)

        # A fake smtp server which just sleeps for 5 seconds when sendmail
        # is called.
        smtp_server = stub(sendmail=lambda *args: time.sleep(5))

        def threaded_send_email(email, smtp_server):
            """
            A new threaded email sender. This is required because there is
            no transaction in the new thread that is spawned and sendemail
            tries to create a new cursor from an existing transaction.

            So create the new transaction here, refresh the active record
            objects and call sendmail like the cron would have
            """
            with Transaction().start(DB_NAME, USER, CONTEXT):
                # email active record is from old transaction, so referesh it.
                email = EmailQueue(email.id)

                database = backend.get('database')

                try:
                    # Now send the email
                    email.send(smtp_server)
                except database.DatabaseOperationalError:
                    # This specific email could not be sent because of a
                    # transaction serialization error
                    searialization_error_q.put(email.id)

        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            email1, email2 = EmailQueue.search(
                [('state', '=', 'outbox')], limit=2
            )

        t1 = threading.Thread(
            target=threaded_send_email, args=(email1, smtp_server)
        )
        t2 = threading.Thread(
            target=threaded_send_email, args=(email2, smtp_server)
        )
        # create another thread with **email1** again. This is expected to
        # fail, though even t1 might fail and this would succeed. Either
        # way we dont care because we only make sure that there is 1
        # failure and that both email1 and 2 are sent.
        t3 = threading.Thread(
            target=threaded_send_email, args=(email1, smtp_server)
        )

        # start all the threads. Since there is a time.sleep of 5 seconds
        # in the sendmail call, it simulates a case of delayed execution.
        # thread3 is guaranteed to start within 5 seconds of thread1 and
        # the error that is asserted also specifically looks for a
        # concurrency triggered transaction serialisation exception.
        t1.start()
        t2.start()
        t3.start()

        # Blockingly wait till the threads complete
        t1.join()
        t2.join()
        t3.join()

        # 1: Assert that the email1's ID is in the serialization_error_q
        self.assertEqual(searialization_error_q.qsize(), 1)

        # 1B: Ensure that the ID is of email1 which was the one sent twice
        self.assertEqual(searialization_error_q.get(), email1.id)

        # 2: Assert that both email 1 and 2 have the sent state
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            self.assertEqual(EmailQueue(email1.id).state, 'sent')
            self.assertEqual(EmailQueue(email2.id).state, 'sent')

        # 3: Assert that there are 8 emails left in outbox
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            self.assertEqual(
                EmailQueue.search([('state', '=', 'outbox')], count=True), 8
            )


def suite():
    """
    Define suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestEmailQueue)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
