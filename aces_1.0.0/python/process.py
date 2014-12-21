#!/usr/bin/python2.6

'''A process wrapper class that maintains the text output and execution status of a process
or a list of other process wrappers which carry such data.'''

import os
import sys
import traceback

def readText(textFile):
    if( textFile != "" ):
        fp = open(textFile, 'rb')
        # Create a text/plain message
        text = (fp.read())
        fp.close()
    return text
# readText

def writeText(text, textFile):
    if( textFile != "" ):
        fp = open(textFile, 'wb')
        # Create a text/plain message
        fp.write(text)
        fp.close()
    return text
# readText

class Process:
    "A process with logged output"

    def __init__(self, description=None, cmd=None, args=[], cwd=None, env=None, batchWrapper=False):
        "Initialize the standard class variables"
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
        self.batchWrapper = batchWrapper
        self.processKeys = []
    # __init__

    def getElapsedSeconds(self):
        import math
        if self.end and self.start:
            delta = (self.end - self.start)
            formatted = "%s.%s" % (delta.days * 86400 + delta.seconds, int(math.floor(delta.microseconds/1e3)))
        else:
            formatted = None
        return formatted
    # getElapsedtime

    def writeKey(self, writeDict, key=None, value=None, startStop=None):
        "Write a key, value pair in a supported format"
        if key != None and (value != None or startStop != None):
            indent = '\t'*writeDict['indentationLevel']
            if writeDict['format'] == 'xml':
                if startStop == 'start':
                    writeDict['logHandle'].write( "%s<%s>\n" % (indent, key) )
                elif startStop == 'stop':
                    writeDict['logHandle'].write( "%s</%s>\n" % (indent, key) )
                else:
                    writeDict['logHandle'].write( "%s<%s>%s</%s>\n" % (indent, key, value, key) )
            else: # writeDict['format'] == 'txt':
                writeDict['logHandle'].write( "%s%40s : %s\n" % (indent, key, value) )

    def writeLogHeader(self, writeDict):
        import platform

        # Retrieve operating environment information
        user = None
        try:
            user = os.getlogin()
        except:
            try:
                user = os.getenv("USERNAME")
                if user == None:
                    user = os.getenv("USER")
            except:
                user = "unknown_user"
        try:
            (sysname, nodename, release, version, machine, processor) = platform.uname()
        except:
            (sysname, nodename, release, version, machine, processor) = ("unknown_sysname", "unknown_nodename", "unknown_release", "unknown_version", "unknown_machine", "unknown_processor")
        try:
            hostname = platform.node()
        except:
            hostname = "unknown_hostname"

        self.writeKey(writeDict, 'process', None, 'start' )
        writeDict['indentationLevel'] += 1

        self.writeKey(writeDict, 'description', self.description )
        self.writeKey(writeDict, 'cmd', self.cmd )
        if self.args: self.writeKey(writeDict, 'args', ' '.join(self.args) )
        self.writeKey(writeDict, 'start', self.start )
        self.writeKey(writeDict, 'end', self.end )
        self.writeKey(writeDict, 'elapsed', self.getElapsedSeconds() )

        self.writeKey(writeDict, 'user', user )
        self.writeKey(writeDict, 'sysname', sysname )
        self.writeKey(writeDict, 'nodename', nodename )
        self.writeKey(writeDict, 'release', release )
        self.writeKey(writeDict, 'version', version )
        self.writeKey(writeDict, 'machine', machine )
        self.writeKey(writeDict, 'processor', processor )

        if len(self.processKeys) > 0:
            self.writeKey(writeDict, 'processKeys', None, 'start' )
            for pair in self.processKeys:
                (key, value) = pair
                writeDict['indentationLevel'] += 1
                self.writeKey(writeDict, key, value )
                writeDict['indentationLevel'] -= 1
            self.writeKey(writeDict, 'processKeys', None, 'stop' )

        self.writeKey(writeDict, 'status', self.status )
    # writeLogHeader

    def writeLogFooter(self, writeDict):
        writeDict['indentationLevel'] -= 1
        self.writeKey(writeDict, 'process', None, 'stop' )
    # writeLogFooter

    def writeLog(self, logHandle=sys.stdout, indentationLevel=0,format='xml'):
        "Write logging information to the specified handle"
        
        writeDict = {}
        writeDict['logHandle'] = logHandle
        writeDict['indentationLevel'] = indentationLevel
        writeDict['format'] = format
        
        if logHandle:
            self.writeLogHeader(writeDict)
            
            if self.log:
                self.writeKey(writeDict, 'output', None, 'start' )
                if format == 'xml':
                    logHandle.write( "<![CDATA[\n" )
                for line in self.log:
                    logHandle.write( '%s%s\n' % ("", line) )
                if format == 'xml':
                    logHandle.write( "]]>\n" )
                self.writeKey(writeDict, 'output', None, 'stop' )

            self.writeLogFooter(writeDict)
    # writeLog

    def writeLogToDisk(self, logFilename=None, format='xml', header=None):
        if logFilename: 
            try:
                # This also doesn't seem like the best structure...
                # 3.1
                try:
                    logHandle = open( logFilename, mode='wt', encoding="utf-8")
                # 2.6
                except:
                    logHandle = open( logFilename, mode='wt')
            except:
                print( "Couldn't open log : %s" % logFilename )
                logHandle = None

        if logHandle:
            if header:
                if format == 'xml':
                    logHandle.write( "<![CDATA[\n" )
                logHandle.write( header )
                if format == 'xml':
                    logHandle.write( "]]>\n" )
            self.writeLog(logHandle)
            logHandle.close()
    # writeLogToDisk

    def logLine(self, line):
        "Add a line of text to the log"
        self.log.append( line.rstrip() )
        if self.echo:
            print( "%s" % line.rstrip() )
    # logLine

    def execute(self):
        "Execute this process"
        import re
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
                print( "\n%s : %s\n" % (self.__class__, sp.list2cmdline(cmdargs)) )
            else:
                print( "\n%s : %s\n" % (self.__class__, " ".join(cmdargs)) )

        # intialize a few variables that may or may not be set later
        process = None
        tmpWrapper = None
        stdout = None
        stdin = None
        parentenv = os.environ
        parentcwd = os.getcwd()

        try:
            # Using subprocess
            if sp:
                if self.batchWrapper:
                    cmd = " ".join(cmdargs)
                    tmpWrapper = os.path.join(self.cwd, "process.bat")
                    writeText(cmd, tmpWrapper)
                    print( "%s : Running process through wrapper %s\n" % (self.__class__, tmpWrapper) )
                    process = sp.Popen([tmpWrapper], stdout=sp.PIPE, stderr=sp.STDOUT, 
                        cwd=self.cwd, env=self.env)
                else:
                    process = sp.Popen(cmdargs, stdout=sp.PIPE, stderr=sp.STDOUT, 
                        cwd=self.cwd, env=self.env)

            # using os.popen4
            else:
                if self.env:
                    os.environ = self.env
                if self.cwd:
                    os.chdir( self.cwd )
                
                stdin, stdout = os.popen4( cmdargs, 'r')
        except:
            print( "Couldn't execute command : %s" % cmdargs[0] )
            traceback.print_exc()

        # Using subprocess
        if sp:
            if process != None:
                #pid = process.pid
                #log.logLine( "process id %s\n" % pid )

                try:
                    # This is more proper python, and resolves some issues with a process ending before all
                    #  of its output has been processed, but it also seems to stall when the read buffer
                    #  is near or over it's limit. this happens relatively frequently with processes
                    #  that generate lots of print statements.
                    #
                    for line in process.stdout:
                        self.logLine(line)
                    #
                    # So we go with the, um, uglier  option below

                    # This is now used to ensure that the process has finished
                    line = ""
                    while line != None and process.poll() == None:
                        try:
                            line = process.stdout.readline()
                        except:
                            break
                        # 3.1
                        try:
                            self.logLine( str(line, encoding="utf-8") )
                        # 2.6
                        except:
                            self.logLine( line )
                except:
                    self.logLine( "Logging error : %s" % sys.exc_info()[0] )

                self.status = process.returncode
                
                if self.batchWrapper and tmpWrapper:
                    try:
                        os.remove(tmpWrapper)
                    except:
                        print( "Couldn't remove temp wrapper : %s" % tmpWrapper )
                        traceback.print_exc()

        # Using os.popen4
        else:
            exitCode = -1
            try:
                #print( "reading stdout lines" )
                stdoutLines = stdout.readlines()
                exitCode = stdout.close()

                stdout.close()
                stdin.close()

                if self.env:
                    os.environ = parentenv
                if self.cwd:
                    os.chdir( parentcwd )
                
                if len( stdoutLines ) > 0:
                    for line in stdoutLines:
                        self.logLine(line)

                if not exitCode:
                    exitCode = 0
            except:
                self.logLine( "Logging error : %s" % sys.exc_info()[0] )

            self.status = exitCode
            
        self.end = datetime.datetime.now()
    #execute
