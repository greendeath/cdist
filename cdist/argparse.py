import argparse
import cdist
import multiprocessing
import os
import logging
import collections


# set of beta sub-commands
BETA_COMMANDS = set(('install', 'inventory', ))
# set of beta arguments for sub-commands
BETA_ARGS = {
    'config': set(('jobs', 'tag', 'all_tagged_hosts', )),
}
EPILOG = "Get cdist at http://www.nico.schottelius.org/software/cdist/"
# Parser others can reuse
parser = None


_verbosity_level_off = -2
_verbosity_level = {
    _verbosity_level_off: logging.OFF,
    -1: logging.ERROR,
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.VERBOSE,
    3: logging.DEBUG,
    4: logging.TRACE,
}
# All verbosity levels above 4 are TRACE.
_verbosity_level = collections.defaultdict(
    lambda: logging.TRACE, _verbosity_level)


def add_beta_command(cmd):
    BETA_COMMANDS.add(cmd)


def add_beta_arg(cmd, arg):
    if cmd in BETA_ARGS:
        if arg not in BETA_ARGS[cmd]:
            BETA_ARGS[cmd].append(arg)
    else:
        BETA_ARGS[cmd] = set((arg, ))


def check_beta(args_dict):
    if 'beta' not in args_dict:
        args_dict['beta'] = False
    # Check only if beta is not enabled: if beta option is specified then
    # raise error.
    if not args_dict['beta']:
        cmd = args_dict['command']
        # first check if command is beta
        if cmd in BETA_COMMANDS:
            raise cdist.CdistBetaRequired(cmd)
        # then check if some command's argument is beta
        if cmd in BETA_ARGS:
            for arg in BETA_ARGS[cmd]:
                if arg in args_dict and args_dict[arg]:
                    raise cdist.CdistBetaRequired(cmd, arg)


def check_positive_int(value):
    import argparse

    try:
        val = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
                "{} is invalid int value".format(value))
    if val <= 0:
        raise argparse.ArgumentTypeError(
                "{} is invalid positive int value".format(val))
    return val


