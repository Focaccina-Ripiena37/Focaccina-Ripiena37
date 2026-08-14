from __future__ import annotations

import base64
import json
import os
import random
import urllib.request
from html import escape
from pathlib import Path

USERNAME = os.environ.get('GH_USERNAME', 'Focaccina-Ripiena37')
TOKEN = os.environ.get('GH_TOKEN', '')
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)

BG='#0d1117'; PANEL='#161b22'; BORDER='#30363d'; TEXT='#f0f6fc'; MUTED='#8b949e'; MINT='#3fbf9b'; MINT_TEXT='#7ee2c2'; BLUE='#9cc7ff'

LANG_COLORS = {
    'TypeScript':'#3178c6','JavaScript':'#f1e05a','Python':'#FFD43B','Dart':'#00B4AB',
    'Java':'#b07219','Processing':'#ED225D','HTML':'#e34c26','CSS':'#a371f7',
    'Ruby':'#701516','C++':'#f34b7d','C':'#555555','Go':'#00ADD8','Rust':'#dea584',
}

def request_json(url, data=None):
    headers={'Accept':'application/vnd.github+json','User-Agent':'profile-readme-generator','X-GitHub-Api-Version':'2022-11-28'}
    if TOKEN: headers['Authorization']=f'Bearer {TOKEN}'
    body=None
    if data is not None:
        body=json.dumps(data).encode('utf-8'); headers['Content-Type']='application/json'
    req=urllib.request.Request(url,data=body,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as res: return json.load(res)

def fetch_avatar_data_uri(url):
    req=urllib.request.Request(url,headers={'User-Agent':'profile-readme-generator'})
    with urllib.request.urlopen(req,timeout=30) as res:
        ctype=res.headers.get('Content-Type','image/jpeg'); raw=res.read()
    return f'data:{ctype};base64,{base64.b64encode(raw).decode("ascii")}'

def get_repos():
    repos=[]
    for page in range(1,5):
        batch=request_json(f'https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&sort=updated')
        if not isinstance(batch,list) or not batch: break
        repos.extend(batch)
        if len(batch)<100: break
    return [r for r in repos if not r.get('fork') and r.get('name','').lower()!=USERNAME.lower()]

def get_calendar():
    query='''query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''
    result=request_json('https://api.github.com/graphql',{'query':query,'variables':{'login':USERNAME}})
    try: return result['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    except Exception: return []

def save(name,content): (ASSETS/name).write_text(content,encoding='utf-8')
def trim(value,n):
    s=(value or '').strip(); return s if len(s)<=n else s[:n-1].rstrip()+'…'
def char_avg(size,weight):
    return size*(0.60 if weight>=700 else 0.52)
def trim_px(value,max_width,size=12,weight=400):
    '''Truncate to a pixel-width budget (Arial heuristic) rather than a raw char count, so it never overruns a fixed-width card.'''
    s=(value or '').strip()
    if not s: return s
    max_chars=max(1,int(max_width/char_avg(size,weight)))
    return s if len(s)<=max_chars else s[:max(1,max_chars-1)].rstrip()+'…'
def wrap_px(value,max_width,size=12,weight=400,max_lines=2):
    max_chars=max(1,int(max_width/char_avg(size,weight)))
    words=(value or '').strip().split()
    lines=[]; cur=''
    for w in words:
        cand=(cur+' '+w).strip()
        if len(cand)<=max_chars: cur=cand
        else:
            if cur: lines.append(cur)
            cur=w
        if len(lines)==max_lines: break
    consumed=len(' '.join(lines).split())
    if cur and len(lines)<max_lines: lines.append(cur); consumed=len((' '.join(lines)).split())
    if not lines: lines=['']
    if consumed<len(words):
        last=lines[-1][:max_chars-1].rstrip()+'…'
        lines[-1]=last
    return lines
def txt(x,y,value,size=14,color=TEXT,weight=400,anchor='start'):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'

DEFS=f'''<linearGradient id="glass" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#ffffff" stop-opacity="0.16"/>
<stop offset="0.5" stop-color="#ffffff" stop-opacity="0.03"/>
<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
</linearGradient>
<linearGradient id="starTail" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#ffffff" stop-opacity="0"/>
<stop offset="0.75" stop-color="#bfe9da" stop-opacity="0.5"/>
<stop offset="1" stop-color="#ffffff" stop-opacity="1"/>
</linearGradient>
<filter id="cardShadow" x="-30%" y="-30%" width="160%" height="160%">
<feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#000000" flood-opacity="0.4"/>
</filter>'''

def shell(height,inner,space=False,seed=1):
    bg=starfield(1000,height,seed=seed) if space else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}"><defs>{DEFS}</defs><rect width="1000" height="{height}" rx="18" fill="{BG}"/><clipPath id="canvasClip"><rect width="1000" height="{height}" rx="18"/></clipPath><g clip-path="url(#canvasClip)">{bg}</g><rect x="1" y="1" width="998" height="{height-2}" rx="17" fill="none" stroke="{BORDER}"/>{inner}</svg>'

def panel(w,h,rx=12,fill=PANEL,stroke=BORDER,fill_opacity=1):
    '''Glossy/plastic card: base fill + drop shadow, then a glass highlight sheen on top. fill_opacity<1 lets a starfield behind the card show through, like a ship's window.'''
    return (f'<rect width="{w}" height="{h}" rx="{rx}" fill="{fill}" fill-opacity="{fill_opacity}" stroke="{stroke}" filter="url(#cardShadow)"/>'
            f'<rect width="{w}" height="{h}" rx="{rx}" fill="url(#glass)" pointer-events="none"/>')

def fade_in(delay=0.0, dur=0.5, dy=10):
    return (f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 {dy}" to="0 0" begin="{delay:.2f}s" dur="{dur}s" fill="freeze" additive="sum"/>')

def pop_in(delay=0.0, dur=0.45):
    return (f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="scale" from="0.85 0.85" to="1 1" begin="{delay:.2f}s" dur="{dur}s" fill="freeze" additive="sum"/>')

def group(x,y,inner,anim=''):
    return f'<g transform="translate({x},{y})" opacity="0">{anim}{inner}</g>'

def shooting_star(y,delay,dur=3.0,length=70,dy=55):
    path=f'M -100,{y} L 1100,{y+dy}'
    return (f'<rect width="{length}" height="2" rx="1" fill="url(#starTail)" opacity="0">'
            f'<animateMotion path="{path}" begin="{delay:.2f}s" dur="{dur}s" repeatCount="indefinite" rotate="auto"/>'
            f'<animate attributeName="opacity" values="0;0;0.9;0.9;0" keyTimes="0;0.05;0.15;0.85;1" begin="{delay:.2f}s" dur="{dur}s" repeatCount="indefinite"/>'
            f'</rect>')

def twinkle(x,y,delay,dur=2.2,r=1.4):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="#ffffff" opacity="0.15"><animate attributeName="opacity" values="0.15;0.9;0.15" dur="{dur}s" begin="{delay:.2f}s" repeatCount="indefinite"/></circle>'

def starfield(width,height,seed=1,dots=42,streaks=5):
    '''Deep-space backdrop behind a whole section: distant twinkling dust plus slow parallax streaks moving the same direction as the header comets, as if seen out a ship's window. Fixed seed keeps daily regenerations diff-quiet.'''
    rnd=random.Random(seed)
    out=''
    for _ in range(dots):
        x=rnd.uniform(16,width-16); y=rnd.uniform(50,height-14); r=rnd.choice([0.5,0.7,0.9,0.9,1.1])
        dur=rnd.uniform(1.8,3.8); delay=rnd.uniform(0,3.5); peak=rnd.uniform(0.3,0.6)
        out+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#ffffff" opacity="0.04"><animate attributeName="opacity" values="0.04;{peak:.2f};0.04" dur="{dur:.2f}s" begin="{delay:.2f}s" repeatCount="indefinite"/></circle>'
    for _ in range(streaks):
        y=rnd.uniform(50,height-14); dy=rnd.uniform(-14,14); length=rnd.uniform(36,80)
        dur=rnd.uniform(8,15); delay=rnd.uniform(0,6)
        path=f'M -80,{y:.1f} L {width+80},{y+dy:.1f}'
        out+=(f'<rect width="{length:.0f}" height="1.3" rx="0.6" fill="url(#starTail)" opacity="0">'
              f'<animateMotion path="{path}" begin="{delay:.2f}s" dur="{dur:.2f}s" repeatCount="indefinite" rotate="auto"/>'
              f'<animate attributeName="opacity" values="0;0;0.4;0.4;0" keyTimes="0;0.05;0.15;0.85;1" begin="{delay:.2f}s" dur="{dur:.2f}s" repeatCount="indefinite"/></rect>')
    return out

profile=request_json(f'https://api.github.com/users/{USERNAME}')
repos=get_repos(); calendar=get_calendar()
bio=trim(profile.get('bio') or 'Full-stack engineer focused on polished web products and developer experience.',100)
name=profile.get('name') or USERNAME
location=profile.get('location') or 'Remote / Europe'
company=(profile.get('company') or '').strip()
followers=profile.get('followers',0); public_repos=profile.get('public_repos',len(repos)); total_stars=sum(int(r.get('stargazers_count',0)) for r in repos)
try: avatar_uri=fetch_avatar_data_uri(profile['avatar_url']+'&s=200') if profile.get('avatar_url') else ''
except Exception: avatar_uri=''

# ---------- hero ----------
hero=f'''<defs>{DEFS}<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{BG}"><animate attributeName="stop-color" values="{BG};#0f2620;{BG}" dur="8s" repeatCount="indefinite"/></stop>
<stop offset="1" stop-color="#111a22"><animate attributeName="stop-color" values="#111a22;#0f2b26;#111a22" dur="8s" repeatCount="indefinite"/></stop>
</linearGradient><clipPath id="avatarClip"><circle r="42"/></clipPath></defs><rect width="1000" height="250" rx="22" fill="url(#g)"/><rect x="1" y="1" width="998" height="248" rx="21" fill="none" stroke="{BORDER}"/>'''
stars=[(18,0.0),(34,1.4),(12,2.6),(44,0.7),(26,3.6)]
hero+=''.join(shooting_star(y,d) for y,d in stars)
twinkles=[(600,20,0.2),(690,38,1.1),(760,16,0.6),(840,32,1.8),(900,22,0.4),(940,44,1.5)]
hero+=''.join(twinkle(x,y,d) for x,y,d in twinkles)
if avatar_uri:
    avatar_inner=(f'<circle r="43" fill="{PANEL}" filter="url(#cardShadow)"/>'
                  f'<image x="-42" y="-42" width="84" height="84" href="{avatar_uri}" clip-path="url(#avatarClip)"/>'
                  f'<circle r="42" fill="none" stroke="{MINT}" stroke-width="2"/>')
else:
    avatar_inner=f'<circle r="42" fill="{PANEL}" stroke="{MINT}" stroke-width="2" filter="url(#cardShadow)"/>{txt(0,8,"FR37",22,TEXT,700,"middle")}'
hero+=group(78,91,avatar_inner,pop_in(0))
hero+=(f'<circle cx="149" cy="53" r="4" fill="{MINT}"><animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/></circle>'
       + group(160,58,txt(0,0,'LIVE PROFILE',13,MINT,700),fade_in(0.05,0.4,4)))
hero+=group(145,99,txt(0,0,name,34,TEXT,700),fade_in(0.15))
hero+=group(145,132,txt(0,0,bio,15,MUTED),fade_in(0.3))
hero+=f'<line x1="34" y1="176" x2="966" y2="176" stroke="{BORDER}"/>'
badges=[('FULL-STACK',MINT_TEXT,'#0f2b26','#1f6f5f'),('GITHUB NATIVE',BLUE,'#111d2d','#2f5f8f')]
if company: badges.append((company.upper(),'#e3b8ff','#241a33','#5f3f8f'))
bx=34
for i,(label,fg,bgc,stroke) in enumerate(badges):
    w=max(120,28+len(label)*8)
    inner=panel(w,32,16,bgc,stroke)+txt(w/2,21,label,13,fg,700,'middle')
    hero+=group(bx,195,inner,pop_in(0.45+i*0.1))
    bx+=w+12
save('hero.svg',f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="250" viewBox="0 0 1000 250">{hero}</svg>')

# ---------- about ----------
facts=[f'📍 {location}']
if company: facts.append(f'🎓 {company}')
facts.append(f'📦 {public_repos} public repos')
inner=group(34,42,txt(0,0,'ABOUT ME',14,MINT,700),fade_in(0))
inner+=group(34,85,txt(0,0,'Full-Stack Engineer',21,TEXT,700),fade_in(0.1))
inner+=group(34,118,txt(0,0,bio,15,MUTED),fade_in(0.2))
fx=34
for i,f in enumerate(facts):
    w=40+len(f)*7.2
    row=panel(w,28,14)+txt(w/2,18,f,12,MUTED,700,'middle')
    inner+=group(fx,148,row,fade_in(0.3+i*0.08,0.4,6))
    fx+=w+10
save('about.svg',shell(200,inner))

# ---------- skills (pills + language-mix bar chart) ----------
counts={}
for r in repos:
    lang=r.get('language')
    if lang: counts[lang]=counts.get(lang,0)+1
langs=sorted(counts,key=lambda k:(-counts[k],k))[:6] or ['TypeScript','JavaScript','Python']
inner=group(34,42,txt(0,0,'SKILLS',14,MINT,700),fade_in(0))
x=34
for i,lang in enumerate(langs):
    w=max(92,24+len(lang)*8); color=LANG_COLORS.get(lang,MINT)
    pill=(panel(w,36,18,'#0f2b26','#1f6f5f')
          + f'<circle cx="18" cy="18" r="5" fill="{color}"/>'
          + txt(w/2+6,23,lang,13,MINT_TEXT,700,'middle'))
    inner+=group(x,70,pill,pop_in(0.15+i*0.08))
    x+=w+12
total_repos=sum(counts.values()) or 1
inner+=group(34,132,txt(0,0,'LANGUAGE MIX',12,MINT,700),fade_in(0.15+len(langs)*0.08))
bar_w=932; bar_h=16; bx=0; bar_delay=0.25+len(langs)*0.08
bar='<g transform="translate(34,142)">'+panel(bar_w,bar_h,8)
legend=''
for i,lang in enumerate(langs):
    share=counts[lang]/total_repos; seg_w=round(bar_w*share); color=LANG_COLORS.get(lang,MINT)
    delay=bar_delay+i*0.08
    bar+=(f'<rect x="{bx}" width="0" height="{bar_h}" rx="0" fill="{color}">'
          f'<animate attributeName="width" values="0;{seg_w};{seg_w};0;0" keyTimes="0;0.12;0.82;0.92;1" begin="{delay:.2f}s" dur="7s" repeatCount="indefinite"/></rect>')
    legend+=f'<circle cx="{6}" cy="{-3}" r="4" fill="{color}"/>'+txt(14,0,f'{lang} {round(share*100)}%',11,MUTED,700)
    bx+=seg_w
bar+=f'<rect width="{bar_w}" height="{bar_h}" rx="8" fill="url(#glass)" pointer-events="none"/></g>'
inner+=bar
lx=34
for i,lang in enumerate(langs):
    share=counts[lang]/total_repos; label=f'{lang} {round(share*100)}%'; w=18+len(label)*6.6
    row=f'<circle cx="6" cy="0" r="4" fill="{LANG_COLORS.get(lang,MINT)}"/>'+txt(14,4,label,11,MUTED,700)
    inner+=group(lx,176,row,fade_in(0.6+i*0.06,0.3,4))
    lx+=w+14
inner+=group(34,206,txt(0,0,'Detected from your public, non-fork repositories.',12,MUTED),fade_in(0.9,0.3,4))
save('skills.svg',shell(230,inner))

# ---------- stats (3 cards + weekly activity bar chart) ----------
inner=group(34,42,txt(0,0,'GITHUB STATS',14,MINT,700),fade_in(0))
for i,(x,value,label) in enumerate([(34,public_repos,'PUBLIC REPOS'),(357,total_stars,'TOTAL STARS'),(680,followers,'FOLLOWERS')]):
    card=(panel(286,82,12,fill_opacity=0.86)
          + txt(143,36,value,25,TEXT,700,'middle')
          + txt(143,60,label,12,MUTED,700,'middle')
          + f'<rect x="1" y="80" width="0" height="2" rx="1" fill="{MINT}"><animate attributeName="width" from="0" to="284" begin="{0.35+i*0.1:.2f}s" dur="0.6s" fill="freeze"/></rect>')
    inner+=group(x,66,card,pop_in(0.1+i*0.1))
weekly=[sum(int(d.get('contributionCount',0)) for d in w.get('contributionDays',[])) for w in calendar[-14:]] if calendar else []
inner+=group(34,172,txt(0,0,'WEEKLY ACTIVITY',12,MINT,700),fade_in(0.5))
inner+=group(760,172,txt(0,0,'LAST 14 WEEKS',11,MUTED,700,'end'),fade_in(0.5))
if weekly:
    n=len(weekly); gap=6; bar_w=(932-gap*(n-1))/n; max_v=max(weekly) or 1; base_y=232; chart_h=48
    chart='<g transform="translate(34,0)">'
    for i,v in enumerate(weekly):
        h=round((v/max_v)*chart_h) if max_v else 0; x=i*(bar_w+gap); y=base_y-h
        is_last=i==n-1
        pulse='<animate attributeName="opacity" values="1;0.55;1" dur="1.6s" repeatCount="indefinite"/>' if is_last else ''
        chart+=(f'<rect x="{x:.1f}" y="{base_y}" width="{bar_w:.1f}" height="0" rx="2" fill="{MINT if is_last else "#1f6f5f"}">'
                f'<animate attributeName="height" from="0" to="{h}" begin="{0.7+i*0.03:.2f}s" dur="0.5s" fill="freeze"/>'
                f'<animate attributeName="y" from="{base_y}" to="{y}" begin="{0.7+i*0.03:.2f}s" dur="0.5s" fill="freeze"/>'
                f'{pulse}</rect>')
    chart+='</g>'
    inner+=chart
else:
    inner+=group(34,206,txt(0,0,'No public contribution data available.',12,MUTED),fade_in(0.6))
save('stats.svg',shell(250,inner,space=True,seed=7))

# ---------- projects ----------
ranked=sorted(repos,key=lambda r:(int(r.get('stargazers_count',0)),r.get('pushed_at') or ''),reverse=True)[:6]
cols,rows=3,2 if len(ranked)>3 else 1
card_w,card_h,gap=306,132,20
inner=group(34,42,txt(0,0,'PROJECTS',14,MINT,700),fade_in(0))
for i,r in enumerate(ranked):
    col,row=i%cols,i//cols
    x=34+col*(card_w+gap); y=66+row*(card_h+gap)
    inner_w=card_w-40
    title=trim_px(r.get('name') or f'Project #{i+1}',inner_w,17,700)
    desc_lines=wrap_px(r.get('description') or 'No description yet.',inner_w,12,400,max_lines=2)
    lang=r.get('language') or 'Code'; stars=int(r.get('stargazers_count',0)); color=LANG_COLORS.get(lang,MINT)
    card=(panel(card_w,card_h,12,fill_opacity=0.86)
          + txt(20,33,title,17,TEXT,700)
          + ''.join(txt(20,55+li*17,line,12,MUTED) for li,line in enumerate(desc_lines))
          + f'<circle cx="26" cy="98" r="5" fill="{color}"/>'
          + txt(38,102,lang,12,BLUE,700)
          + txt(card_w-20,102,f'★ {stars}',12,MUTED,700,'end'))
    inner+=group(x,y,card,fade_in(0.15+i*0.08,0.45,10))
height=66+rows*(card_h+gap)+8
save('projects.svg',shell(height,inner,space=True,seed=13))

# ---------- heatmap ----------
inner=group(34,42,txt(0,0,'HEATMAP',14,MINT,700),fade_in(0))
weeks=calendar[-53:] if calendar else []
cell=11; gap=3; start_x=90; start_y=62
palette=['#161b22','#0e4429','#006d32','#26a641','#39d353']
max_count=max([d.get('contributionCount',0) for w in weeks for d in w.get('contributionDays',[])],default=1)
cells=''
for wi,week in enumerate(weeks):
    for di,day in enumerate(week.get('contributionDays',[])):
        c=int(day.get('contributionCount',0))
        level=0 if c==0 else 1 if c<=max(1,max_count*.25) else 2 if c<=max(1,max_count*.5) else 3 if c<=max(1,max_count*.75) else 4
        x=start_x+wi*(cell+gap); y=start_y+di*(cell+gap)
        delay=0.15+wi*0.012
        cells+=f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{palette[level]}" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.3s" fill="freeze"/></rect>'
inner+=cells
inner+=group(90,190,txt(0,0,'Less',11,MUTED),fade_in(0.9,0.3,4))
legend=''.join(f'<rect x="{i*17}" y="0" width="11" height="11" rx="2" fill="{c}"/>' for i,c in enumerate(palette))
inner+=group(124,180,legend,fade_in(0.95,0.3,4))
inner+=group(214,190,txt(0,0,'More',11,MUTED),fade_in(1.0,0.3,4))
save('heatmap.svg',shell(215,inner))

# ---------- connect ----------
inner=group(34,42,txt(0,0,'CONNECT',14,MINT,700),fade_in(0))
inner+=group(34,84,txt(0,0,'Let’s build something useful together.',19,TEXT,700),fade_in(0.1))
inner+=group(34,118,txt(0,0,f'GitHub: github.com/{USERNAME}  ·  {location}',14,MUTED),fade_in(0.2))
button=(f'<rect width="220" height="40" rx="20" fill="#0f2b26" stroke="{MINT}" stroke-width="1.5" filter="url(#cardShadow)">'
        f'<animate attributeName="stroke-opacity" values="1;0.4;1" dur="2.2s" repeatCount="indefinite"/></rect>'
        f'<rect width="220" height="40" rx="20" fill="url(#glass)" pointer-events="none"/>'
        + txt(110,26,'★ Follow on GitHub',13,MINT_TEXT,700,'middle'))
inner+=group(34,140,button,fade_in(0.3))
save('connect.svg',shell(200,inner))

print(f'Updated profile assets for {USERNAME}: {len(repos)} repos, {total_stars} stars, {len(ranked)} featured, avatar={"yes" if avatar_uri else "no"}')
