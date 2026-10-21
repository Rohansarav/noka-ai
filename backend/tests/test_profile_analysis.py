"""The two input methods share a strict, reviewable, catalogue-bound analysis pipeline."""
import io
from types import SimpleNamespace
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.models import Skill
from backend.app.skill_extraction import extract, parse_upload, provider_schema, provider_extract
from backend.tests.test_profiles import database, client, create, docx_bytes, pdf_bytes, HEADERS, MIME


def catalogue(database):
    with Session(database) as db:
        return list(db.scalars(select(Skill).order_by(Skill.id)))


def model_payload(skills, mention='Python', excerpt='Python', canonical='Programming'):
    return {'skills':[{'mention':mention,'years':None,'evidence_excerpt':excerpt,'confidence':'medium','canonical_skill_ids':[s.id for s in skills if s.canonical_name==canonical]}]}


def test_local_aliases_are_merged_without_losing_reviewed_identity(database):
    skills=catalogue(database)
    result=extract('Python programming and coding, alongside writing reports.',skills)
    programming=next(s.id for s in skills if s.canonical_name=='Programming')
    candidates=[c for c in result.candidates if c.options==[programming]]
    assert len(candidates)==1 and result.duplicates_merged==2
    assert {m.casefold() for m in candidates[0].mentions}=={'python','programming','coding'}


def test_manual_and_document_text_use_the_same_contract_and_options(client, database):
    pid=create(client)
    for factory,name,mime in ((pdf_bytes,'demo.pdf','application/pdf'),(docx_bytes,'demo.docx',MIME)):
        data=factory()
        manual=parse_upload(data,name,mime)
        upload=client.post(f'/api/profiles/{pid}/analysis',files={'file':(name,data,mime)},data={'use_ai':'false'},headers=HEADERS)
        typed=client.post(f'/api/profiles/{pid}/analysis',data={'text':manual,'use_ai':'false'},headers=HEADERS)
        assert upload.status_code==typed.status_code==200
        assert upload.json()==typed.json()
        assert upload.json()['schema_version']=='skill-review-v2'
        assert len(upload.json()['candidates'])>=3
    assert client.get('/api/profiles/current').json()['profile']['skills']==[]


def test_openai_is_bound_to_catalogue_and_same_for_both_inputs(client, database, monkeypatch):
    pid=create(client)
    seen=[]
    def grounded(text, skills):
        seen.append(text)
        return provider_schema(skills).model_validate(model_payload(skills))
    monkeypatch.setattr('backend.app.skill_extraction.provider_extract',grounded)
    content=docx_bytes()
    text=parse_upload(content,'demo.docx',MIME)
    uploaded=client.post(f'/api/profiles/{pid}/analysis',files={'file':('demo.docx',content,MIME)},data={'use_ai':'true'},headers=HEADERS)
    manual=client.post(f'/api/profiles/{pid}/analysis',data={'text':text,'use_ai':'true'},headers=HEADERS)
    assert uploaded.json()==manual.json() and len(seen)==2
    assert uploaded.json()['mode']=='openai'
    assert uploaded.json()['candidates'][0]['options']==[s.id for s in catalogue(database) if s.canonical_name=='Programming']


def test_reasoned_mapping_resolves_supported_free_form_mentions(database,monkeypatch):
    skills=catalogue(database)
    text='I inspected model outputs for bias and recorded deviations.'
    monkeypatch.setattr('backend.app.skill_extraction.provider_extract',lambda text, skills:model_payload(skills,'model oversight',text,'Monitoring'))
    result=extract(text,skills,True)
    assert result.mode=='openai' and result.candidates[0].mapping=='reasoned'
    assert result.candidates[0].options==[s.id for s in skills if s.canonical_name=='Monitoring']


def test_schema_rejects_unknown_ids_and_extra_output_then_falls_back(database,monkeypatch):
    skills=catalogue(database)
    for invalid in ({'skills':[{'mention':'Python','years':None,'confidence':'high','evidence_excerpt':'Python','canonical_skill_ids':['invented']}]},{'skills':[],'secret':'unexpected'}):
        monkeypatch.setattr('backend.app.skill_extraction.provider_extract',lambda text, skills:invalid)
        result=extract('Python programming and writing are my skills.',skills,True)
        assert result.mode=='manual_fallback'
        assert result.candidates and all('invented' not in c.options for c in result.candidates)


def test_missing_evidence_is_excluded_and_no_proficiency_is_auto_confirmed(database,monkeypatch):
    skills=catalogue(database)
    monkeypatch.setattr('backend.app.skill_extraction.provider_extract',lambda text, skills:model_payload(skills,excerpt='Invented quote'))
    result=extract('Python programming and writing are my skills.',skills,True)
    assert not result.candidates and result.warnings


def test_document_line_breaks_do_not_turn_a_real_excerpt_into_an_unmapped_dead_end(database,monkeypatch):
    skills=catalogue(database)
    monkeypatch.setattr('backend.app.skill_extraction.provider_extract',lambda text, skills:model_payload(skills,excerpt='Python programming'))
    result=extract('I used Python\nprogramming to build useful software.',skills,True)
    assert result.mode=='openai' and len(result.candidates)==1 and not result.warnings


def test_incomplete_provider_response_is_never_used(database,monkeypatch):
    class FakeClient:
        def __init__(self,**kwargs):self.responses=self
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def parse(self,**kwargs):return SimpleNamespace(status='incomplete',output_parsed=kwargs['text_format'].model_validate({'skills':[]}))
    from pydantic import SecretStr
    monkeypatch.setattr('backend.app.skill_extraction.get_settings',lambda:SimpleNamespace(openai_api_key=SecretStr('test-key'),openai_model='configured-model'))
    monkeypatch.setattr('openai.OpenAI',FakeClient)
    result=extract('Python programming and writing are my skills.',catalogue(database),True)
    assert result.mode=='manual_fallback' and result.candidates


def test_actionable_errors_for_short_manual_input_and_scanned_pdf(client):
    pid=create(client)
    response=client.post(f'/api/profiles/{pid}/analysis',data={'text':'short'},headers=HEADERS)
    assert response.status_code==422 and '20 characters' in response.json()['error']['message']
    writer=PdfWriter();writer.add_blank_page(width=612,height=792);stream=io.BytesIO();writer.write(stream)
    response=client.post(f'/api/profiles/{pid}/analysis',files={'file':('scan.pdf',stream.getvalue(),'application/pdf')},headers=HEADERS)
    assert response.status_code==422 and 'Scanned PDFs' in response.json()['error']['message']


def test_analysis_ownership_and_csrf_and_generic_mime(client):
    pid=create(client)
    with TestClient(app) as other:
        assert other.post(f'/api/profiles/{pid}/analysis',data={'text':'Python programming and writing.'},headers=HEADERS).status_code==404
    assert client.post(f'/api/profiles/{pid}/analysis',data={'text':'Python programming and writing.'}).status_code==403
    assert client.post(f'/api/profiles/{pid}/analysis',files={'file':('demo.pdf',pdf_bytes(),'application/octet-stream')},data={'use_ai':'false'},headers=HEADERS).status_code==200
