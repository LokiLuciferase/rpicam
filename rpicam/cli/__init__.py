#!/usr/bin/env python3
import click


def click_option(*args, **kwargs):
    if not 'show_default' in kwargs:
        kwargs.update({'show_default': True})
    return click.option(*args, **kwargs)

