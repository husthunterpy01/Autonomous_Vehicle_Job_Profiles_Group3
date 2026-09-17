"""Isolated fixture: DATABASE_URL=sqlite:// python -m scripts.be9_snapshot."""
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.routers.job import router
from app.services.silver_sync import SilverSync

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

Base.metadata.create_all(engine)

with Session(engine) as db, db.begin():

    SilverSync(db).run([{

        "deduplication_key": "f97c5d29941bfb1b2fdab0874906ab82",

        "company_name": "Demo AV Company", "job_name": "Autonomy Engineer",

        "job_description": "Synthetic fixture: build perception and controls software.",

        "locations": ["Perth", "Remote"], "ats_name": "greenhouse", "source_job_id": "42",

        "functional_area": ["Perception", "Controls"],

        "skills": [{"name": "Python", "skill_type": "programming_language"}],

    }])



app = FastAPI(title="BE9 isolated API snapshot")

app.include_router(router, prefix="/api/v1")





def demo_db():

    with Session(engine) as db:

        yield db





app.dependency_overrides[get_db] = demo_db





@app.get("/", response_class=HTMLResponse)

def snapshot():

    return HTMLResponse("""<!doctype html><html><head><title>BE9 API snapshot</title>

<style>body{font:16px system-ui;margin:10px auto;max-width:1180px;color:#16324a;background:#f3f6fa}h1{margin:8px 0;font-size:24px}p{color:#496177;margin:8px 0;font-size:14px}section{background:white;padding:12px;border:1px solid #d8e3ed;border-radius:12px;margin-top:12px}pre{font:12px/1.2 Consolas,monospace;white-space:pre-wrap;margin:0}#status{font-weight:700;color:#147550}small{color:#496177}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}h2{font-size:18px;margin:0 0 12px}</style></head>

<body><small>PR #87 / BE9 / Backend integration evidence</small><h1>Job API: normalized categories and stable identity</h1>

<p>Isolated SQLite database · synthetic fixture · live responses from the actual job router and service</p>

<section><b>GET /api/v1/jobs?q=Autonomy&amp;location=Remote</b><p id="status">Loading...</p></section>

<div class="grid"><section><h2>Job list response (selected fields)</h2><pre id="response"></pre></section>

<section><h2>Category filter verification</h2><pre id="filtered"></pre><h2 style="margin-top:12px">Identity contract</h2><pre>Silver deduplication_key: MD5 text

f97c5d29941bfb1b2fdab0874906ab82



Backend job_id: generated UUID



bronze_id: provenance only



Categories: many-to-many foreign keys

Taxonomy version: 1

Main type: null (not inferred)</pre></section></div>

<script>(async()=>{try{const r=await fetch('/api/v1/jobs?q=Autonomy&location=Remote');const data=await r.json();document.getElementById('status').textContent='HTTP '+r.status+' · '+data.total+' matching job · '+data.items[0].categories.length+' categories';document.getElementById('response').textContent=JSON.stringify({total:data.total,page:data.page,job_id:data.items[0].job_id,title:data.items[0].title,locations:data.items[0].locations,skills:data.items[0].skills,categories:data.items[0].categories},null,2);const c=data.items[0].categories[0];const f=await fetch('/api/v1/jobs?category_id='+c.category_id);const result=await f.json();document.getElementById('filtered').textContent=JSON.stringify({http_status:f.status,category:c.sub_type,category_id:c.category_id,total:result.total,job_id:result.items[0].job_id},null,2)}catch(e){document.getElementById('status').textContent=String(e)}})()</script></body></html>""")





if __name__ == "__main__":

    uvicorn.run(app, host="127.0.0.1", port=8879)

