import sys
from config import *
from colored import fg, attr

load_config(os.path.join(os.getcwd(), 'config.json'))

def formatted_print(module, text):
    cfg = get_config()
    var = str(cfg['COLOR'][module])
    TEXT_FORMAT = (fg(var), attr(0))
    print(str.format('[%s{}%s] {}', module, text) % TEXT_FORMAT)
    sys.stdout.flush()
