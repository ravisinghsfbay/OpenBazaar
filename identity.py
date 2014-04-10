import zmq
import sys
import hashlib
import obelisk
import broadcast
import forge
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

class Blockchain:

    def __init__(self):
        self.blocks = []
        self.processor = []

    def accept(self, block):
        self.processor.append(block)

    def update(self):
        process = self.processor
        self.processor = []
        for block in process:
            self.process(block)

    def process(self, block):
        print "Processing block...", block
        if not block.complete:
            self.postpone(block)
            return
        if not block.verify():
            # Invalid block so reject it.
            print >> sys.stderr, "Rejecting invalid block."
            return
        # check hash of keys + values matches root hash
        # fetch tx height/index associated with block
        # compare to list
        # remove all items higher from blocks and kv map
        #
        pass

    def postpone(self, block):
        # readd for later processing
        self.accept(block)

    @property
    def genesis_hash(self):
        return "*We are butterflies*"

    @property
    def last_hash(self):
        if not self.blocks:
            return self.genesis_hash
        return self.blocks[-1].header.tx_hash

class Pool:

    def __init__(self, chain):
        self.txs = []
        self.chain = chain

    def add(self, tx):
        self.txs.append(tx)
        # add timeout/limit logic here.
        # for now create new block for every new registration.
        self.fabricate_block()

    def fabricate_block(self):
        print "Fabricating new block!"
        txs = self.txs
        self.txs = []
        block = Block(txs, self.chain.last_hash)
        block.register()
        self.chain.accept(block)

class BlockHeader:

    def __init__(self, tx_hash, root_hash):
        self.tx_hash = tx_hash
        self.root_hash = root_hash

class Block:

    def __init__(self, txs, prev_hash, header=None):
        self.txs = txs
        self.prev_hash = prev_hash
        self.header = header
        self.complete = False

    def register(self):
        # register block in the bitcoin blockchain
        root_hash = self.calculate_root_hash()
        # create tx with root_hash as output
        self.header = BlockHeader(None, root_hash)
        forge.send_root_hash(root_hash, self._registered)

    def _registered(self, tx_hash):
        self.header.tx_hash = tx_hash
        self.complete = True
        print "Registered block, awaiting confirmation:", tx_hash.encode("hex")

    def calculate_root_hash(self):
        h = hashlib.new("ripemd160")
        h.update(self.prev_hash)
        for key, value in self.txs:
            h.update(key)
            h.update(value)
        return h.digest()

    def verify(self):
        if self.header is None:
            return False
        root_hash = self.calculate_root_hash()
        return self.header.root_hash == root_hash

    def is_next(self, block):
        return block.header.tx_hash == self.prev_hash

    def __repr__(self):
        return "<Block tx_hash=%s root_hash=%s prev=%s txs=%s>" % (
            self.header.tx_hash.encode("hex") if self.header else None,
            self.header.root_hash.encode("hex") if self.header else None,
            self.prev_hash.encode("hex"), self.txs)

class ZmqPoller:

    def __init__(self, pool):
        self.pool = pool
        self.context = zmq.Context()
        self.recvr = self.context.socket(zmq.PULL)
        self.recvr.bind("tcp://*:5557")

    def update(self):
        try:
            name_reg = self.recvr.recv(flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            return
        value = self.recvr.recv()
        self.pool.add((name_reg, value))

def main(argv):
    chain = Blockchain()
    pool = Pool(chain)
    zmq_poller = ZmqPoller(pool)
    lc_zmq = LoopingCall(zmq_poller.update)
    lc_zmq.start(0.1)
    lc_chain = LoopingCall(chain.update)
    lc_chain.start(6)
    reactor.run()
    return

if __name__ == "__main__":
    main(sys.argv)
