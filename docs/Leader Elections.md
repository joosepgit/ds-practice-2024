# Leader elections
For leader election the bulling algorithm was implemented. New leader is elected based on the ID of the node. This method allows for relativly quick election with maximum of n(n-1) messages (broadcast for every alive node).

Elections are started when any active node will not detect heartbeat from current leader in threshold time (1min by default, 10s during tests)

# Consistency
For consistencty, we use the chain replication algorithm. The database nodes dbnode* all implement leader election by bullying. The current leader is the only node that gets hit with direct requests. If the request is a read, the read is made directly on the leader node. If it is a write, the write is first propagated to the tail node, which writes first. After that, the earlier nodes perform the write sequentially until the acknowledgement reaches the leader. Only then does the leader perform the write. 