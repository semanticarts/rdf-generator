import argparse, tempfile
from rdflib import Graph
import pprint

# command line parameters are
#   Scale
#   RDF config path
#   Output path

class writable_dir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir=values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError("writable_dir:{0} is not a valid path".format(prospective_dir))
        if os.access(prospective_dir, os.W_OK):
            setattr(namespace,self.dest,prospective_dir)
        else:
            raise argparse.ArgumentTypeError("writable_dir:{0} is not a writable dir".format(prospective_dir))

ldir = tempfile.mkdtemp()

parser = argparse.ArgumentParser()
parser.add_argument("config", help="SHACL configuration file", type=argparse.FileType('r'))
parser.add_argument("scale", help="Base scaling for data generation", type=int, default=10)
parser.add_argument("-o", "--output", help="Output directory [default is .]", action=writable_dir, default=ldir)
args=parser.parse_args()

# print (args)

# Read in RDF configuration

g = Graph()
g.parse(args.config, format="turtle")

# Get list of classes and relative scales using http://tools.semanticarts.com/generator/instanceScaling

qres = g.query(
    """SELECT DISTINCT ?class ?scaling
       WHERE {
          [ sh:targetClass ?class ; gen:instanceScaling ?scaling ]
       }""")

scaling = dict((str(res[0]), float(str(res[1]))) for res in qres)

print (scaling)