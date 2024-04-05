# Documentation

## Organization

The project has been restructured from globally importing the generic utils directory to generating gRPC services from the spec/pb directory into all services that need them. This has been integrated with the docker setup and enables the IDE to work properly in a local development setup. This is necessary for ensuring correct type hints and a smoother development experience over all.

## Development setup

To run the project locally, simply clone the repository and run the following commands in the root directory.
```bash
./build.sh
docker compose up
```
To stop the services and clean generated files, run the following.
```bash
docker compose down
./clean.sh
```
## Errors

The frontend has been updated to display error messages returned from the server in case of Axios errors.

## Orchestrator

The orchestrator has been updated to call 3 remote procedures in parallel using the gather function from asyncio.

## Services

All services are fully functional in terms of logging and gRPC/HTTP communication. They currently implement dummy business logic.

### Fraud detection

Fraud detection checks two dummy conditions. It triggers if the selected country is Finland or the CVV code is 000.

### Transaction verification

Transaction verification verifies the input data. It checks several conditions that are cumbersome to list here. See the contents of the service in transaction_verification/src/app.py for detailed information.

### Suggestions

Suggestions always returns 3 suggestions with a random id, title and author. Each of which have been randomly selected from 4 possible options


