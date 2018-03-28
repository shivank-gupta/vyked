
from .utils.common_utils import json_file_to_dict
config = json_file_to_dict('config.json')

class CONFIG:
    convert_tcp_to_http =  config['tcp_to_http'] if (isinstance(config, dict) and 'tcp_to_http' in config  ) else True
    http_keep_alive_timeout = config['keep_alive_timeout'] if (isinstance(config, dict) and 'keep_alive_timeout' in config  ) else 15
    http_connection_timeout = config['http_connection_timeout'] if (isinstance(config, dict) and 'http_connection_timeout' in config  ) else 60

