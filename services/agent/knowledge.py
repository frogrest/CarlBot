from pathlib import Path
import re

STOPWORDS = {
    'the','and','for','with','that','this','from','into','when','then','have','has','are','was','were','your','you','our','their','not','can','but','use','used','using','what','how','why','where','which','will','should','must','may','all','any','a','an','to','of','in','on','at','is','it','as','or','by','be','if','we','do','does'
}

class KnowledgeBase:
    def __init__(self, root: str):
        self.root = Path(root)

    def _tokens(self, text: str):
        return {t for t in re.findall(r'[a-z0-9_-]{3,}', text.lower()) if t not in STOPWORDS}

    def search(self, query: str, limit: int = 3):
        q = self._tokens(query)
        results = []
        for path in self.root.rglob('*.md'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            tokens = self._tokens(text)
            score = len(q & tokens)
            if score:
                results.append({'path': str(path.relative_to(self.root)), 'score': score, 'excerpt': text[:700]})
        results.sort(key=lambda x: (-x['score'], x['path']))
        return results[:limit]
