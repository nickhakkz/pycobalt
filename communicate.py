#
# For communication with cobaltstrike
#
# TODO popups
# TODO handle callback functions (e.g. bps)
# TODO better argument checking on aggressor functions
# TODO kill process after

import json
import re
import sys
import traceback

import utils
import events
import aggressor
import commands
import aliases

_in_pipe = None
_out_pipe = None

def __init__():
    global _in_pipe
    global _out_pipe

    _in_pipe = sys.stdin
    _out_pipe = sys.stdout

    # since cobaltstrike can't read stderr
    sys.stderr = sys.stdout

def write(message_type, message=''):
    global _out_pipe
    wrapper = {
                  'name': message_type,
                  'message': message,
              }
    _out_pipe.write(json.dumps(wrapper) + "\n")
    _out_pipe.flush()

# Fix for mudge's shitty Java parameter marshalling
def fix_dicts(old):
    if not isinstance(old, dict):
        return old

    new = {}
    for key, item in old.items():
        # make new key
        m = re.match("'([^']+)'", key)
        if m:
            new_key = m.group(1)
        else:
            new_key = key

        if isinstance(item, list):
            # lists
            new_item = []
            for piece in item:
                new_item.append(fix_dicts(piece))
        elif isinstance(item, dict):
            # nested dicts
            new_item = fix_dicts(item)
        else:
            new_item = item
        new[new_key] = new_item
    return new

# Loop forever, handling messages
def loop(fork=True):
    # tell cobaltstrike to fork
    if fork:
        communicate.fork()

    reader = communicate.readiter()
    while True:
        try:
            name, message = next(reader)
            if name:
                communicate.handle_message(name, message)
            else:
                communicate.error('received invalid message: {}'.format(message))
        except StopIteration as e:
            break
        except Exception as e:
            communicate.error('exception: {}\n'.format(str(e)))
            communicate.error('traceback: {}'.format(traceback.format_exc()))

# Handle a received message according to its name
def handle_message(name, message):
    debug('handling message of type {}: {}'.format(name, messagE))
    if name == 'event':
        # dispatch event
        event_name = message['name']
        event_args = message['args'] if 'args' in message else []
        events.call(event_name, event_args)
    elif name == 'alias':
        # dispatch alias
        alias_name = message['name']
        alias_args = message['args'] if 'args' in message else []
        aliases.call(alias_name, alias_args)
    elif name == 'command':
        # dispatch command
        command_name = message['name']
        command_args = message['args'] if 'args' in message else []
        commands.call(command_name, command_args)
    elif name == 'eval':
        # eval python code
        eval(message)
    else:
        raise RuntimeError('received unhandled or out-of-order message type: {} {}'.format(name, str(message)))

# Parse an input line
# Format: {'name':<name>, 'message':<message>}
def parse_line(line):
    try:
        line = line.strip()
        wrapper = json.loads(line)
        wrapper = fix_dicts(wrapper)
        name = wrapper['name']
        if 'message' in wrapper:
            message = wrapper['message']
        else:
            message = None

        return name, message
    except Exception as e:
        return None, str(e)

# Read a message line
# Returns: message name, submessage
def read():
    global _in_pipe
    return parse_line(next(_in_pipe))

# Read message lines
# Returns: message name, submessage
def readiter():
    global _in_pipe
    for line in _in_pipe:
        yield parse_line(line)

# Tell cobaltstrike to fork
_has_forked = False
def fork():
    global _has_forked
    if _has_forked:
        # already forked?
        error('tried to fork twice')
        return

    _has_forked = True
    write('fork')

# Call aggressor function
def call(name, args):
    message = {
                'name': name,
                'args': args,
              }
    write('call', message)

    # read until we get a return value
    while True:
        name, message = read()
        if name == 'return':
            # got it
            return message
        else:


    if name != 'return':
        raise RuntimeError('out of sync input message: {}'.format(name))

# Eval aggressor code
def eval(code):
    write('eval', code)

# Write error notice
def error(line):
    write('error', line)

# Write script console message
def message(line):
    write('message', line)

# Register a command
def command(name):
    global _has_forked
    if _has_forked:
        # cobaltstrike crashes if you try to register a command after forking
        error('tried to register a command after forking')
        return

    write('command', name)

# Register an alias
def alias(name):
    global _has_forked
    if _has_forked:
        # cobaltstrike crashes if you try to register an alias after forking
        error('tried to register an alias after forking')
        return

    write('alias', name)

# Write script console debug message
_debug_on = False
def debug(line):
    global _debug_on
    if _debug_on:
        write('debug', line)

__init__()