# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool

from email_queue import EmailQueue


def register():
    Pool.register(
        EmailQueue,
        module='email_queue', type_='model'
    )
