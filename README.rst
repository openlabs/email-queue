email-queue
===========

This module implements an email queue which acts as a transaction safe
buffer for tryton modules to send emails.

.. image:: https://travis-ci.org/openlabs/email-queue.svg?branch=develop
    :target: https://travis-ci.org/openlabs/email-queue

.. image:: https://coveralls.io/repos/openlabs/email-queue/badge.png
    :target: https://coveralls.io/r/openlabs/email-queue


Source code: https://github.com/openlabs/email-queue

Why should I use this module ?
------------------------------

Do you send emails from your tryton module ? Then you most probably need
this module. Here's why:

Transaction Safety
``````````````````

Consider the case where you are sending an Order confirmation email when
you click the confirm button. The transaction could roll back for a
variety of reasons after the email has been sent out to the customer. This
could be specially annoying if you sent an order number or other
information which could change, the second time you save the record - in
addition to the second time the second email that would spam the user.

This module solves the problem by buffering the email to a database table
within the same transaction. Later, a cron task clears out the email. If
the transaction was rolled back the would not be saved in the buffer too
and you would not have to do anything separate.

Performance
```````````

Depending on how your SMTP server is setup and the bandwidth of your
servers, the sending of an email takes way more time than a database
write. This creates blocking operations resulting in poor user experience
and your app would now need more workers to handle more such requests.
This module works around the problem by first buffering the email and then
having a separate cron task which clears out the email by actually sending
it.

Scalability
```````````

If you desire to be webscale like most of the internet aspires to be, you
would probably want to perform network bound operations like sending
emails from separate servers and scale using a message queue. This module
offers an API which lets you easily scale by subclassing the email.queue
model and changing the `send_all` implementation.

How do I install this module ?
------------------------------

Install from PyPI::

   pip install openlabs_email_queue

Install from source::

    git clone git@github.com:openlabs/email-queue
    python setup.py install

You can then install the module in your database.


How do I use this functionality in my modules ?
-----------------------------------------------

The module provides a convenient method which has the same signature as
python's `smtplib.SMTP.sendmail <https://docs.python.org/2/library/smtplib.html#smtplib.SMTP.sendmail>`_
method. This makes it easy to update your existing email sending code.

.. code-block:: python


    msg = MIMEText('This is the body')
    msg['Subject'] = 'An important email'
    msg['From'] = 'me@me.com'
    msg['To'] = 'you@you.com'

    EmailQueue = Pool().get('email.queue')
    EmailQueue.queue_mail(me, [you], msg.as_string())


If your transaction was successful, the email would be queued to be sent
and the mail would be sent out through the SMTP server when the cron runs
next time.

*The cron runs every 1 minute and you can change the frequency from cron
settings*

How do I configure the SMTP Server ?
------------------------------------

By default the emails are sent out using the smtp client provided by
Tryton. You can configure the settings for the same on your tryton
configuration file.

Authors and Contributors
------------------------

This module was built at `Openlabs <http://www.openlabs.co.in>`_. 

Professional Support
--------------------

This module is professionally supported by `Openlabs <http://www.openlabs.co.in>`_.
If you are looking for on-site teaching or consulting support, contact our
`sales <mailto:sales@openlabs.co.in>`_ and `support
<mailto:support@openlabs.co.in>`_ teams.
