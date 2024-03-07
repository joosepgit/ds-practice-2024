class FraudDetectionError(Exception):
    status_code = 400
    
    def __init__(self, message):            
        super().__init__(message)

class TransactionVerificationError(Exception):
    status_code = 400

    def __init__(self, message):            
        super().__init__(message)