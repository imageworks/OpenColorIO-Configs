#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A process wrapper class that maintains the text output and execution status of
a process or a list of other process wrappers which carry such data.
"""

from __future__ import division

import os
import sys
import traceback

__author__ = 'ACES Developers'
__copyright__ = 'Copyright (C) 2014 - 2015 - ACES Developers'
__license__ = ''
__maintainer__ = 'ACES Developers'
__email__ = 'aces@oscars.org'
__status__ = 'Production'

__all__ = ['read_text',
           'write_text',
           'Process',
           'ProcessList',
           'main']


def read_text(text_file):
    """
    Object description.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # TODO: Investigate if check is needed.
    if not text_file:
        return

    with open(text_file, 'rb') as fp:
        text = (fp.read())

    return text


def write_text(text, text_file):
    """
    Object description.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    # TODO: Investigate if check is needed.
    if not text_file:
        return

    with open(text_file, 'wb') as fp:
        fp.write(text)

    return text


class Process:
    """
    A process with logged output.
    """

    def __init__(self,
                 description=None,
                 cmd=None,
                 args=None,
                 cwd=None,
                 env=None,
                 batch_wrapper=False):
        """
        Initialize the standard class variables.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        if args is None:
            args = []

        self.cmd = cmd
        if not description:
            self.description = cmd
        else:
            self.description = description
        self.status = None
        self.args = args
        self.start = None
        self.end = None
        self.log = []
        self.echo = True
        self.cwd = cwd
        self.env = env
        self.batch_wrapper = batch_wrapper
        self.process_keys = []

    def get_elapsed_seconds(self):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        import math

        if self.end and self.start:
            delta = (self.end - self.start)
            formatted = '%s.%s' % (delta.days * 86400 + delta.seconds,
                                   int(math.floor(delta.microseconds / 1e3)))
        else:
            formatted = None
        return formatted

    def write_key(self, write_dict, key=None, value=None, start_stop=None):
        """
        Writes a key / value pair in a supported format.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        if key is not None and (value is not None or start_stop is not None):
            indent = '\t' * write_dict['indentationLevel']
            if write_dict['format'] == 'xml':
                if start_stop == 'start':
                    write_dict['logHandle'].write('%s<%s>\n' % (indent, key))
                elif start_stop == 'stop':
                    write_dict['logHandle'].write('%s</%s>\n' % (indent, key))
                else:
                    write_dict['logHandle'].write(
                        '%s<%s>%s</%s>\n' % (indent, key, value, key))
            else:
                write_dict['logHandle'].write(
                    '%s%40s : %s\n' % (indent, key, value))

    def write_log_header(self, write_dict):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        import platform

        try:
            user = os.getlogin()
        except:
            try:
                user = os.getenv('USERNAME')
                if user is None:
                    user = os.getenv('USER')
            except:
                user = 'unknown_user'
        try:
            (sysname, nodename, release, version, machine,
             processor) = platform.uname()
        except:
            (sysname, nodename, release, version, machine, processor) = (
                'unknown_sysname', 'unknown_nodename', 'unknown_release',
                'unknown_version', 'unknown_machine', 'unknown_processor')

        self.write_key(write_dict, 'process', None, 'start')
        write_dict['indentationLevel'] += 1

        self.write_key(write_dict, 'description', self.description)
        self.write_key(write_dict, 'cmd', self.cmd)
        if self.args:
            self.write_key(write_dict, 'args', ' '.join(self.args))
        self.write_key(write_dict, 'start', self.start)
        self.write_key(write_dict, 'end', self.end)
        self.write_key(write_dict, 'elapsed', self.get_elapsed_seconds())

        self.write_key(write_dict, 'user', user)
        self.write_key(write_dict, 'sysname', sysname)
        self.write_key(write_dict, 'nodename', nodename)
        self.write_key(write_dict, 'release', release)
        self.write_key(write_dict, 'version', version)
        self.write_key(write_dict, 'machine', machine)
        self.write_key(write_dict, 'processor', processor)

        if len(self.process_keys) > 0:
            self.write_key(write_dict, 'processKeys', None, 'start')
            for pair in self.process_keys:
                (key, value) = pair
                write_dict['indentationLevel'] += 1
                self.write_key(write_dict, key, value)
                write_dict['indentationLevel'] -= 1
            self.write_key(write_dict, 'processKeys', None, 'stop')

        self.write_key(write_dict, 'status', self.status)

    def write_log_footer(self, write_dict):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        write_dict['indentationLevel'] -= 1
        self.write_key(write_dict, 'process', None, 'stop')

    def write_log(self,
                  log_handle=sys.stdout,
                  indentation_level=0,
                  format='xml'):
        """
        Writes logging information to the specified handle.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        write_dict = {}
        write_dict['logHandle'] = log_handle
        write_dict['indentationLevel'] = indentation_level
        write_dict['format'] = format

        if log_handle:
            self.write_log_header(write_dict)

            if self.log:
                self.write_key(write_dict, 'output', None, 'start')
                if format == 'xml':
                    log_handle.write('<![CDATA[\n')
                for line in self.log:
                    log_handle.write('%s%s\n' % ('', line))
                if format == 'xml':
                    log_handle.write(']]>\n')
                self.write_key(write_dict, 'output', None, 'stop')

            self.write_log_footer(write_dict)

    def write_log_to_disk(self, log_filename=None, format='xml', header=None):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        if log_filename:
            try:
                # TODO: Review statements.
                # 3.1
                try:
                    log_handle = (
                        open(log_filename, mode='wt', encoding='utf-8'))
                # 2.6
                except:
                    log_handle = open(log_filename, mode='wt')
            except:
                print('Couldn\'t open log : %s' % log_filename)
                log_handle = None

        if log_handle:
            if header:
                if format == 'xml':
                    log_handle.write('<![CDATA[\n')
                log_handle.write(header)
                if format == 'xml':
                    log_handle.write(']]>\n')
            self.write_log(log_handle, format=format)
            log_handle.close()

    def log_line(self, line):
        """
        Adds a line of text to the log.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        self.log.append(line.rstrip())
        if self.echo:
            print('%s' % line.rstrip())

    def execute(self):
        """
        Executes the current process.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        import datetime
        import traceback

        try:
            import subprocess as sp
        except:
            sp = None

        self.start = datetime.datetime.now()

        cmdargs = [self.cmd]
        cmdargs.extend(self.args)

        if self.echo:
            if sp:
                print(
                    '\n%s : %s\n' % (self.__class__, sp.list2cmdline(cmdargs)))
            else:
                print('\n%s : %s\n' % (self.__class__, ' '.join(cmdargs)))

        process = None
        tmp_wrapper = None
        stdout = None
        stdin = None
        parentenv = os.environ
        parentcwd = os.getcwd()

        try:
            # Using *subprocess*.
            if sp:
                if self.batch_wrapper:
                    cmd = ' '.join(cmdargs)
                    tmp_wrapper = os.path.join(self.cwd, 'process.bat')
                    write_text(cmd, tmp_wrapper)
                    print('%s : Running process through wrapper %s\n' % (
                        self.__class__, tmp_wrapper))
                    process = sp.Popen([tmp_wrapper], stdout=sp.PIPE,
                                       stderr=sp.STDOUT,
                                       cwd=self.cwd, env=self.env)
                else:
                    process = sp.Popen(cmdargs, stdout=sp.PIPE,
                                       stderr=sp.STDOUT,
                                       cwd=self.cwd, env=self.env)

            # using *os.popen4*.
            else:
                if self.env:
                    os.environ = self.env
                if self.cwd:
                    os.chdir(self.cwd)

                stdin, stdout = os.popen4(cmdargs, 'r')
        except:
            print('Couldn\'t execute command : %s' % cmdargs[0])
            traceback.print_exc()

        # Using *subprocess*
        if sp:
            if process is not None:
                # pid = process.pid
                # log.logLine('process id %s\n' % pid)

                try:
                    # This is more proper python, and resolves some issues with
                    # a process ending before all of its output has been
                    # processed, but it also seems to stall when the read
                    # buffer is near or over its limit. This happens
                    # relatively frequently with processes that generate lots
                    # of print statements.
                    for line in process.stdout:
                        self.log_line(line)

                    # So we go with the, um, uglier option below.

                    # This is now used to ensure that the process has finished.
                    line = ''
                    while line is not None and process.poll() is None:
                        try:
                            line = process.stdout.readline()
                        except:
                            break
                        # 3.1
                        try:
                            # TODO: Investigate previous eroneous statement.
                            # self.log_line(str(line, encoding='utf-8'))
                            self.log_line(str(line))
                        # 2.6
                        except:
                            self.log_line(line)
                except:
                    self.log_line('Logging error : %s' % sys.exc_info()[0])

                self.status = process.returncode

                if self.batch_wrapper and tmp_wrapper:
                    try:
                        os.remove(tmp_wrapper)
                    except:
                        print(
                            'Couldn\'t remove temp wrapper : %s' % tmp_wrapper)
                        traceback.print_exc()

        # Using *os.popen4*.
        else:
            exit_code = -1
            try:
                stdout_lines = stdout.readlines()
                # TODO: Investigate if this is the good behavior, close() does
                # not return anything / None.
                exit_code = stdout.close()

                stdout.close()
                stdin.close()

                if self.env:
                    os.environ = parentenv
                if self.cwd:
                    os.chdir(parentcwd)

                if len(stdout_lines) > 0:
                    for line in stdout_lines:
                        self.log_line(line)

                if not exit_code:
                    exit_code = 0
            except:
                self.log_line('Logging error : %s' % sys.exc_info()[0])

            self.status = exit_code

        self.end = datetime.datetime.now()


