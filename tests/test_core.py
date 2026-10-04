import json
import threading
import uuid
from pathlib import Path
import pytest
from PySide6.QtCore import QRect
from grok import files
from grok.dock import geometry
from grok.storage import Settings, History
from grok.ai import PROVIDERS, NoRedirect
from grok.windows import Vault


@pytest.mark.parametrize('name', ['..', 'a/b', 'a\\b', 'CON.txt', 'NUL', 'a.', 'a ', 'x:y', ''])
def test_unsafe_names(name):
    with pytest.raises(ValueError):
        files.valid_name(name)


def test_copy_move_rename_create(tmp_path):
    src = tmp_path / 'source'
    src.mkdir()
    file = src / 'sample.txt'
    file.write_text('safe fixture')
    dest = tmp_path / 'dest'
    dest.mkdir()
    files.transfer([str(file)], str(dest))
    assert (dest / file.name).read_text() == 'safe fixture'
    assert file.exists()
    new = files.rename(dest / file.name, 'renamed.txt')
    assert Path(new).exists()
    folder = files.create_folder(dest, 'nested')
    files.transfer([new], folder, move=True)
    assert not Path(new).exists()
    assert (Path(folder) / 'renamed.txt').exists()


def test_collision_batch_preflight(tmp_path):
    src = tmp_path / 'src'; src.mkdir()
    dest = tmp_path / 'dest'; dest.mkdir()
    for n in ['a', 'b']:
        (src / n).write_text('source')
    (dest / 'b').write_text('protected')
    with pytest.raises(FileExistsError):
        files.transfer([src / 'a', src / 'b'], dest)
    assert not (dest / 'a').exists()
    assert (dest / 'b').read_text() == 'protected'


def test_recursive_and_self_copy(tmp_path):
    src = tmp_path / 'src'; src.mkdir()
    (src / 'child').mkdir(); (src / 'child' / 'data').write_text('nested')
    dest = tmp_path / 'dest'; dest.mkdir()
    files.transfer([src], dest)
    assert (dest / 'src' / 'child' / 'data').read_text() == 'nested'
    with pytest.raises(ValueError):
        files.transfer([src], src / 'child')


def test_cancellation_preserves_source(tmp_path):
    src = tmp_path / 'a'; src.write_text('keep')
    dest = tmp_path / 'dest'; dest.mkdir()
    cancel = threading.Event(); cancel.set()
    with pytest.raises(InterruptedError):
        files.transfer([src], dest, cancel=cancel)
    assert src.read_text() == 'keep'
    assert not (dest / 'a').exists()


def test_settings_roundtrip_and_corrupt(tmp_path):
    s = Settings(tmp_path)
    s.data['favorites'] = ['C:\\example']
    s.data['width'] = 640
    s.save()
    assert Settings(tmp_path).data['favorites'] == ['C:\\example']
    assert Settings(tmp_path).data['width'] == 640
    assert 'key' not in json.loads(s.path.read_text())
    s.path.write_text('{broken')
    assert Settings(tmp_path).recovered


def test_history_branch():
    h = History()
    for p in ['a', 'b', 'c']:
        h.push(p)
    assert h.step(-1) == 'b'
    h.index -= 1
    h.push('d')
    assert h.paths == ['a', 'b', 'd']
    assert h.step(1) is None


@pytest.mark.parametrize('area', [QRect(0, 0, 1920, 1040), QRect(-1920, -200, 1920, 1080), QRect(60, 0, 1306, 768), QRect(0, 0, 320, 400)])
@pytest.mark.parametrize('expanded', [True, False])
def test_dock_in_work_area(area, expanded):
    rect = geometry(area, 420, expanded, 0.5)
    assert area.contains(rect)
    assert rect.right() == area.right()
    assert rect.width() == min(area.width(), 420 if expanded else 42)


def test_vault_roundtrip():
    vault = Vault('GROK-test-' + uuid.uuid4().hex)
    try:
        vault.put('fixture', 'synthetic-test-value')
        assert vault.get('fixture') == 'synthetic-test-value'
        vault.remove('fixture')
        assert vault.get('fixture') is None
    finally:
        vault.remove('fixture')


@pytest.mark.parametrize('provider', list(PROVIDERS))
def test_provider_payload(provider):
    p = PROVIDERS[provider]
    url, headers, body = p.encode('synthetic', 'example-model', [{'role':'user','content':'hello'}])
    assert url.startswith('https://')
    assert 'synthetic' not in url
    assert 'synthetic' not in json.dumps(body)
    if provider == 'Gemini':
        assert body['contents'][0]['parts'][0]['text'] == 'hello'
        assert p.decode({'candidates':[{'content':{'parts':[{'text':'world'}]}}]}) == 'world'
    elif provider == 'Claude':
        assert body['max_tokens'] == 4096
        assert p.decode({'content':[{'type':'text','text':'world'}]}) == 'world'
    else:
        if provider in ('OpenAI', 'xAI'):
            assert body['store'] is False
        assert p.decode({'choices':[{'message':{'content':'world'}}]}) == 'world'


def test_redirect_block():
    with pytest.raises(ValueError):
        NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid')
