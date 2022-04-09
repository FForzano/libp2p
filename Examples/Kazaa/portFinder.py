class portFinder:
    def __init__(self, min_port = 50000,max_port = 60000):
        self.min_port = min_port
        self.max_port = max_port
        self.current_port = min_port
    
    def give_port(self):
        if self.current_port == self.max_port:
            self.current_port == self.min_port
            return self.max_port
        
        self.current_port += 1
        return self.current_port -1
