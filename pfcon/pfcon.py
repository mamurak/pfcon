#!/usr/bin/env python3.5

import  sys

from    io              import  BytesIO as IO
from    http.server     import  BaseHTTPRequestHandler, HTTPServer
from    socketserver    import  ThreadingMixIn
from    webob           import  Response
import  cgi
import  json
import  urllib
import  ast
import  shutil
import  datetime

import  platform
import  socket
import  psutil
import  os
import  multiprocessing
import  pfurl

import  pudb

# pfcon local dependencies
from    ._colors        import  Colors
from    .debug          import  debug
from   .C_snode         import *


# Horrible global var
G_b_httpResponse            = False

Gd_internalvar  = {

    'service':  {
        'pangea': {
            'data': {
                'addr':         '10.17.24.163:5055',
                'baseURLpath':  '/api/v1/cmd/',
                'status':       'undefined',

                'storeAccess.tokenSet':  {
                    "action":   "internalctl",
                    "meta": {
                           "var":          "key",
                           "set":          "setKeyValueHere"
                       }
                },

                'storeAccess.addrGet':  {
                    "action":   "internalctl",
                    "meta": {
                        "var":          "storeAddress",
                        "compute":      "address"
                    }
                }

            },
            'compute': {
                'addr':         '10.17.24.163:5010',
                'baseURLpath':  '/api/v1/cmd/',
                'status':       'undefined'
            }
        }
    }
}

Gd_tree         = C_stree()


