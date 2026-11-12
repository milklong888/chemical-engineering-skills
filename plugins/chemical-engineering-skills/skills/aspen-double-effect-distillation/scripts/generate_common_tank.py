"""Reproduce only 04-common-tank-boundary-local.svg; Python 3, no dependencies.
Authority: ../references/boundaries.md and material_connections.md.
Original schematic by milklong888, CC BY 4.0. No Aspen validation implied.
"""
from pathlib import Path
from html import escape
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "assets"
OUT = ROOT / '04-common-tank-boundary-local.svg'
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1350" viewBox="0 0 1800 1350">
<title>共同储槽：来源、回流与最终净产品边界</title>
<desc>条件化局部结构候选，未Aspen验证。HP与LP凝液入共同槽，混合后返回HP或成为最终净产品。同一HX热冷两侧仅传热，不交换物料。</desc>
<defs><marker id="f" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#183449"/></marker><marker id="q" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#bb671c"/></marker></defs>
<style>text{font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;font-size:22px;fill:#183449}.sm{font-size:19px}.bold{font-weight:700}.title{font-size:34px;font-weight:700}.heat{fill:#bb671c}</style>
<rect width="1800" height="1350" fill="#f4f7fa"/>
''']

def text(x,y,s,cls='',anchor=None):
    a = f' text-anchor="{anchor}"' if anchor else ''
    parts.append(f'<text x="{x}" y="{y}" class="{cls}"{a}>{escape(s)}</text>')

def box(x,y,w,h,lines,hx=False):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{"#e5f2f7" if hx else "white"}" stroke="{"#176784" if hx else "#9bafbf"}" stroke-width="2"/>')
    start = y+h/2-(len(lines)-1)*16+8
    for n,s in enumerate(lines): text(x+w/2,start+n*32,s,'bold' if n==0 else 'sm','middle')

def arrow(points,label=None,lx=0,ly=0,heat=False):
    d=' '.join(('M' if i==0 else 'L')+f'{x},{y}' for i,(x,y) in enumerate(points))
    dash=' stroke-dasharray="8 7"' if heat else ''
    parts.append(f'<path d="{d}" stroke="{"#bb671c" if heat else "#183449"}" stroke-width="3" fill="none" marker-end="url(#{"q" if heat else "f"})"{dash}/>')
    if label: text(lx,ly,label,'sm heat' if heat else 'sm')

def panel(y,h):
    parts.append(f'<rect x="30" y="{y}" width="1740" height="{h}" rx="16" fill="#edf2f6" stroke="#d3dfe7"/>')

text(48,58,'04  共同储槽：来源、回流与最终净边界','title')
text(48,101,'入槽凝液 C_HP / C_LP 不是全岛最终净产品；R_HP来自槽内混合液，其组成须另核。')
text(48,138,'局部接口 · 条件化结构候选 · 未Aspen验证  |  未证明实际边界流量闭合、设备能力或产品指标','sm')
panel(165,725)

# LP top service and its internal reflux are separate from C_LP sent to tank.
box(650,190,190,85,['LP顶部总汽','V · 去冷凝服务'])
box(920,190,260,85,['LP顶部冷凝服务','冷凝 / 内部回流分配'])
arrow([(840,232),(920,232)],'V',870,215)
box(1430,190,300,85,['LP内部液体回流','L → LP顶部返回'])
arrow([(1180,232),(1430,232)],'L · 内部回流',1210,215)

# Shared hot side and common-tank feed.
box(50,310,230,90,['HP顶部总顶汽','V_HP · V'])
box(400,310,240,90,['HX-DE 热侧','给定条件下凝液 C_HP'],True)
arrow([(280,355),(400,355)],'V',330,338)
box(920,355,260,200,['共同储槽','接收 / 混合 / 必要分相','所选控制体：本槽','非指定Aspen模块名'])
arrow([(640,355),(790,355),(790,390),(920,390)],'C_HP · 入槽液 L',666,333)
arrow([(1050,275),(1050,355)],'C_LP · 入槽液 L',1080,315)

# Optional external material has an explicit boundary origin.
box(650,460,190,78,['可选外供液 E','岛外来源 · L'])
arrow([(840,499),(920,499)])
box(1430,340,300,90,['R_HP · 混合回流 L','→ 所需供压 → HP顶部'])
arrow([(1180,390),(1285,390),(1285,385),(1430,385)])
box(1430,470,300,80,['D_NET · 最终净产品','→ 所选系统外产品边界'])
arrow([(1180,455),(1285,455),(1285,510),(1430,510)])
box(1430,585,300,85,['排气 / 排污边界','若存在：组成、相态另列'])
arrow([(1180,520),(1250,520),(1250,627),(1430,627)],'真实外排，不默认为零',1268,570)

# Cold-side once-through kettle-equilibrium approximation.
box(50,675,230,90,['LP底部总抽液','L_LP · L'])
box(400,675,240,90,['HX-DE 冷侧','L → V+L · 受热'],True)
box(760,675,230,90,['FLASH2-K','釜式平衡分相近似'])
arrow([(280,720),(400,720)],'L',330,704)
arrow([(640,720),(760,720)],'V+L',674,704)
box(1330,700,400,80,['V_LP · V → LP下部汽相返回','核返回压力及真实接收位置'])
box(1330,805,400,65,['B_LP · L → 指定净底产品边界'])
arrow([(990,705),(1130,705),(1130,740),(1330,740)],'V',1170,724)
arrow([(990,746),(1080,746),(1080,837),(1330,837)],'L',1170,820)
arrow([(520,400),(520,675)],heat=True)
text(548,585,'同一 HX-DE：仅传热 Q回收','sm heat')
text(548,620,'不跨壁交换物料；不是两台HX','sm heat')

panel(915,145)
text(52,957,'共同槽总账（同一质量流率基准；仅列结构关系，未填实际流量）','bold')
text(52,1002,'C_HP + C_LP + E = R_HP + D_NET + 排气/排污 + 积累率','bold')
text(52,1037,'稳态才令积累率为零；还须逐组分闭合。入槽液与回流不能重复计作最终净产品。','sm')

panel(1080,210)
text(52,1120,'范围外服务与条件','bold')
text(52,1158,'HP底：指定净产品或跨塔边界；HP再沸：外部供热。LP顶冷凝：外部冷却；原料入口另列。','sm')
text(52,1192,'槽压、凝液降压闪蒸、排气去向、回流液相与供压须核；图中纯液入槽条件不代表降压后必然不闪蒸。','sm')
text(52,1226,'混合回流不能继续当作原HP凝液；须核槽内相平衡/混合组成及对两塔产品与热负荷的影响。','sm')
text(52,1260,'FLASH2仅分相时不另加隐含供热；本图未核面积、持液、槽控、温差、压降、热水力或Aspen端口。','sm')
text(48,1326,'原创：milklong888 · CC BY 4.0  |  依据：连接细化卡 §0 来源与净边界补充、§1；Aspen官方学习指南 p11','sm')

data='\n'.join(parts)+'\n</svg>\n'
ET.fromstring(data)
OUT.write_text(data,encoding='utf-8')
print(OUT.name)
