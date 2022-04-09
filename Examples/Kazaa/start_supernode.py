from supernodeKazaa import supernodeKazaa
import sys

if __name__ == "__main__":
    node = supernodeKazaa(sys.argv[1], sys.argv[2], sys.argv[3])
    node.start()