# Process

class ProcessList(Process):
    "A list of processes with logged output"

    def __init__(self, description, blocking=True, cwd=None, env=None):
        Process.__init__(self, description, None, None, cwd, env)
        "Initialize the standard class variables"
        self.processes = []
        self.blocking = blocking
    # __init__

    def generateReport(self, writeDict):
        "Generate a log based on the success of the child processes"
        if self.processes:
            _status = True
            indent = '\t'*(writeDict['indentationLevel']+1)
            
            self.log = []
            
            for child in self.processes:
                if isinstance(child, ProcessList):
                    child.generateReport(writeDict)
                
                childResult = ""
                key = child.description
                value = child.status
                if writeDict['format'] == 'xml':
                    childResult = ( "%s<result description=\"%s\">%s</result>" % (indent, key, value) )
                else: # writeDict['format'] == 'txt':
                    childResult = ( "%s%40s : %s" % (indent, key, value) )
                self.log.append( childResult )
                
                if child.status != 0:
                    _status = False
            if not _status:
                self.status = -1
            else:
                self.status = 0
        else:
            self.log = ["No child processes available to generate a report"]
            self.status = -1

    def writeLogHeader(self, writeDict):
        self.writeKey(writeDict, 'processList', None, 'start' )
        writeDict['indentationLevel'] += 1

        self.writeKey(writeDict, 'description', self.description )
        self.writeKey(writeDict, 'start', self.start )
        self.writeKey(writeDict, 'end', self.end )
        self.writeKey(writeDict, 'elapsed', self.getElapsedSeconds() )

        self.generateReport(writeDict)

        self.writeKey(writeDict, 'status', self.status )
    # writeLogHeader

    def writeLogFooter(self, writeDict):
        writeDict['indentationLevel'] -= 1
        self.writeKey(writeDict, 'processList', None, 'stop' )
    # writeLogFooter

    def writeLog(self, logHandle=sys.stdout, indentationLevel=0,format='xml'):
        "Write logging information to the specified handle"
        
        writeDict = {}
        writeDict['logHandle'] = logHandle
        writeDict['indentationLevel'] = indentationLevel
        writeDict['format'] = format
        
        if logHandle:
            self.writeLogHeader(writeDict)
            
            if self.log:
                self.writeKey(writeDict, 'output', None, 'start' )
                for line in self.log:
                    logHandle.write( '%s%s\n' % ("", line) )
                self.writeKey(writeDict, 'output', None, 'stop' )

            if self.processes:
                self.writeKey(writeDict, 'processes', None, 'start' )
                for child in self.processes:
                    child.writeLog( logHandle, indentationLevel + 1, format )
                self.writeKey(writeDict, 'processes', None, 'stop' )

            self.writeLogFooter(writeDict)
    # writeLog

    def execute(self):
        "Execute this list of processes"
        import datetime

        self.start = datetime.datetime.now()

        self.status = 0
        if self.processes:
            for child in self.processes:
                if child:
                    try:
                        child.execute()
                    except:
                        print( "%s : caught exception in child class %s" % (self.__class__, child.__class__) )
                        traceback.print_exc()
                        child.status = -1

                    if self.blocking and child.status != 0:
                        print( "%s : child class %s finished with an error" % (self.__class__, child.__class__) )
                        self.status = -1
                        break

        self.end = datetime.datetime.now()
    # execute
# ProcessList

def main():
    import optparse

    p = optparse.OptionParser(description='A process logging script',
                                prog='process',
                                version='process 0.1',
                                usage='%prog [options] [options for the logged process]')
    p.add_option('--cmd', '-c', default=None)
    p.add_option('--log', '-l', default=None)

    options, arguments = p.parse_args()

    #
    # Get options
    # 
    cmd = options.cmd
    logFilename = options.log

    try:
        argsStart = sys.argv.index('--') + 1
        args = sys.argv[argsStart:]
    except:
        argsStart = len(sys.argv)+1
        args = []

    if cmd == None:
        print( "process: No command specified" )
 
    #
    # Test regular logging
    #
    process = Process(description="a process",cmd=cmd, args=args)

    #
    # Test report generation and writing a log
    #
    processList = ProcessList("a process list")
    processList.processes.append( process )
    processList.echo = True
    processList.execute()
    
    processList.writeLogToDisk(logFilename)
# main

if __name__ == '__main__':
    main()
