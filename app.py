from __future__ import annotations
import argparse, csv, hashlib, ipaddress, json, os, subprocess, sys, tempfile, uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import tomllib

class PipelineError(RuntimeError): pass

@dataclass
class Record:
    ip: str
    port: int
    sent: int | None
    received: int | None
    loss_ratio: float | None
    latency_ms: float | None
    speed_mbps: float | None
    country_code: str | None = None
    city: str | None = None
    raw: dict | None = None

ALIASES = {
 "ip":("ip","ip地址","ip address","address"),
 "sent":("已发送","sent","sent packets"),
 "received":("已接收","received","received packets"),
 "loss":("丢包率","loss","loss rate","packet loss"),
 "latency":("平均延迟","延迟","latency","avg latency","avg latency(ms)"),
 "speed":("下载速度(mb/s)","下载速度","download speed(mb/s)","download speed","speed(mb/s)"),
 "country":("country","country code","国家代码","国家/地区代码"),
 "city":("city","城市")
}

def num(value, field):
    if value is None or not str(value).strip(): return None
    try: n=float(str(value).strip().replace("%",""))
    except ValueError as e: raise PipelineError(f"Invalid {field}: {value!r}") from e
    if n != n or abs(n)==float("inf"): raise PipelineError(f"Non-finite {field}")
    return n

def parse_csv(path: Path, port: int) -> list[Record]:
    if not path.is_file() or not path.stat().st_size: raise PipelineError(f"Missing/empty CFST CSV: {path}")
    content=None
    for enc in ("utf-8-sig","gb18030"):
        try: content=path.read_text(encoding=enc); break
        except UnicodeDecodeError: pass
    if content is None: raise PipelineError("Unsupported CFST CSV encoding")
    try: dialect=csv.Sniffer().sniff(content[:8192],delimiters=",;\\t")
    except csv.Error: dialect=csv.excel
    reader=csv.DictReader(content.splitlines(),dialect=dialect)
    if not reader.fieldnames: raise PipelineError("CFST CSV has no header")
    h={x.strip().lower():x for x in reader.fieldnames}; col={}
    for key, aliases in ALIASES.items():
        for a in aliases:
            if a.lower() in h: col[key]=h[a.lower()]; break
    if "ip" not in col: raise PipelineError(f"IP column not found in CSV: {reader.fieldnames}")
    result=[]
    for line,row in enumerate(reader,2):
        if not row or not any((v or "").strip() for v in row.values()): continue
        try: ip=str(ipaddress.IPv4Address((row.get(col["ip"]) or "").strip()))
        except ipaddress.AddressValueError as e: raise PipelineError(f"Invalid IPv4 on CSV line {line}") from e
        v={k:num(row.get(c),k) for k,c in col.items() if k in ("sent","received","loss","latency","speed")}
        loss=v.get("loss")
        if loss is not None and not 0<=loss<=1: raise PipelineError(f"Loss must be CFST ratio [0,1], line {line}: {loss}")
        sent,recv=v.get("sent"),v.get("received")
        if sent is not None and (sent<0 or int(sent)!=sent): raise PipelineError(f"Invalid sent count line {line}")
        if recv is not None and (recv<0 or int(recv)!=recv): raise PipelineError(f"Invalid received count line {line}")
        if sent is not None and recv is not None and recv>sent: raise PipelineError(f"Received exceeds sent line {line}")
        result.append(Record(ip,port,int(sent) if sent is not None else None,
          int(recv) if recv is not None else None,loss,v.get("latency"),v.get("speed"),
          (row.get(col.get("country","")) or "").strip().upper() or None,
          (row.get(col.get("city","")) or "").strip() or None,{k:(v or "") for k,v in row.items()}))
    if not result: raise PipelineError("CFST CSV contains no records")
    if len({r.ip for r in result}) != len(result): raise PipelineError("Duplicate IPv4 rows in CFST CSV")
    return result

def rank(rows):
    return sorted(rows,key=lambda r:(r.speed_mbps is None,-(r.speed_mbps or 0),
      r.latency_ms is None,r.latency_ms if r.latency_ms is not None else float("inf"),
      r.loss_ratio is None,r.loss_ratio if r.loss_ratio is not None else float("inf"),
      int(ipaddress.IPv4Address(r.ip))))

def atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix="."+path.name+".",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\\n") as f:
            f.write(content); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise

def run_cfst(cfg, args_cfg, run_dir, stage):
    csv_path=run_dir/f"stage{stage}.csv"
    args=[str(x).replace("{input}",str(args_cfg["input_path"])).replace("{csv}",str(csv_path)).replace("{run_dir}",str(run_dir)) for x in args_cfg["args"]]
    env=os.environ.copy()
    for k in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"): env.pop(k,None)
    env["NO_PROXY"]="*"; env["no_proxy"]="*"
    try:
        p=subprocess.run([cfg.get("binary","/usr/local/bin/cfst"),*args],cwd=run_dir,env=env,
          text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
          timeout=int(cfg.get("process_timeout_seconds",1800)),check=False)
    except subprocess.TimeoutExpired as e: raise PipelineError(f"CFST stage {stage} timed out; no publish") from e
    atomic_write(run_dir/f"stage{stage}.log",p.stdout or "")
    if p.returncode: raise PipelineError(f"CFST stage {stage} exited {p.returncode}; no publish")
    if not csv_path.is_file(): raise PipelineError(f"CFST stage {stage} CSV missing")
    return csv_path

