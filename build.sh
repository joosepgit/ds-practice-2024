python -m pip install -r fraud_detection/requirements.txt -r orchestrator/requirements.txt \
 -r suggestions/requirements.txt -r  transaction_verification/requirements.txt 

cp spec/pb/fraud_detection.proto fraud_detection/src/grpc_gen/fraud_detection.proto
cp spec/pb/suggestions.proto fraud_detection/src/grpc_gen/suggestions.proto

cp spec/pb/transaction_verification.proto transaction_verification/src/grpc_gen/transaction_verification.proto
cp spec/pb/fraud_detection.proto transaction_verification/src/grpc_gen/fraud_detection.proto

cp spec/pb/suggestions.proto suggestions/src/grpc_gen/suggestions.proto

cp spec/pb/order_queue.proto order_queue/src/grpc_gen/order_queue.proto

cp spec/pb/order_executor.proto order_executor/src/grpc_gen/order_executor.proto
cp spec/pb/order_queue.proto order_executor/src/grpc_gen/order_queue.proto
cp spec/pb/db.proto order_executor/src/grpc_gen/db.proto

cp spec/pb/db.proto dbnode/src/grpc_gen/db.proto

cp spec/pb/payment.proto payment/src/grpc_gen/payment.proto

cp spec/pb/fraud_detection.proto orchestrator/src/grpc_gen/fraud_detection.proto
cp spec/pb/transaction_verification.proto orchestrator/src/grpc_gen/transaction_verification.proto
cp spec/pb/suggestions.proto orchestrator/src/grpc_gen/suggestions.proto
cp spec/pb/order_queue.proto orchestrator/src/grpc_gen/order_queue.proto

python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. fraud_detection/src/grpc_gen/*.proto

python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. transaction_verification/src/grpc_gen/*.proto

python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. suggestions/src/grpc_gen/*.proto

python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. order_queue/src/grpc_gen/*.proto

python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. order_executor/src/grpc_gen/*.proto

 python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. dbnode/src/grpc_gen/*.proto

  python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. payment/src/grpc_gen/*.proto

 python -m grpc_tools.protoc -I. \
 --python_out=. --pyi_out=. --grpc_python_out=. orchestrator/src/grpc_gen/*.proto