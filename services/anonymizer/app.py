"""Detected PII redaction with build-provisioned English language assets."""
from model_identity import verify_installed
MODEL_IDENTITY = verify_installed()
from fastapi import FastAPI
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from pydantic import BaseModel, ConfigDict, Field
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.predefined_recognizers import EmailRecognizer
import tldextract

app=FastAPI(title='AITrust-ID Anonymizer')
app.add_middleware(RequestBodyLimitMiddleware,max_body_size=1_250_000)
provider=NlpEngineProvider(nlp_configuration={'nlp_engine_name':'spacy','models':[{'lang_code':'en','model_name':'en_core_web_sm'}]})
analyzer=AnalyzerEngine(nlp_engine=provider.create_engine(),supported_languages=['en'])
class OfflineEmailRecognizer(EmailRecognizer):
    # Use tldextract's packaged suffix snapshot; never refresh it at inference.
    extractor=tldextract.TLDExtract(suffix_list_urls=(),cache_dir=None)
    def validate_result(self,pattern_text):
        return self.extractor(pattern_text).fqdn != ''
analyzer.registry.remove_recognizer('EmailRecognizer')
analyzer.registry.add_recognizer(OfflineEmailRecognizer())
import ipaddress
import re
IPV6_TOKEN=re.compile(r'(?<![0-9A-Za-z_:.])([0-9A-Fa-f:.]{2,64})(?![0-9A-Za-z_:.%])')
IPV6_LABEL_TOKEN=re.compile(r'(?<![0-9A-Za-z_:.])(?P<label>ip(?:v6)?(?:_?address)?|addr(?:ess)?|host):(?P<value>[0-9A-Fa-f:.]{2,64})(?![0-9A-Za-z_:.%])',re.I)
def complete_ipv6_spans(text):
    candidates=[(match.start(1),match[1]) for match in IPV6_TOKEN.finditer(text)]
    for match in IPV6_LABEL_TOKEN.finditer(text):
        # A non-hexadecimal label cannot be a hextet of the address. Never
        # split a valid or malformed address at an internal separator colon.
        if any(char not in '0123456789abcdefABCDEF' for char in match['label']):
            candidates.append((match.start('value'),match['value']))
    result=[]
    for start,token in candidates:
        value=token.rstrip('.')
        if ':' not in value:continue
        try:address=ipaddress.ip_address(value)
        except ValueError:continue
        if address.version==6:result.append((start,start+len(value)))
    return sorted(set(result))

from presidio_analyzer.predefined_recognizers import IpRecognizer
from presidio_analyzer import RecognizerResult
class CompleteIPv6Recognizer(IpRecognizer):
    def analyze(self,text,entities,nlp_artifacts=None):
        original=super().analyze(text,entities,nlp_artifacts)
        if 'IP_ADDRESS' not in entities:return original
        full=complete_ipv6_spans(text)
        # Keep upstream IPv4/scoped behavior; replace only truncated candidates
        # wholly inside an independently parsed complete unscoped IPv6 token.
        kept=[r for r in original if not any(start<=r.start and r.end<=end and (start,end)!=(r.start,r.end) for start,end in full)]
        existing={(r.start,r.end) for r in kept}
        return kept+[RecognizerResult('IP_ADDRESS',start,end,0.6) for start,end in full if (start,end) not in existing]
analyzer.registry.remove_recognizer('IpRecognizer')
analyzer.registry.add_recognizer(CompleteIPv6Recognizer())

anonymizer=AnonymizerEngine()
from replay_metadata import identity
REDACTOR_IDENTITY=identity(analyzer,MODEL_IDENTITY)
class Doc(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text:str=Field(max_length=200_000)
@app.get('/healthz')
def healthz():return {'ok':True, 'model_identity':MODEL_IDENTITY}
@app.post('/redact')
def redact(doc:Doc):
    results=analyzer.analyze(text=doc.text,language='en',score_threshold=0.0)
    output=anonymizer.anonymize(text=doc.text,analyzer_results=results)
    return {'text':output.text,'entities':sorted({r.entity_type for r in results}),'entity_count':len(results),'identity':REDACTOR_IDENTITY}
