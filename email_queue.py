# -*- coding: utf-8 -*-
"""
    email_queue.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from email.message import Message

from trytond.model import ModelSQL, fields
from trytond.tools import get_smtp_server
from trytond.transaction import Transaction

__all__ = ['EmailQueue']


class EmailQueue(ModelSQL):
    """
    Email Queue
    """
    __name__ = "email.queue"

    from_addr = fields.Char("From Address", required=True)
    to_addrs = fields.Char("To Addresses", required=True)
    msg = fields.Text("Message", required=True)
    state = fields.Selection([
        ("outbox", "Outbox"),
        ("sending", "Sending"),
        ("sent", "Sent"),
    ], "State", required=True)

    @staticmethod
    def default_state():
        return "outbox"

    @classmethod
    def queue_mail(cls, from_addr, to_addrs, msg):
        """
        Add the message to the email queue

        :param from_addr: Address from which the email is sent
        :type from_addr: String
        :param to_addres: A string or a list of string addresses.
                          (a bare string will be treated as a list with 1
                          address)
        :param msg: RFC822 Message as a string or an instance of Message or
                    its subclasses from email.mime module
        """
        if isinstance(to_addrs, (list, tuple)):
            to_addrs = ','.join(to_addrs)

        if isinstance(msg, Message):
            msg = msg.as_string()

        return cls.create([{
            'from_addr': from_addr,
            'to_addrs': to_addrs,
            'msg': msg,
        }])

    def send(self, smtp_server):
        """
        Send this email with transaction safety using the given server
        """
        assert self.state == 'outbox', 'Only mails in outbox can be sent'

        with Transaction().new_cursor() as txn:
            try:
                self.write([self], {'state': 'sending'})
                smtp_server.sendmail(
                    self.from_addr, self.to_addrs.split(','), self.msg
                )
            except Exception:
                txn.cursor.rollback()
                raise
            else:
                self.write([self], {'state': 'sent'})
                txn.cursor.commit()

    @classmethod
    def send_all(cls):
        """
        Sends emails with the default SMTP server and marks them as sent.
        """
        server = get_smtp_server()

        for mail in cls.search([('state', '=', 'outbox')]):
            mail.send(server)

        server.quit()
