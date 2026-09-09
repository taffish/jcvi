"""仅收窄 JCVI 默认本体资源 I/O：缺本地 GO/SO 时拒绝隐式网络请求。"""
from pathlib import Path
import sysconfig

path=Path(sysconfig.get_paths()['purelib'])/'jcvi/formats/obo.py'
source=path.read_text()
old='    from jcvi.apps.base import download\n\n    so_file = download(obo_url, debug=False)'
new='''    # TAFFISH packaging I/O guard: prepare an explicit verified local OBO first.
    # No ontology terms, parsing or analysis algorithms are changed.
    from pathlib import Path
    from urllib.parse import urlsplit

    so_file = Path(urlsplit(obo_url).path).name
    if not so_file or not Path(so_file).is_file():
        raise FileNotFoundError(
            "JCVI ontology missing: prepare a verified local " + so_file
            + " in the work directory; use jcvi-resources for an explicit fixed OBO member. "
            + "Implicit ontology downloading is disabled."
        )'''
assert source.count(old)==1,'unexpected upstream ontology source; refuse blind patch'
path.write_text(source.replace(old,new))
print('JCVI local ontology guard applied; parsing/analysis unchanged')
