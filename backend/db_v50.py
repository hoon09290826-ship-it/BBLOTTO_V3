import os, sqlite3
from datetime import datetime
from pathlib import Path
from .security import hash_password
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv('BBLOTTO_DB', BASE_DIR / 'database' / 'bblotto_v50.db'))
LOTTO_SEED = [
    (1221,[12,15,17,24,29,45],16),(1222,[3,6,21,30,34,35],22),(1223,[5,9,12,20,21,26],7),
    (1224,[4,8,16,21,27,39],14),(1225,[11,13,22,27,35,40],2),(1226,[7,12,18,23,32,44],19),
    (1227,[2,10,14,26,33,41],6),(1228,[1,5,17,29,34,42],8),(1229,[6,13,19,24,31,45],11),
    (1230,[3,11,15,23,36,44],9)
]
def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c
def init_db():
    with conn() as c:
        c.execute('CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT "admin", created_at TEXT NOT NULL, last_login TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, grade TEXT DEFAULT "VIP", memo TEXT DEFAULT "", created_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS draws(round INTEGER PRIMARY KEY, n1 INTEGER,n2 INTEGER,n3 INTEGER,n4 INTEGER,n5 INTEGER,n6 INTEGER, bonus INTEGER, source TEXT DEFAULT "manual", updated_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS recommendations(id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, round INTEGER NOT NULL, numbers TEXT NOT NULL, score INTEGER NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS admin_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, action TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL)')
        if c.execute('select count(*) from admins').fetchone()[0] == 0:
            c.execute('insert into admins(username,password_hash,name,role,created_at) values(?,?,?,?,?)',('admin', hash_password('admin1234'), 'BBLOTTO 관리자', 'superadmin', now()))
        if c.execute('select count(*) from members').fetchone()[0] == 0:
            c.executemany('insert into members(name,phone,grade,memo,created_at) values(?,?,?,?,?)', [('VIP 테스트회원','010-0000-0001','VIP','초기 테스트 회원',now()),('프리미엄 테스트회원','010-0000-0002','PREMIUM','초기 테스트 회원',now())])
        for r, nums, bonus in LOTTO_SEED:
            c.execute('insert or ignore into draws(round,n1,n2,n3,n4,n5,n6,bonus,source,updated_at) values(?,?,?,?,?,?,?,?,?,?)',(r,*nums,bonus,'seed',now()))
def log(admin_id, action, detail=''):
    with conn() as c: c.execute('insert into admin_logs(admin_id,action,detail,created_at) values(?,?,?,?)',(admin_id,action,detail,now()))
def rowdict(row): return dict(row) if row else None
def rows(sql, args=()):
    with conn() as c: return [dict(r) for r in c.execute(sql,args).fetchall()]
def one(sql,args=()):
    with conn() as c: return rowdict(c.execute(sql,args).fetchone())
def execute(sql,args=()):
    with conn() as c:
        cur=c.execute(sql,args)
        return cur.lastrowid
