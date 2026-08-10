"""Parsian / PEC — WSDL endpoints and the fixed values its protocol defines."""

NAME = "parsian"

SALE_WSDL = "https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx?wsdl"
CONFIRM_WSDL = "https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx?wsdl"

REDIRECT_URL = "https://pec.shaparak.ir/NewIPG/?token={token}"

SALE_OPERATION = "SalePaymentRequest"
CONFIRM_OPERATION = "ConfirmPayment"

#: Both services take their arguments inside a single ``requestData`` element.
REQUEST_WRAPPER = "requestData"

#: PEC's "no error" status, on both operations.
SUCCESS_STATUS = 0
