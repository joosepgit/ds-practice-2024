# Interservice communication
Communication between services inside the system back-end is done using the gRPC framework.
## Messages structure
Message definitions are descried in spec/pb/*.proto files.

[//]: # (TODO: update the structure from mockup to the actual one after it is implemented)

## Causality, vector clocks

The system utilizes vector clocks to establish causality. The checkout procedure has been implemented so that all services are initialized by the orchestrator in parallel. The data they need for processing is passed during initialization and is pushed into TTLCache for 60 seconds. Then the orchestrator initiates checkout by calling the transaction verification service, passing an empty vector clock.

### Transaction verification

Transaction verification performs 3 sequential checks and updates its vector clock accordingly. It calls fraud detection if all checks pass, passing its vector clock with the request.

### Fraud detection

Fraud detection merges its vector clock with the one passed from transaction verification, performs 2 sequential dummy checks and updates the merged vector clock accordingly. It calls suggestions if all checks pass, passing its vector clock with the request.

### Suggestions

Suggestions service merges its vector clock with the one passed from fraud detection, generates a random suggestion and pushes it into its cache based on the order id. It then returns the vector clock and metadata parameters. 

### Propagation

Any error is immediately propagated back to the orchestrator, execution is stopped and the data is cleared. If there are no errors, then after success in the suggestions service, the vector clocks of fraud detection and transaction verification are incremented once more for sending a request.

### Suggestions query

Finally, if the checkout is completely successful, the orchestrator queries the generated suggestion from suggestions service based on order id and increments the suggestions service vector clock.

### Final checks

In each service, if the vector clock validity condition holds as described in the bonus task guide of practice session 5, all cached data is cleared and the response is returned to the end user.