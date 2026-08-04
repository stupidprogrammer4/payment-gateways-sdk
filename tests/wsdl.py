"""Real WSDL documents for PEC's two services, for the live SOAP tests to serve.

These are the actual contracts ``zeep`` has to read: the same target namespaces, the same
``requestData`` wrapper, and the same field types PEC declares — ``OrderId`` and ``Token`` as
``long``, ``Status`` as ``int``. That matters, because ``zeep`` builds the request body *from the
schema*: if the SDK sent a string where the WSDL says ``long``, zeep would raise while serialising
rather than at the bank, and only a real WSDL surfaces that.

``{endpoint}`` is filled in with the test server's address so zeep posts back to it.
"""

SALE_NS = "https://pec.shaparak.ir/NewIPGServices/Sale/SaleService"
CONFIRM_NS = "https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService"

SALE_WSDL = """<?xml version="1.0" encoding="utf-8"?>
<wsdl:definitions
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:tns="{ns}"
    xmlns:s="http://www.w3.org/2001/XMLSchema"
    xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
    targetNamespace="{ns}">
  <wsdl:types>
    <s:schema elementFormDefault="qualified" targetNamespace="{ns}">
      <s:element name="SalePaymentRequest">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="requestData"
                       type="tns:SalePaymentRequestData"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="SalePaymentRequestData">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="LoginAccount" type="s:string"/>
          <s:element minOccurs="1" maxOccurs="1" name="Amount" type="s:long"/>
          <s:element minOccurs="1" maxOccurs="1" name="OrderId" type="s:long"/>
          <s:element minOccurs="0" maxOccurs="1" name="CallBackUrl" type="s:string"/>
          <s:element minOccurs="0" maxOccurs="1" name="AdditionalData" type="s:string"/>
          <s:element minOccurs="0" maxOccurs="1" name="Originator" type="s:string"/>
        </s:sequence>
      </s:complexType>
      <s:element name="SalePaymentRequestResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="SalePaymentRequestResult"
                       type="tns:SalePaymentRequestResult"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="SalePaymentRequestResult">
        <s:sequence>
          <s:element minOccurs="1" maxOccurs="1" name="Status" type="s:int"/>
          <s:element minOccurs="0" maxOccurs="1" name="Message" type="s:string"/>
          <s:element minOccurs="1" maxOccurs="1" name="Token" type="s:long"/>
        </s:sequence>
      </s:complexType>
    </s:schema>
  </wsdl:types>
  <wsdl:message name="SalePaymentRequestSoapIn">
    <wsdl:part name="parameters" element="tns:SalePaymentRequest"/>
  </wsdl:message>
  <wsdl:message name="SalePaymentRequestSoapOut">
    <wsdl:part name="parameters" element="tns:SalePaymentRequestResponse"/>
  </wsdl:message>
  <wsdl:portType name="SaleServiceSoap">
    <wsdl:operation name="SalePaymentRequest">
      <wsdl:input message="tns:SalePaymentRequestSoapIn"/>
      <wsdl:output message="tns:SalePaymentRequestSoapOut"/>
    </wsdl:operation>
  </wsdl:portType>
  <wsdl:binding name="SaleServiceSoap" type="tns:SaleServiceSoap">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http"/>
    <wsdl:operation name="SalePaymentRequest">
      <soap:operation soapAction="{ns}/SalePaymentRequest" style="document"/>
      <wsdl:input><soap:body use="literal"/></wsdl:input>
      <wsdl:output><soap:body use="literal"/></wsdl:output>
    </wsdl:operation>
  </wsdl:binding>
  <wsdl:service name="SaleService">
    <wsdl:port name="SaleServiceSoap" binding="tns:SaleServiceSoap">
      <soap:address location="{endpoint}"/>
    </wsdl:port>
  </wsdl:service>
</wsdl:definitions>
"""

CONFIRM_WSDL = """<?xml version="1.0" encoding="utf-8"?>
<wsdl:definitions
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:tns="{ns}"
    xmlns:s="http://www.w3.org/2001/XMLSchema"
    xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
    targetNamespace="{ns}">
  <wsdl:types>
    <s:schema elementFormDefault="qualified" targetNamespace="{ns}">
      <s:element name="ConfirmPayment">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="requestData"
                       type="tns:ConfirmRequestData"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="ConfirmRequestData">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="LoginAccount" type="s:string"/>
          <s:element minOccurs="1" maxOccurs="1" name="Token" type="s:long"/>
        </s:sequence>
      </s:complexType>
      <s:element name="ConfirmPaymentResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="ConfirmPaymentResult"
                       type="tns:ConfirmPaymentResult"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="ConfirmPaymentResult">
        <s:sequence>
          <s:element minOccurs="1" maxOccurs="1" name="Status" type="s:int"/>
          <s:element minOccurs="0" maxOccurs="1" name="CardNumberMasked" type="s:string"/>
          <s:element minOccurs="1" maxOccurs="1" name="Token" type="s:long"/>
          <s:element minOccurs="0" maxOccurs="1" name="RRN" type="s:string"/>
        </s:sequence>
      </s:complexType>
    </s:schema>
  </wsdl:types>
  <wsdl:message name="ConfirmPaymentSoapIn">
    <wsdl:part name="parameters" element="tns:ConfirmPayment"/>
  </wsdl:message>
  <wsdl:message name="ConfirmPaymentSoapOut">
    <wsdl:part name="parameters" element="tns:ConfirmPaymentResponse"/>
  </wsdl:message>
  <wsdl:portType name="ConfirmServiceSoap">
    <wsdl:operation name="ConfirmPayment">
      <wsdl:input message="tns:ConfirmPaymentSoapIn"/>
      <wsdl:output message="tns:ConfirmPaymentSoapOut"/>
    </wsdl:operation>
  </wsdl:portType>
  <wsdl:binding name="ConfirmServiceSoap" type="tns:ConfirmServiceSoap">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http"/>
    <wsdl:operation name="ConfirmPayment">
      <soap:operation soapAction="{ns}/ConfirmPayment" style="document"/>
      <wsdl:input><soap:body use="literal"/></wsdl:input>
      <wsdl:output><soap:body use="literal"/></wsdl:output>
    </wsdl:operation>
  </wsdl:binding>
  <wsdl:service name="ConfirmService">
    <wsdl:port name="ConfirmServiceSoap" binding="tns:ConfirmServiceSoap">
      <soap:address location="{endpoint}"/>
    </wsdl:port>
  </wsdl:service>
</wsdl:definitions>
"""


def sale_wsdl(endpoint: str) -> str:
    return SALE_WSDL.format(ns=SALE_NS, endpoint=endpoint)


def confirm_wsdl(endpoint: str) -> str:
    return CONFIRM_WSDL.format(ns=CONFIRM_NS, endpoint=endpoint)
