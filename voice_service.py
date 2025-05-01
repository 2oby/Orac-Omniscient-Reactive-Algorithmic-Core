#!/usr/bin/env python3
"""
Voice Service – Smart‑Home Control (fixed warnings + working dashboard buttons)
"""
# ——— Imports & config remain identical to previous version ———
# (Only the changed / added sections are shown below for clarity.)

# ---------------------------------------------------------------------------
# Pydantic models  (warnings removed)
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = Field(None, description="Model ID or alias")
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(150, gt=0, le=2048)

    class Config:
        protected_namespaces = ()


class QueryResponse(BaseModel):
    command: Optional[Dict[str, Any]] = None
    raw_generation: str = ""
    model_used: str = ""
    error: Optional[str] = None

    class Config:
        protected_namespaces = ()


class ModelInfo(BaseModel):
    model_id: str
    is_loaded: bool
    is_current: bool = False
    model_type: str = ""

    class Config:
        protected_namespaces = ()

# ---------------------------------------------------------------------------
# Root dashboard – fixed JS button handlers
# ---------------------------------------------------------------------------
# inside the HTML response (full HTML rebuilt; only the <script> block differs):

    html += """
    <script>
    async function act(btn,id,action){
        btn.disabled=true;const txt=btn.textContent;btn.textContent=(action==='load'?'Loading…':'Unloading…');
        try{
            const res=await fetch(`/${action}-model?model_id=`+encodeURIComponent(id));
            const data=await res.json();
            flash(res.ok?'success':'error',data.message||data.detail);
            setTimeout(()=>location.reload(),800);
        }catch(e){flash('error',e.message);btn.disabled=false;btn.textContent=txt;}
    }
    function flash(cls,msg){const m=document.getElementById('msg');m.className=cls;m.textContent=msg;m.style.display='block';}
    async function send(){
        const btn=document.getElementById('send');btn.disabled=true;btn.textContent='…';
        try{
            const body={prompt:document.getElementById('prompt').value,temperature:0.7,max_tokens:150};
            const r=await fetch('/smart-home/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
            const d=await r.json();
            document.getElementById('resp').style.display='block';
            document.getElementById('cmd').textContent=d.command?JSON.stringify(d.command,null,2):'';
            document.getElementById('raw').textContent=d.raw_generation||'';
            document.getElementById('err').textContent=d.error||'';
        }catch(e){flash('error',e.message);}finally{btn.disabled=false;btn.textContent='Test';}
    }
    </script></body></html>"""

# ---------------------------------------------------------------------------
# Entrypoint stays the same (module name = voice_service)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting server on http://0.0.0.0:8000 …")
    uvicorn.run(app, host="0.0.0.0", port=8000)
