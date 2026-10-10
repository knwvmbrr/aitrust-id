"""Bounded non-content identities; digest equality is not authenticity or accuracy."""
import hashlib
import json
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Digest=Annotated[str,StringConstraints(pattern=r'^[a-f0-9]{64}$')]
Package=Annotated[str,StringConstraints(pattern=r'^[A-Za-z0-9_.-]{1,80}$')]
Version=Annotated[str,StringConstraints(pattern=r'^[0-9][A-Za-z0-9_.+!=-]{0,79}$')]

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)

class RedactorSources(Strict):
    app:Digest
    model_loader:Digest
    requirements_lock:Digest
    identity_contract:Digest
    identity_builder:Digest

class RedactorConfiguration(Strict):
    language:Literal['en']='en'
    python:Annotated[str,StringConstraints(pattern=r'^[0-9]+\.[0-9]+\.[0-9]+$')]
    platform_machine:Literal['x86_64','aarch64','arm64','AMD64']
    dependency_records:dict[Package,Digest]=Field(min_length=1,max_length=128)
    model_name:Literal['en_core_web_sm']='en_core_web_sm'
    model_version:Literal['3.8.0']='3.8.0'
    model_manifest_sha256:Digest
    sources:RedactorSources
    dependencies:dict[Package,Version]=Field(min_length=1,max_length=128)
    recognizer_configuration_sha256:Digest
    recognizer_count:int=Field(ge=1,le=128)
    analysis_score_threshold:Literal[0.0]=0.0
    email_suffix_refresh:Literal[False]=False
    anonymization:Literal['presidio-default-replace']='presidio-default-replace'

    @model_validator(mode='before')
    @classmethod
    def scalar_types(cls,value):
        if isinstance(value,dict):
            if 'analysis_score_threshold' in value and type(value['analysis_score_threshold']) not in (int,float):
                raise ValueError('Numeric threshold required')
            if 'email_suffix_refresh' in value and type(value['email_suffix_refresh']) is not bool:
                raise ValueError('Boolean refresh setting required')
        return value

    @model_validator(mode='after')
    def distribution_keys(self):
        if set(self.dependencies)!=set(self.dependency_records):
            raise ValueError('Distribution identities differ')
        return self



def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

class RedactorIdentity(Strict):
    version:Literal['presidio-offline-en/v1']='presidio-offline-en/v1'
    sha256:Digest
    configuration:RedactorConfiguration

    @model_validator(mode='after')
    def checked_digest(self):
        if self.sha256!=digest({'version':self.version,'configuration':self.configuration.model_dump()}):
            raise ValueError('Redactor identity digest differs')
        return self


def redactor_identity(configuration):
    config=RedactorConfiguration.model_validate(configuration).model_dump()
    value={'version':'presidio-offline-en/v1','configuration':config}
    return RedactorIdentity.model_validate({**value,'sha256':digest(value)}).model_dump()

class PipelineConfiguration(Strict):
    gateway_source_sha256:Digest
    normalization_source_sha256:Digest
    normalization_data_sha256:Digest
    normalization_id:Literal['NFC-Unicode-15.0.0/v1']='NFC-Unicode-15.0.0/v1'
    normalization_stages:Literal['before-redaction-and-before-evaluation']='before-redaction-and-before-evaluation'
    asserted_rule_tag:Literal['PS']='PS'
    rule_floor:Literal[0.7]=0.7
    procedural_tag:Literal['PII_REDACTED']='PII_REDACTED'
    redactor:RedactorIdentity

class PipelineIdentity(Strict):
    version:Literal['local-text-pipeline/v1']='local-text-pipeline/v1'
    sha256:Digest
    configuration:PipelineConfiguration

    @model_validator(mode='after')
    def checked_digest(self):
        if self.sha256!=digest({'version':self.version,'configuration':self.configuration.model_dump()}):
            raise ValueError('Pipeline identity digest differs')
        return self


def pipeline_identity(configuration):
    config=PipelineConfiguration.model_validate(configuration).model_dump()
    value={'version':'local-text-pipeline/v1','configuration':config}
    return PipelineIdentity.model_validate({**value,'sha256':digest(value)}).model_dump()
