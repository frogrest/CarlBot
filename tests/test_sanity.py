from services.agent.core import Agent
from services.agent.knowledge import KnowledgeBase


def test_auto_policy():
    a = Agent('http://x', 'http://y')
    assert a.allowed_auto_action('reconnect-rtsp')
    assert a.allowed_auto_action('restart-ai-service')
    assert not a.allowed_auto_action('change-network-config')
    a.close()


def test_knowledge_search(tmp_path):
    (tmp_path / 'rtsp.md').write_text('# RTSP\nRTSP authentication failures require credential verification.', encoding='utf-8')
    kb = KnowledgeBase(str(tmp_path))
    result = kb.search('RTSP authentication')
    assert result
    assert result[0]['path'] == 'rtsp.md'
