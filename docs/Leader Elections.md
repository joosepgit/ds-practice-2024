# Leader elections
For leader election the bulling algorithm was implemented. New leader is elected based on the ID of the node. This method allows for relativly quick election with maximum of n(n-1) messages (broadcast for every alive node).

Elections are started when any active node will not detect heartbeat from current leader in threshold time (1min by default, 10s during tests)