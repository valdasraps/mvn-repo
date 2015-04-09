#!/usr/bin/env python
"""
Command line client for CondDB-WS REST API.
"""
import optparse
import urllib
import urllib2
import urlparse
import json
import re
import sys

API_VERSION = "1.0"
API_URL = "http://cmshcal23:8889"


# http://stackoverflow.com/questions/1885161/how-can-i-get-optparses-optionparser-to-ignore-invalid-options
from optparse import OptionParser, BadOptionError

class PassThroughOptionParser(OptionParser):
    def _process_long_opt(self, rargs, values):
        try:
            OptionParser._process_long_opt(self, rargs, values)
        except BadOptionError, err:
            self.largs.append(err.opt_str)

    def _process_short_opts(self, rargs, values):
        try:
            OptionParser._process_short_opts(self, rargs, values)
        except BadOptionError, err:
            self.largs.append(err.opt_str)

    def format_epilog(self, formatter):
        return self.epilog


def http_request(url, body, method, plain_list=False):
    """
    HTTP GET/POST request for the api
    """
    try:
        url = urlparse.urljoin(API_URL, url)
        if method == 'POST':
            data = json.dumps(body)
            # Need to supply a fake user agent string,
            # otherwise connection gets reset
            req = urllib2.Request(url, data, {
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/json',
                'Content-Length': len(data)
            })
        else:
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')

        response = urllib2.urlopen(req)
        # if response.headers.type in ['text/html', 'text/plain']:
        if response.headers.type not in ['application/json']:
            return response.read()
        content = json.loads(response.read())

        if plain_list is True and isinstance(content, list):
            # Print list items without any json-formatting
            return '\n'.join([
                str(item) for item in content
            ])
        else:
            return content
    except urllib2.HTTPError as exc:
        print str(exc)
        quit()


def post(url, body, plain_list=False):
    return http_request(url, body, 'POST', plain_list=plain_list)


def get(url, plain_list=False):
    return http_request(url, None, 'GET', plain_list=plain_list)


def parse_cond_params():
    """
    Standard optparse parser uses fixed option lists,
    but some parameters are condition-specific.
    Parse them manually here.
    """
    regex = r'--(?P<param>\w+)=?(?P<value>\w*)'
    params = {}
    for arg in sys.argv:
        matches = re.findall(regex, arg)
        if len(matches) > 0:
            param, value = matches[0]
            if len(value) == 0:
                value = None
            params[param] = value
    return params


if __name__ == "__main__":
    example='''
Examples:

    Get available condition types:
    ./conddb-omds.py -l

    Get condition-specific parameter list:
    ./conddb-omds.py -c HcalQIEData -p

    To get possible options for condition-specific parameter, supply its name without assigned value:
    ./conddb-omds.py -c HcalQIEData --version

    Get and write condition data with specified parameters into .txt file:
    ./conddb-omds.py -c HcalQIEData --version=1 -o /tmp/output.txt
'''
    parser = PassThroughOptionParser(epilog=example)
    parser.add_option(
        '-l', dest='show_list', action='store_true', default=False,
        help='list of available condition types')
    parser.add_option(
        '-c', dest='cond_type', action='store', default=None,
        help='selected condition type')
    parser.add_option(
        '-p', dest='show_params', action='store_true', default=False,
        help='list of condition-specific parameters')
    parser.add_option(
        '-o', dest='output_file', action='store', default=None,
        help='output file name')
    args = vars(parser.parse_args()[0])

    # Nothing provided?
    if set(args.values()) == set([False, None]):
        parser.print_help()
        quit()

    # Check versions
    remote_api_version = get('/api_version')
    if str(remote_api_version) != str(API_VERSION):
        msg = "Version mismatch "
        msg += "(remote API version: " + str(remote_api_version)
        msg += ", client script version: " + str(API_VERSION) + ")"
        print msg
        quit()

    if args['show_list'] is True:
        # List of available condition types
        print get('/conditions', plain_list=True)
        quit()

    if args['cond_type'] is not None:
        cond_type = args['cond_type']
        cond_info = get('/conditions/' + cond_type)
        if 'params' in cond_info:
            cond_params = cond_info['params']
        else:
            cond_params = []

        if args['show_params'] is True:
            # List of parameters for selected condition type'
            print 'Condition-specific parameters:'
            print '\n'.join([param['name'] for param in cond_params])
        else:
            # Validate condition-specific parameters
            # All of them must be specified in command line.
            parsed_params = parse_cond_params()
            missing_params = []
            for cond_param in cond_params:
                if cond_param['name'] in parsed_params.keys():
                    if parsed_params[cond_param['name']] is None:
                        # Parameter name is specified but no value is assigned
                        # Get all possible values from the server
                        param_options = get(
                            '/conditions/' + cond_type + '/params/' + cond_param['name'])
                        print 'Options for \'%s\' parameter:' % cond_param['name']
                        print '\n'.join(param_options)
                        quit()
                    else:
                        # Everything's ok with this parameter
                        pass
                else:
                    # This param is not specified
                    missing_params.append(cond_param['name'])

            if len(missing_params) > 0:
                print "Missing condition-specific parameters:"
                print '\n'.join(missing_params)
                quit()

            if args['output_file'] is None:
                print "Missing output file name (-o option)"
                quit()

            # Get these conditions (finally)
            # 1. POST: condition type and get info of the new resthub query
            query_info = post(
                '/conditions/' + cond_type + '/queries', {})

            # 2. POST: ask server to export condition data into .ssv file
            # and get its filename
            for key in list(parsed_params.keys()):
                # Need to put table alias prefix for each param
                new_key = query_info['table_alias'] + '.' + key
                parsed_params[new_key] = parsed_params[key]
                del parsed_params[key]

            temp_filename = post(
                '/conditions/' + cond_type + '/queries/' + query_info['id'],
                parsed_params)['ssv_filename']

            # 3. GET: actual condition data by received temp file name
            file_content = get('/file/' + temp_filename)
            with open(args['output_file'], 'w') as fp:
                fp.write(file_content)
