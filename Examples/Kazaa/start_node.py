from nodeKazaa import nodeKazaa
import sys

if __name__ == "__main__":
    node = nodeKazaa(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    node.start()
