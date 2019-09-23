import argparse, re, os, random, glob
from rdflib import Graph, Literal, BNode, Namespace, URIRef
from rdflib.namespace import RDF, RDFS
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

parser = argparse.ArgumentParser()
parser.add_argument("config", help="SHACL configuration file", type=argparse.FileType('r'))
parser.add_argument("scale", help="Base scaling for data generation", type=int, default=10)
parser.add_argument("-o", "--output", help="Output directory [default is .]", action=writable_dir, default=".")
parser.add_argument("-c", "--clear", help="Clear output directory before generation", action='store_true')
parser.add_argument("--instance_ns", help="Namespace for generated instances, as defined in configuration [default is data]", default="data")
args=parser.parse_args()

# print (args)

if (args.clear):
    for old in glob.iglob(f"{args.output}/gen_*.ttl"):
        os.remove(old)

# Read in RDF configuration

config = Graph()
config.parse(args.config, format="turtle")

# Get list of classes and relative scales using http://tools.semanticarts.com/generator/instanceScaling

qres = config.query(
    """SELECT DISTINCT ?class ?scaling
       WHERE {
          [ sh:targetClass ?class ; gen:instanceScaling ?scaling ]
       }""")

scaling = dict((str(res[0]), float(str(res[1]))) for res in qres)

out_count = 1
out_limit = 1000
out = None

def new_graph():
    global out
    out = Graph()
    out.namespace_manager = config.namespace_manager
    
def flush(force=False):
    global out, out_count, out_limit
    if (force or len(out) >= out_limit):
        out.serialize(destination=f"{args.output}/gen_{out_count}.ttl", format='turtle')
        out_count += 1
        new_graph()
        
new_graph()

DATA = Namespace(config.store.namespace(args.instance_ns))

def getRelations(subjectClass):
    relations = []
    qres = config.query(
        """SELECT DISTINCT ?property ?targetClass ?min ?max
           WHERE {
              ?classShape sh:targetClass <%s> ; sh:property ?propShape .
              ?propShape sh:class ?targetClass; sh:path ?property .
              OPTIONAL { ?propShape sh:minCount ?min }
              OPTIONAL { ?propShape sh:maxCount ?max }
           }""" % subjectClass)
    for property, targetClass, min, max in qres:
        min = int(str(min)) if min else 0
        max = int(str(max)) if max else min if min > 0 else 1
        targetName = re.match(r'.*[/#](.*)', str(targetClass)).group(1)
        targetScale = int(scaling[str(targetClass)] * args.scale)
        relations.append((property, targetName, targetScale, min, max))
    return relations      

for genClass in scaling:
    class_u = URIRef(genClass)
    className = re.match(r'.*[/#](.*)', genClass).group(1)
    relations = getRelations(genClass)
    for instance in range(int(scaling[genClass] * args.scale)):
        instance_u = URIRef(DATA[f"{className}_{instance}"])
        out.add((instance_u, RDF.type, class_u))
        out.add((instance_u, RDFS.label, Literal(f"{className} {instance}")))
        
        for property, targetName, targetScale, min, max in relations:
             cardinality = random.randint(min, max)
             for related in range(cardinality):
                related_u = DATA["%s_%d" % (targetName, random.randrange(targetScale))]
                out.add((instance_u, property, related_u))
        
        flush()

flush(True)