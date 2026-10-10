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