def subscription_line(r: Record):
    if r.speed_mbps is None or r.latency_ms is None: raise PipelineError(f"{r.ip}: missing speed/latency")
    if not r.country_code: raise PipelineError(f"{r.ip}: trusted country code absent; do not infer country from CFST Colo")
    label=f"{r.country_code}-{r.speed_mbps:.2f}MB/s-{r.latency_ms:.0f}ms"
    if r.city: label+=f"-{r.city}"
    return f"{r.ip}:{r.port}#{label}"

def main():
    ap=argparse.ArgumentParser(description="Two-pass CFST v2.3.5 orchestration")
    ap.add_argument("--config",default="/config/config.toml"); ap.add_argument("--parse-only",action="store_true")
    ns=ap.parse_args()
    try:
        cfg=tomllib.loads(Path(ns.config).read_text(encoding="utf-8"))
        c=cfg["cfst"]; policy=cfg["selection"]; out=cfg.get("output",{})
        first_n=int(policy.get("first_top_n",80)); second_n=int(policy.get("second_top_n",50))
        max_loss=float(policy.get("max_loss_ratio",0))
        if first_n<1 or second_n<1 or second_n>first_n or max_loss!=0:
            raise PipelineError("Current approved defaults require first_top_n>=second_top_n>=1 and max_loss_ratio=0")
        root=Path(cfg.get("paths",{}).get("work_dir","/work/runs")); root.mkdir(parents=True,exist_ok=True)
        run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
        wd=root/run_id; wd.mkdir(mode=0o700)
        if ns.parse_only: raise PipelineError("Offline parse-only mode is not implemented for two-pass runs yet")
        stage1_cfg=cfg["stage1"]; stage1_cfg["input_path"]=str(Path(c["input_file"]))
        stage1_csv=run_cfst(c,stage1_cfg,wd,1)
        first=parse_csv(stage1_csv,int(c.get("port",443)))
        first_ok=[r for r in first if r.loss_ratio == max_loss and r.speed_mbps is not None and r.latency_ms is not None]
        first_top=rank(first_ok)[:first_n]
        if not first_top: raise PipelineError("No first-pass nodes meet 0% loss and complete speed/latency criteria")
        candidate_file=wd/"stage2_candidates.txt"
        atomic_write(candidate_file,"".join(r.ip+"\\n" for r in first_top))
        stage2_cfg=cfg["stage2"]; stage2_cfg["input_path"]=str(candidate_file)
        stage2_csv=run_cfst(c,stage2_cfg,wd,2)
        second=parse_csv(stage2_csv,int(c.get("port",443)))
        first_ips={r.ip for r in first_top}
        if any(r.ip not in first_ips for r in second): raise PipelineError("Second-pass CSV contains an IP not selected in first pass")
        second_ok=[r for r in second if r.loss_ratio == max_loss and r.speed_mbps is not None and r.latency_ms is not None]
        final=rank(second_ok)[:second_n]
        if not final: raise PipelineError("No second-pass nodes meet 0% loss and complete measurement criteria")
        snap={"schema_version":1,"run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat(),
          "cfst_version":c.get("version","2.3.5"),"policy":{"first_top_n":first_n,"second_top_n":second_n,"max_loss_ratio":max_loss},
          "stage1_csv_sha256":hashlib.sha256(stage1_csv.read_bytes()).hexdigest(),
          "stage2_csv_sha256":hashlib.sha256(stage2_csv.read_bytes()).hexdigest(),
          "stage1_records":[asdict(x) for x in first],"stage1_eligible":[asdict(x) for x in first_top],
          "stage2_records":[asdict(x) for x in second],"final_records":[asdict(x) for x in final]}
        atomic_write(wd/"measurements.json",json.dumps(snap,ensure_ascii=False,indent=2)+"\\n")
        if out.get("enabled",False):
            lines=[subscription_line(x) for x in final]
            atomic_write(Path(out.get("path","/output/nodes.txt")),"\\n".join(lines)+"\\n")
        print(json.dumps({"run_id":run_id,"stage1_records":len(first),"stage1_eligible":len(first_top),
          "stage2_records":len(second),"final_nodes":len(final),"published":bool(out.get("enabled",False)),
          "snapshot":str(wd/"measurements.json")},ensure_ascii=False,indent=2))
        return 0
    except (PipelineError,OSError,KeyError,ValueError,subprocess.SubprocessError) as e:
        print("ERROR:",e,file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