class StoreHandler(BaseHTTPRequestHandler):

    b_quiet     = False

    def __init__(self, *args, **kwargs):
        """
        """
        b_test  = False

        for k,v in kwargs.items():
            if k == 'test': b_test  = True

        if not b_test:
            BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def qprint(self, msg, **kwargs):

        str_comms  = ""
        for k,v in kwargs.items():
            if k == 'comms':    str_comms  = v

        if not StoreHandler.b_quiet:
            if str_comms == 'status':   print(Colors.PURPLE,    end="")
            if str_comms == 'error':    print(Colors.RED,       end="")
            if str_comms == "tx":       print(Colors.YELLOW + "<----")
            if str_comms == "rx":       print(Colors.GREEN  + "---->")
            print('%s' % datetime.datetime.now() + " | ",       end="")
            print(msg)
            if str_comms == "tx":       print(Colors.YELLOW + "<----")
            if str_comms == "rx":       print(Colors.GREEN  + "---->")
            print(Colors.NO_COLOUR, end="")

    def log_message(self, format, *args):
        """
        This silences the server from spewing to stdout!
        """
        return

    def do_GET(self):

        d_server            = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
        d_meta              = ast.literal_eval(d_server['meta'])

        d_msg               = {'action': d_server['action'], 'meta': d_meta}
        d_ret               = {}
        self.qprint(self.path, comms = 'rx')

        return d_ret

    def form_get(self, str_verb, data):
        """
        Returns a form from cgi.FieldStorage
        """
        return cgi.FieldStorage(
            IO(data),
            headers = self.headers,
            environ =
            {
                'REQUEST_METHOD':   str_verb,
                'CONTENT_TYPE':     self.headers['Content-Type'],
            }
        )

    def internalctl_varprocess(self, *args, **kwargs):
        """

        get/set a specific variable as parsed from the meta JSON.

        :param args:
        :param kwargs:
        :return:
        """
        global Gd_internalvar
        global Gd_tree
        d_meta      = {}
        d_ret       = {}
        str_var     = ''
        b_status    = False
        b_tree      = False

        for k,v in kwargs.items():
            if k == 'd_meta':   d_meta  = v

        str_var     = d_meta['var']

        T           = C_stree()

        if d_meta:
            if 'get' in d_meta.keys():
                if Gd_tree.isdir(str_var):
                    Gd_tree.copy(startPath = str_var, destination = T)
                    d_ret                   = dict(T.snode_root)
                else:
                    d_ret[str_var]          = Gd_tree.cat(str_var)
                b_status                = True

            if 'set' in d_meta.keys():
                try:
                    d_set   = json.loads(d_meta['set'])
                    b_tree  = True
                except:
                    b_tree  = False
                if b_tree:
                    D       = C_stree()
                    D.initFromDict(d_set)
                    D.copy(startPath = '/', destination = Gd_tree, pathDiskRoot = str_var)
                    d_ret           = d_set
                else:
                    Gd_tree.touch(str_var, d_meta['set'])
                    d_ret[str_var]          = Gd_tree.cat(str_var)
                b_status                = True

        return {'d_ret':    d_ret,
                'status':   b_status}

    def internalctl_process(self, *args, **kwargs):
        """

        Process the 'internalctl' action.

             {  "action": "internalctl",
                     "meta": {
                            "var":      "/tree/path",
                            "set":     "<someValue>"
                     }
             }

             {  "action": "internalctl",
                     "meta": {
                            "var":      "/tree/path",
                            "get":      "currentPath"
                     }
             }

        :param args:
        :param kwargs:
        :return:
        """

        d_request           = {}
        b_status            = False
        d_ret               = {
            'status':   b_status
        }

        for k,v in kwargs.items():
            if k == 'request':   d_request   = v
        if d_request:
            d_meta  = d_request['meta']
            d_ret   = self.internalctl_varprocess(d_meta = d_meta)
        return d_ret

    def dataRequest_process(self, *args, **kwargs):
        """
        Method for talking to the data handling service.

        :param args:
        :param kwargs:
        :return: JSON object from the 'pfioh' call.
        """

        global  Gd_tree
        b_status    = False

        self.qprint("dataRequest_prcoess()", comms = 'status')

        d_request   = {}
        d_meta      = {}
        d_ret       = {}
        for k,v in kwargs.items():
            if k == 'request':          d_request           = v

        d_meta                  = d_request['meta']
        str_remoteService       = d_meta['service']
        str_dataServiceAddr     = Gd_tree.cat('/service/%s/data/addr'       % str_remoteService)
        str_dataServiceURL      = Gd_tree.cat('/service/%s/data/baseURL'    % str_remoteService)

        dataComs = pfurl.Pfurl(
            msg                         = json.dumps(d_request),
            verb                        = 'POST',
            http                        = '%s/%s' % (str_dataServiceAddr, str_dataServiceURL),
            b_quiet                     = True,
            b_raw                       = True,
            b_httpResponseBodyParse     = True,
            jsonwrapper                 = 'payload'
        )

        self.qprint("Calling remote data service...",   comms = 'rx')
        d_dataResponse                          = json.loads(dataComs())
        d_ret['%s-data' % str_remoteService]    = d_dataResponse

        return {
            'd_ret':        d_dataResponse,
            'serviceName':  str_remoteService,
            'status':       True
        }

    def computeRequest_process(self, *args, **kwargs):
        """
        Method for talking to the data handling service.

        :param args:
        :param kwargs:
        :return: JSON object from the 'pfioh' call.
        """

        global  Gd_tree
        b_status    = False

        self.qprint("computeRequest_process()", comms = 'status')

        d_request   = {}
        d_meta      = {}
        d_ret       = {}
        for k,v in kwargs.items():
            if k == 'request':          d_request           = v

        d_meta                  = d_request['meta']
        str_remoteService       = d_meta['service']
        str_computeServiceAddr  = Gd_tree.cat('/service/%s/compute/addr'    % str_remoteService)
        str_computeServiceURL   = Gd_tree.cat('/service/%s/compute/baseURL' % str_remoteService)

        # Remember, 'pman' responses do NOT need to http-body parsed!
        computeComs = pfurl.Pfurl(
            msg                         = json.dumps(d_request),
            verb                        = 'POST',
            http                        = '%s/%s' % (str_computeServiceAddr, str_computeServiceURL),
            b_quiet                     = True,
            b_raw                       = True,
            b_httpResponseBodyParse     = False,
            jsonwrapper                 = 'payload'
        )

        self.qprint("Calling remote compute service...", comms = 'rx')
        d_computeResponse                       = json.loads(computeComs())

        return {
            'd_ret':        d_computeResponse,
            'serviceName':  str_remoteService,
            'status':       True
        }

    def hello_process_remote(self, *args, **kwargs):
        """
        Process the 'hello' call on the remote services

        :param args:
        :param kwargs:
        :return:
        """
        global Gd_tree
        b_status    = False

        self.qprint("hello_process_remote()", comms = 'status')

        d_request   = {}
        d_ret       = {}
        for k,v in kwargs.items():
            if k == 'request':          d_request           = v

        d_dataResponse      = self.dataRequest_process(request      = d_request)
        d_ret['%s-data'     % d_dataResponse['serviceName']]        = d_dataResponse

        d_computeResponse   = self.computeRequest_process(request   = d_request)
        d_ret['%s-compute'  % d_computeResponse['serviceName']]     = d_computeResponse

        return {
            'd_ret':                d_ret,
            'serviceNameData':      d_dataResponse['serviceName'],
            'serviceNameCompute':   d_computeResponse['serviceName'],
            'status':               True
        }

    def hello_process(self, *args, **kwargs):
        """

        The 'hello' action is merely to 'speak' with the server. The server
        can return current date/time, echo back a string, query the startup
        command line args, etc.

        This method is a simple means of checking if the server is "up" and
        running.

        :param args:
        :param kwargs:
        :return:
        """

        self.qprint("hello_process()", comms = 'status')
        b_status            = False
        d_ret               = {}
        d_request           = {}
        d_remote            = {}
        for k, v in kwargs.items():
            if k == 'request':      d_request   = v

        d_meta  = d_request['meta']
        if 'askAbout' in d_meta.keys():
            str_askAbout    = d_meta['askAbout']
            if str_askAbout == 'timestamp':
                str_timeStamp   = datetime.datetime.today().strftime('%Y%m%d%H%M%S.%f')
                d_ret['timestamp']              = {}
                d_ret['timestamp']['now']       = str_timeStamp
                b_status                        = True
            if str_askAbout == 'sysinfo':
                d_ret['sysinfo']                = {}
                d_ret['sysinfo']['system']      = platform.system()
                d_ret['sysinfo']['machine']     = platform.machine()
                d_ret['sysinfo']['platform']    = platform.platform()
                d_ret['sysinfo']['uname']       = platform.uname()
                d_ret['sysinfo']['version']     = platform.version()
                d_ret['sysinfo']['memory']      = psutil.virtual_memory()
                d_ret['sysinfo']['cpucount']    = multiprocessing.cpu_count()
                d_ret['sysinfo']['loadavg']     = os.getloadavg()
                d_ret['sysinfo']['cpu_percent'] = psutil.cpu_percent()
                d_ret['sysinfo']['hostname']    = socket.gethostname()
                b_status                        = True
            if str_askAbout == 'echoBack':
                d_ret['echoBack']               = {}
                d_ret['echoBack']['msg']        = d_meta['echoBack']
                b_status                        = True

        # pudb.set_trace()
        d_remote    = self.hello_process_remote(request = d_request)

        return { 'd_ret':       d_ret,
                 'd_remote':    d_remote,
                 'status':      b_status}

    def coordinate_process(self, *args, **kwargs):
        """
        The main coordination method entry point.

        This method (and sub-methods) is responsible for copying data to remote,
        calling the remote process, and copying results back.

        :param args:
        :param kwargs:
        :return:
        """

        self.qprint("coordinate_process()", comms = 'status')
        d_request   = {}
        for k,v in kwargs.items():
            if k == 'request':      d_request   = v

        self.qprint("d_request = %s" % d_request)
        d_metaData      = d_request['meta-data']
        d_metaCompute   = d_request['meta-compute']
        d_metaStore     = d_request['meta-store']

        str_storeMeta   = d_metaStore['meta']
        str_storeKey    = d_metaStore['key']

        str_key         = d_request[str_storeMeta][str_storeKey]
        self.qprint("key = %s" % str_key)

    def do_POST(self, *args, **kwargs):
        """
        Main dispatching method for coordination service.

        The following actions are available:

            * hello
            * coordinate
            * status
            * servicectl

        :param kwargs:
        :return:
        """

        d_msg       = {}
        d_done      = {}

        # Parse the form data posted
        self.qprint(str(self.headers), comms = 'rx')

        length              = self.headers['content-length']
        data                = self.rfile.read(int(length))
        form                = self.form_get('POST', data)
        d_form              = {}
        d_ret               = {
            'msg':      'In do_POST',
            'status':   True,
            'formsize': sys.getsizeof(form)
        }

        self.qprint('data length = %d' % len(data),   comms = 'status')
        self.qprint('form length = %d' % len(form), comms = 'status')

        if len(form):
            self.qprint("Unpacking multi-part form message...", comms = 'status')
            for key in form:
                self.qprint("\tUnpacking field '%s..." % key, comms = 'status')
                d_form[key]     = form.getvalue(key)
            d_msg               = json.loads((d_form['d_msg']))
        else:
            self.qprint("Parsing JSON data...", comms = 'status')
            d_data              = json.loads(data.decode())
            d_msg               = d_data['payload']

        self.qprint('d_msg = %s' % d_msg, comms = 'status')

        if 'action' in d_msg:
            self.qprint("verb: %s detected." % d_msg['action'], comms = 'status')
            str_method      = '%s_process' % d_msg['action']
            self.qprint("method to call: %s(request = d_msg) " % str_method, comms = 'status')
            d_done          = {'status': False}
            try:
                method      = getattr(self, str_method)
                d_done      = method(request = d_msg)
            except  AttributeError:
                raise NotImplementedError("Class `{}` does not implement `{}`".format(self.__class__.__name__, method))
            self.qprint(d_done, comms = 'tx')
            d_ret = d_done

        self.ret_client(d_ret)
        return d_ret

    def do_POST_serverctl(self, d_meta):
        """
        """
        d_ctl               = d_meta['ctl']
        self.qprint('Processing server ctl...', comms = 'status')
        self.qprint(d_meta, comms = 'rx')
        if 'serverCmd' in d_ctl:
            if d_ctl['serverCmd'] == 'quit':
                self.qprint('Shutting down server', comms = 'status')
                d_ret = {
                    'msg':      'Server shut down',
                    'status':   True
                }
                self.qprint(d_ret, comms = 'tx')
                self.ret_client(d_ret)
                os._exit(0)

    def ret_client(self, d_ret):
        """
        Simply "writes" the d_ret using json and the client wfile.

        :param d_ret:
        :return:
        """
        if not G_b_httpResponse:
            self.wfile.write(json.dumps(d_ret).encode())
        else:
            self.wfile.write(str(Response(json.dumps(d_ret))).encode())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Handle requests in a separate thread.
    """

    def col2_print(self, str_left, str_right):
        print(Colors.WHITE +
              ('%*s' % (self.LC, str_left)), end='')
        print(Colors.LIGHT_BLUE +
              ('%*s' % (self.RC, str_right)) + Colors.NO_COLOUR)

    def __init__(self, *args, **kwargs):
        """

        Holder for constructor of class -- allows for explicit setting
        of member 'self' variables.

        :return:
        """
        global Gd_internalvar
        global Gd_tree
        HTTPServer.__init__(self, *args, **kwargs)
        self.LC             = 40
        self.RC             = 40
        self.args           = None
        self.str_desc       = 'pfcon\n\n'

        self.dp             = debug(verbosity=0, level=-1)

        Gd_tree.initFromDict(Gd_internalvar)

    def setup(self, **kwargs):
        global G_b_httpResponse
        global Gd_tree

        for k,v in kwargs.items():
            if k == 'args': self.args       = v
            if k == 'desc': self.str_desc   = v

        G_b_httpResponse = self.args['b_httpResponse']
        print(self.str_desc)

        self.col2_print("Listening on address:",    self.args['ip'])
        self.col2_print("Listening on port:",       self.args['port'])
        self.col2_print("Server listen forever:",   self.args['b_forever'])
        self.col2_print("Return HTTP responses:",   G_b_httpResponse)

        print(Colors.YELLOW + "\n\t\tInternal data tree:")
        print(C_snode.str_blockIndent(str(Gd_tree), 3, 8))

        print(Colors.LIGHT_GREEN + "\n\n\tWaiting for incoming data..." + Colors.NO_COLOUR)