def get_parsers():
    global parser

    # Construct parser others can reuse
    if parser:
        return parser
    else:
        parser = {}
    # Options _all_ parsers have in common
    parser['loglevel'] = argparse.ArgumentParser(add_help=False)
    parser['loglevel'].add_argument(
            '-q', '--quiet',
            help='Quiet mode: disables logging, including WARNING and ERROR',
            action='store_true', default=False)
    parser['loglevel'].add_argument(
            '-v', '--verbose',
            help=('Increase the verbosity level. Every instance of -v '
                  'increments the verbosity level by one. Its default value '
                  'is 0 which includes ERROR and WARNING levels. '
                  'The levels, in order from the lowest to the highest, are: '
                  'ERROR (-1), WARNING (0), INFO (1), VERBOSE (2), DEBUG (3) '
                  'TRACE (4 or higher).'),
            action='count', default=0)

    parser['beta'] = argparse.ArgumentParser(add_help=False)
    parser['beta'].add_argument(
           '-b', '--beta',
           help=('Enable beta functionality. '
                 'Can also be enabled using CDIST_BETA env var.'),
           action='store_true', dest='beta',
           default='CDIST_BETA' in os.environ)

    # Main subcommand parser
    parser['main'] = argparse.ArgumentParser(
            description='cdist ' + cdist.VERSION, parents=[parser['loglevel']])
    parser['main'].add_argument(
            '-V', '--version', help='Show version', action='version',
            version='%(prog)s ' + cdist.VERSION)
    parser['sub'] = parser['main'].add_subparsers(
            title="Commands", dest="command")

    # Banner
    parser['banner'] = parser['sub'].add_parser(
            'banner', parents=[parser['loglevel']])
    parser['banner'].set_defaults(func=cdist.banner.banner)

    parser['inventory_common'] = argparse.ArgumentParser(add_help=False)
    parser['inventory_common'].add_argument(
           '-I', '--inventory',
           help=('Use specified custom inventory directory. '
                 'Inventory directory is set up by the following rules: '
                 'if this argument is set then specified directory is used, '
                 'if CDIST_INVENTORY_DIR env var is set then its value is '
                 'used, if HOME env var is set then ~/.cdist/inventory is '
                 'used, otherwise distribution inventory directory is used.'),
           dest="inventory_dir", required=False)

    # Config
    parser['config_main'] = argparse.ArgumentParser(add_help=False)
    parser['config_main'].add_argument(
            '-C', '--cache-path-pattern',
            help=('Specify custom cache path pattern. It can also be set '
                  'by CDIST_CACHE_PATH_PATTERN environment variable. If '
                  'it is not set then default hostdir is used.'),
            dest='cache_path_pattern',
            default=os.environ.get('CDIST_CACHE_PATH_PATTERN'))
    parser['config_main'].add_argument(
            '-c', '--conf-dir',
            help=('Add configuration directory (can be repeated, '
                  'last one wins)'), action='append')
    parser['config_main'].add_argument(
           '-i', '--initial-manifest',
           help='path to a cdist manifest or \'-\' to read from stdin.',
           dest='manifest', required=False)
    parser['config_main'].add_argument(
           '-j', '--jobs', nargs='?',
           type=check_positive_int,
           help=('Operate in parallel in specified maximum number of jobs. '
                 'Global explorers, object prepare and object run are '
                 'supported. Without argument CPU count is used by default. '
                 'Currently in beta.'),
           action='store', dest='jobs',
           const=multiprocessing.cpu_count())
    parser['config_main'].add_argument(
           '-n', '--dry-run',
           help='do not execute code', action='store_true')
    parser['config_main'].add_argument(
           '-o', '--out-dir',
           help='directory to save cdist output in', dest="out_path")

    # remote-copy and remote-exec defaults are environment variables
    # if set; if not then None - these will be futher handled after
    # parsing to determine implementation default
    parser['config_main'].add_argument(
           '-r', '--remote-out-dir',
           help='Directory to save cdist output in on the target host',
           dest="remote_out_path")
    parser['config_main'].add_argument(
           '--remote-copy',
           help='Command to use for remote copy (should behave like scp)',
           action='store', dest='remote_copy',
           default=os.environ.get('CDIST_REMOTE_COPY'))
    parser['config_main'].add_argument(
           '--remote-exec',
           help=('Command to use for remote execution '
                 '(should behave like ssh)'),
           action='store', dest='remote_exec',
           default=os.environ.get('CDIST_REMOTE_EXEC'))

    # Config
    parser['config_args'] = argparse.ArgumentParser(add_help=False)
    parser['config_args'].add_argument(
             '-A', '--all-tagged',
             help=('use all hosts present in tags db'),
             action="store_true", dest="all_tagged_hosts", default=False)
    parser['config_args'].add_argument(
             '-a', '--all',
             help=('list hosts that have all specified tags, '
                   'if -t/--tag is specified'),
             action="store_true", dest="has_all_tags", default=False)
    parser['config_args'].add_argument(
            'host', nargs='*', help='host(s) to operate on')
    parser['config_args'].add_argument(
            '-f', '--file',
            help=('Read specified file for a list of additional hosts to '
                  'operate on or if \'-\' is given, read stdin (one host per '
                  'line). If no host or host file is specified then, by '
                  'default, read hosts from stdin.'),
            dest='hostfile', required=False)
    parser['config_args'].add_argument(
           '-p', '--parallel', nargs='?', metavar='HOST_MAX',
           type=check_positive_int,
           help=('Operate on multiple hosts in parallel for specified maximum '
                 'hosts at a time. Without argument CPU count is used by '
                 'default.'),
           action='store', dest='parallel',
           const=multiprocessing.cpu_count())
    parser['config_args'].add_argument(
           '-s', '--sequential',
           help='operate on multiple hosts sequentially (default)',
           action='store_const', dest='parallel', const=0)
    parser['config_args'].add_argument(
             '-t', '--tag',
             help=('host is specified by tag, not hostname/address; '
                   'list all hosts that contain any of specified tags'),
             dest='tag', required=False, action="store_true", default=False)
    parser['config'] = parser['sub'].add_parser(
            'config', parents=[parser['loglevel'], parser['beta'],
                               parser['config_main'],
                               parser['inventory_common'],
                               parser['config_args']])
    parser['config'].set_defaults(func=cdist.config.Config.commandline)

    # Install
    parser['install'] = parser['sub'].add_parser('install', add_help=False,
                                                 parents=[parser['config']])
    parser['install'].set_defaults(func=cdist.install.Install.commandline)

    # Inventory
    parser['inventory'] = parser['sub'].add_parser(
           'inventory', parents=[parser['loglevel'], parser['beta'],
                                 parser['inventory_common']])
    parser['invsub'] = parser['inventory'].add_subparsers(
            title="Inventory commands", dest="subcommand")

    parser['add-host'] = parser['invsub'].add_parser(
            'add-host', parents=[parser['loglevel'], parser['beta'],
                                 parser['inventory_common']])
    parser['add-host'].add_argument(
            'host', nargs='*', help='host(s) to add')
    parser['add-host'].add_argument(
           '-f', '--file',
           help=('Read additional hosts to add from specified file '
                 'or from stdin if \'-\' (each host on separate line). '
                 'If no host or host file is specified then, by default, '
                 'read from stdin.'),
           dest='hostfile', required=False)

    parser['add-tag'] = parser['invsub'].add_parser(
            'add-tag', parents=[parser['loglevel'], parser['beta'],
                                parser['inventory_common']])
    parser['add-tag'].add_argument(
           'host', nargs='*',
           help='list of host(s) for which tags are added')
    parser['add-tag'].add_argument(
           '-f', '--file',
           help=('Read additional hosts to add tags from specified file '
                 'or from stdin if \'-\' (each host on separate line). '
                 'If no host or host file is specified then, by default, '
                 'read from stdin. If no tags/tagfile nor hosts/hostfile'
                 ' are specified then tags are read from stdin and are'
                 ' added to all hosts.'),
           dest='hostfile', required=False)
    parser['add-tag'].add_argument(
           '-T', '--tag-file',
           help=('Read additional tags to add from specified file '
                 'or from stdin if \'-\' (each tag on separate line). '
                 'If no tag or tag file is specified then, by default, '
                 'read from stdin. If no tags/tagfile nor hosts/hostfile'
                 ' are specified then tags are read from stdin and are'
                 ' added to all hosts.'),
           dest='tagfile', required=False)
    parser['add-tag'].add_argument(
           '-t', '--taglist',
           help=("Tag list to be added for specified host(s), comma separated"
                 " values"),
           dest="taglist", required=False)

    parser['del-host'] = parser['invsub'].add_parser(
            'del-host', parents=[parser['loglevel'], parser['beta'],
                                 parser['inventory_common']])
    parser['del-host'].add_argument(
            'host', nargs='*', help='host(s) to delete')
    parser['del-host'].add_argument(
            '-a', '--all', help=('Delete all hosts'),
            dest='all', required=False, action="store_true", default=False)
    parser['del-host'].add_argument(
            '-f', '--file',
            help=('Read additional hosts to delete from specified file '
                  'or from stdin if \'-\' (each host on separate line). '
                  'If no host or host file is specified then, by default, '
                  'read from stdin.'),
            dest='hostfile', required=False)

    parser['del-tag'] = parser['invsub'].add_parser(
            'del-tag', parents=[parser['loglevel'], parser['beta'],
                                parser['inventory_common']])
    parser['del-tag'].add_argument(
            'host', nargs='*',
            help='list of host(s) for which tags are deleted')
    parser['del-tag'].add_argument(
            '-a', '--all',
            help=('Delete all tags for specified host(s)'),
            dest='all', required=False, action="store_true", default=False)
    parser['del-tag'].add_argument(
            '-f', '--file',
            help=('Read additional hosts to delete tags for from specified '
                  'file or from stdin if \'-\' (each host on separate line). '
                  'If no host or host file is specified then, by default, '
                  'read from stdin. If no tags/tagfile nor hosts/hostfile'
                  ' are specified then tags are read from stdin and are'
                  ' deleted from all hosts.'),
            dest='hostfile', required=False)
    parser['del-tag'].add_argument(
            '-T', '--tag-file',
            help=('Read additional tags from specified file '
                  'or from stdin if \'-\' (each tag on separate line). '
                  'If no tag or tag file is specified then, by default, '
                  'read from stdin. If no tags/tagfile nor'
                  ' hosts/hostfile are specified then tags are read from'
                  ' stdin and are added to all hosts.'),
            dest='tagfile', required=False)
    parser['del-tag'].add_argument(
            '-t', '--taglist',
            help=("Tag list to be deleted for specified host(s), "
                  "comma separated values"),
            dest="taglist", required=False)

    parser['list'] = parser['invsub'].add_parser(
            'list', parents=[parser['loglevel'], parser['beta'],
                             parser['inventory_common']])
    parser['list'].add_argument(
            'host', nargs='*', help='host(s) to list')
    parser['list'].add_argument(
            '-a', '--all',
            help=('list hosts that have all specified tags, '
                  'if -t/--tag is specified'),
            action="store_true", dest="has_all_tags", default=False)
    parser['list'].add_argument(
            '-f', '--file',
            help=('Read additional hosts to list from specified file '
                  'or from stdin if \'-\' (each host on separate line). '
                  'If no host or host file is specified then, by default, '
                  'list all.'), dest='hostfile', required=False)
    parser['list'].add_argument(
            '-H', '--host-only', help=('Suppress tags listing'),
            action="store_true", dest="list_only_host", default=False)
    parser['list'].add_argument(
            '-t', '--tag',
            help=('host is specified by tag, not hostname/address; '
                  'list all hosts that contain any of specified tags'),
            action="store_true", default=False)

    parser['inventory'].set_defaults(
            func=cdist.inventory.Inventory.commandline)

    # Shell
    parser['shell'] = parser['sub'].add_parser(
            'shell', parents=[parser['loglevel']])
    parser['shell'].add_argument(
            '-s', '--shell',
            help=('Select shell to use, defaults to current shell. Used shell'
                  ' should be POSIX compatible shell.'))
    parser['shell'].set_defaults(func=cdist.shell.Shell.commandline)

    for p in parser:
        parser[p].epilog = EPILOG

    return parser


def handle_loglevel(args):
    if args.quiet:
        args.verbose = _verbosity_level_off

    logging.root.setLevel(_verbosity_level[args.verbose])
