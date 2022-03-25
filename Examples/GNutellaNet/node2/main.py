from nodeGNutella import nodeGNutella
import sys

if __name__ == "__main__":
    node = nodeGNutella(sys.argv[1], sys.argv[2], sys.argv[3])
    node.start()