class ProcessList(Process):
    """
    A list of processes with logged output.
    """

    def __init__(self, description, blocking=True, cwd=None, env=None):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        Process.__init__(self, description, None, None, cwd, env)
        'Initialize the standard class variables'
        self.processes = []
        self.blocking = blocking

    def generate_report(self, write_dict):
        """
        Generates a log based on the success of the child processes.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        if self.processes:
            _status = True
            indent = '\t' * (write_dict['indentationLevel'] + 1)

            self.log = []

            for child in self.processes:
                if isinstance(child, ProcessList):
                    child.generate_report(write_dict)

                key = child.description
                value = child.status
                if write_dict['format'] == 'xml':
                    child_result = (
                        '%s<result description=\'%s\'>%s</result>' % (
                            indent, key, value))
                else:
                    child_result = ('%s%40s : %s' % (indent, key, value))
                self.log.append(child_result)

                if child.status != 0:
                    _status = False
            if not _status:
                self.status = -1
            else:
                self.status = 0
        else:
            self.log = ['No child processes available to generate a report']
            self.status = -1

    def write_log_header(self, write_dict):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        self.write_key(write_dict, 'processList', None, 'start')
        write_dict['indentationLevel'] += 1

        self.write_key(write_dict, 'description', self.description)
        self.write_key(write_dict, 'start', self.start)
        self.write_key(write_dict, 'end', self.end)
        self.write_key(write_dict, 'elapsed', self.get_elapsed_seconds())

        self.generate_report(write_dict)

        self.write_key(write_dict, 'status', self.status)

    def write_log_footer(self, write_dict):
        """
        Object description.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        write_dict['indentationLevel'] -= 1
        self.write_key(write_dict, 'processList', None, 'stop')

    def write_log(self,
                  log_handle=sys.stdout,
                  indentation_level=0,
                  format='xml'):
        """
        Writes logging information to the specified handle.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        write_dict = {}
        write_dict['logHandle'] = log_handle
        write_dict['indentationLevel'] = indentation_level
        write_dict['format'] = format

        if log_handle:
            self.write_log_header(write_dict)

            if self.log:
                self.write_key(write_dict, 'output', None, 'start')
                for line in self.log:
                    log_handle.write('%s%s\n' % ('', line))
                self.write_key(write_dict, 'output', None, 'stop')

            if self.processes:
                self.write_key(write_dict, 'processes', None, 'start')
                for child in self.processes:
                    child.write_log(log_handle, indentation_level + 1, format)
                self.write_key(write_dict, 'processes', None, 'stop')

            self.write_log_footer(write_dict)

    def execute(self):
        """
        Executes the list of processes.

        Parameters
        ----------
        parameter : type
            Parameter description.

        Returns
        -------
        type
             Return value description.
        """

        import datetime

        self.start = datetime.datetime.now()

        self.status = 0
        if self.processes:
            for child in self.processes:
                if child:
                    try:
                        child.execute()
                    except:
                        print('%s : caught exception in child class %s' % (
                            self.__class__, child.__class__))
                        traceback.print_exc()
                        child.status = -1

                    if self.blocking and child.status != 0:
                        print('%s : child class %s finished with an error' % (
                            self.__class__, child.__class__))
                        self.status = -1
                        break

        self.end = datetime.datetime.now()


def main():
    """
    Object description.

    Parameters
    ----------
    parameter : type
        Parameter description.

    Returns
    -------
    type
         Return value description.
    """

    import optparse

    p = optparse.OptionParser(description='A process logging script',
                              prog='process',
                              version='process 0.1',
                              usage=('%prog [options] '
                                     '[options for the logged process]'))
    p.add_option('--cmd', '-c', default=None)
    p.add_option('--log', '-l', default=None)

    options, arguments = p.parse_args()

    cmd = options.cmd
    log_filename = options.log

    try:
        args_start = sys.argv.index('--') + 1
        args = sys.argv[args_start:]
    except:
        args = []

    if cmd is None:
        print('process: No command specified')

    # Testing regular logging.
    process = Process(description='a process', cmd=cmd, args=args)

    # Testing report generation and writing a log.
    process_list = ProcessList('a process list')
    process_list.processes.append(process)
    process_list.echo = True
    process_list.execute()

    process_list.write_log_to_disk(log_filename)


if __name__ == '__main__':
    main()
