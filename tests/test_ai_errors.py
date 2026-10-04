import io
import json
import urllib.error
import pytest
from grok.ai import PROVIDERS


class Response(io.BytesIO):
    pass


@pytest.mark.parametrize('provider', list(PROVIDERS))
def test_transport_success(monkeypatch, provider):
    observed = []
    data = {'candidates':[{'content':{'parts':[{'text':'answer'}]}}]} if provider == 'Gemini' else {'choices':[{'message':{'content':'answer'}}]}
    if provider == 'Claude':
        data = {'content':[{'type':'text','text':'answer'}]}
    class Client:
        def open(self, request, timeout):
            observed.append(request)
            assert timeout == 60
            return Response(json.dumps(data).encode())
    monkeypatch.setattr('urllib.request.build_opener', lambda *_: Client())
    assert PROVIDERS[provider].request('fixture-key', 'test-model', [{'role':'user','content':'fixture'}]) == 'answer'
    assert observed[0].method == 'POST'


@pytest.mark.parametrize('status,expected', [(401,'key'),(403,'account'),(404,'Model'),(429,'quota'),(503,'503')])
def test_sanitized_error(monkeypatch, status, expected):
    class Client:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(request.full_url, status, 'secret-sentinel', {}, io.BytesIO(b'private provider details'))
    monkeypatch.setattr('urllib.request.build_opener', lambda *_: Client())
    with pytest.raises(ValueError) as exc:
        PROVIDERS['OpenAI'].request('fixture-key', 'test-model', [])
    assert expected in str(exc.value)
    assert 'secret-sentinel' not in str(exc.value)
    assert 'private' not in str(exc.value)


def test_invalid_model_no_network(monkeypatch):
    monkeypatch.setattr('urllib.request.build_opener', lambda *_: pytest.fail('Network must not run'))
    with pytest.raises(ValueError):
        PROVIDERS['OpenAI'].request('fixture', '', [])


def test_offline(monkeypatch):
    class Client:
        def open(self, *args, **kwargs):
            raise urllib.error.URLError('private internal proxy URL')
    monkeypatch.setattr('urllib.request.build_opener', lambda *_: Client())
    with pytest.raises(ValueError, match='connection'):
        PROVIDERS['OpenAI'].request('fixture', 'model', [])
