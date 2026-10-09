import os
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings
from app.models import Base

@pytest.fixture
def app(tmp_path):
    url = os.getenv('TEST_DATABASE_URL', f'sqlite:///{tmp_path}/test.db')
    application = create_app(Settings(database_url=url, jwt_secret='test-secret-'*5, llm_enabled=False, openworker_enabled=False))
    Base.metadata.drop_all(application.state.engine)
    Base.metadata.create_all(application.state.engine)
    yield application
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()

@pytest.fixture
def client(app):
    return TestClient(app)

def account(client, role, name):
    body = dict(name=name,email=name+'@example.test',role=role,password='Test-only-password-123!')
    r = client.post('/api/v1/users',json=body)
    assert r.status_code == 201, r.text
    u = r.json()
    r = client.post('/api/v1/auth/login',json={'email':body['email'],'password':body['password']})
    assert r.status_code == 200, r.text
    return u, {'Authorization':'Bearer '+r.json()['access_token']}

@pytest.fixture
def family(client):
    parent, ph = account(client,'PROTECTED_PERSON','parent')
    carer, ch = account(client,'CAREGIVER','caregiver')
    outsider, oh = account(client,'CAREGIVER','outsider')
    r=client.post('/api/v1/families',headers=ch,json={'name':'Gupta Family'})
    assert r.status_code==201, r.text
    f=r.json()
    assert client.post(f"/api/v1/families/{f['id']}/members",headers=ph,json={'user_id':parent['id'],'relationship':'Father','join_code':f['join_code']}).status_code==201
    return dict(parent=parent,carer=carer,outsider=outsider,ph=ph,ch=ch,oh=oh,f=f)

@pytest.fixture
def consent(client,family):
    r=client.post('/api/v1/consents',headers=family['ph'],json={'family_id':family['f']['id'],'protected_person_id':family['parent']['id']})
    assert r.status_code==201, r.text
    return r.json()
