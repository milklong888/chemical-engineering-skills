"""Reproduce three original SVG diagrams; run with Python 3, no dependencies.

Output stays in the sibling assets directory. These are local interface candidates,
not Aspen exports, complete islands, equipment drawings, or validated designs.
Authority: ../references/material_connections.md and heat_services.md
Original graphics: milklong888, CC BY 4.0; cited sources retain their licenses.
"""
from pathlib import Path
from html import escape
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "assets"
W, H = 1600, 1040
INK, BLUE, ORANGE = '#183449', '#176784', '#bb671c'

class Diagram:
    def __init__(self, title, subtitle):
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<title>{escape(title)}</title><desc>{escape(subtitle)}。结构候选，未Aspen验证，局部接口图。</desc>
<defs><marker id="flow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{INK}"/></marker><marker id="heat" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{ORANGE}"/></marker></defs>
<rect width="1600" height="1040" fill="#f4f7fa"/>
<style>text {{font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;fill:{INK};font-size:21px}} .small {{font-size:18px}} .title {{font-size:32px;font-weight:700}} .bold {{font-weight:700}} .blue {{fill:{BLUE}}} .heat {{fill:{ORANGE}}}</style>''']
        self.text(48, 55, title, 'title')
        self.text(48, 96, subtitle)
        self.text(48, 132, '局部接口示意  |  结构候选 · 未Aspen验证  |  非完整塔岛 / 非设备施工图', 'small')

    def text(self, x, y, s, cls='', anchor=None):
        a = f' text-anchor="{anchor}"' if anchor else ''
        self.parts.append(f'<text x="{x}" y="{y}" class="{cls}"{a}>{escape(s)}</text>')

    def box(self, x, y, w, h, lines, kind='normal'):
        fill = '#e5f2f7' if kind == 'hx' else '#ffffff'
        stroke = BLUE if kind == 'hx' else '#9bafbf'
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        start = y + h / 2 - (len(lines) - 1) * 15 + 7
        for n, line in enumerate(lines):
            self.text(x+w/2, start+n*30, line, 'bold' if n == 0 else 'small', 'middle')

    def arrow(self, pts, label=None, lx=None, ly=None, heat=False):
        d = ' '.join(('M' if n == 0 else 'L') + f'{x},{y}' for n,(x,y) in enumerate(pts))
        st = f'stroke="{ORANGE if heat else INK}" stroke-width="3" fill="none" marker-end="url(#{"heat" if heat else "flow"})"'
        if heat: st += ' stroke-dasharray="7 6"'
        self.parts.append(f'<path d="{d}" {st}/>')
        if label: self.text(lx, ly, label, 'small heat' if heat else 'small')

    def panel(self, y, h, title):
        self.parts.append(f'<rect x="32" y="{y}" width="1536" height="{h}" rx="16" fill="#edf2f6" stroke="#d3dfe7"/>')
        self.text(50, y+36, title, 'bold blue')

    def footer(self, lines, source):
        self.panel(775, 207, '边界与未核事项')
        for n, s in enumerate(lines): self.text(52, 847+n*32, s, 'small')
        self.text(48, 1012, '原创图：milklong888 · CC BY 4.0  |  原理来源：'+source, 'small')

    def save(self, name):
        data = '\n'.join(self.parts) + '\n</svg>\n'
        ET.fromstring(data)
        (ROOT/name).write_text(data, encoding='utf-8')

def once_through():
    d = Diagram('01  一次通过：外置釜式平衡近似', 'HP总顶汽冷凝供热；LP总底抽液受热后平衡分相，汽返塔、液净采出。')
    d.panel(166, 580, '同一 HX-DE 的热、冷两侧；图中的两个蓝框不是两台设备')
    d.box(55, 258, 205, 92, ['HP 顶部抽出', 'V_HP · 总顶汽 V'])
    d.box(370, 258, 220, 92, ['HX-DE 热侧', 'V → L · 全冷凝条件'])
    d.box(700, 258, 190, 92, ['FSPLIT-R', '液体非选择性分配'])
    d.box(1130, 212, 360, 88, ['R_HP · 液体回流 L', '→ 所需供压 → HP顶部液体返回'])
    d.box(1130, 340, 360, 80, ['D_HP · 净顶产品 L', '→ 指定产品边界'])
    d.arrow([(260,304),(370,304)],'V',305,288)
    d.arrow([(590,304),(700,304)],'L',635,288)
    d.arrow([(890,290),(1000,290),(1000,256),(1130,256)],'L',1035,240)
    d.arrow([(890,324),(960,324),(960,380),(1130,380)],'L',1035,364)
    d.box(55, 534, 205, 92, ['LP 底部总抽液', 'L_LP · 液体 L'])
    d.box(370, 534, 220, 92, ['HX-DE 冷侧', 'L → V+L · 受热'])
    d.box(700, 534, 190, 92, ['FLASH2-K', '外置釜平衡分相近似'])
    d.box(1130, 490, 360, 88, ['V_LP · 返汽 V', '→ LP下部汽相返回位置'])
    d.box(1130, 630, 360, 80, ['B_LP · 净底产品 L', '→ 指定产品边界；本例仅此一处'])
    d.arrow([(260,580),(370,580)],'L',305,564)
    d.arrow([(590,580),(700,580)],'V+L',620,564)
    d.arrow([(890,563),(1000,563),(1000,534),(1130,534)],'V',1035,518)
    d.arrow([(890,598),(960,598),(960,670),(1130,670)],'L',1035,654)
    d.arrow([(480,350),(480,534)],heat=True)
    d.text(505,440,'仅传热 Q回收','small heat')
    d.text(505,471,'不跨壁交换物料','small heat')
    d.footer(['剩余服务：HP再沸器 ← 外部供热；HP净底 → 指定产品/跨塔边界。',
              '剩余服务：LP顶冷凝器 → 外部冷却；内部回流回LP，LP净顶产品 → 指定边界；原料入口另列。',
              '选完整外置替换时核HP冷凝、LP再沸的实际配置和级数映射；不重复保留同一相变负荷。',
              '核物性、全段温差、压降与返回压头；FLASH2只分相时不另加未记账热量；未核面积/持液/控制。'],
             'Aspen官方学习指南 p11（热曲线 / Reboiler Wizard）')
    d.save('01-once-through-kettle-local.svg')

def partial():
    d = Diagram('02  部分热回收：串联补冷 / 补热', '共享HX出口可以未完成相变；按实际焓路径分配回收与剩余公用工程负荷。')
    d.panel(166, 580, '同一 HX-DE 两侧只热耦合；trim按真实剩余负荷设置，不为凑图增加')
    d.box(50, 260, 205, 90, ['HP 总顶汽', 'V_HP · V'])
    d.box(340, 260, 205, 90, ['HX-DE 热侧', '出口可为 V+L'])
    d.box(655, 260, 215, 90, ['COOL-TRIM', '必要补冷 → 液体 L'])
    d.box(970, 260, 190, 90, ['FSPLIT-R', '仅液体分配'])
    d.box(1260, 210, 275, 85, ['R_HP · L', '→ 供压 → HP顶部'])
    d.box(1260, 355, 275, 80, ['D_HP · L', '→ 净产品边界'])
    d.arrow([(255,305),(340,305)],'V',288,288)
    d.arrow([(545,305),(655,305)],'V+L / L',558,245)
    d.arrow([(870,305),(970,305)],'L',905,288)
    d.arrow([(1160,286),(1210,286),(1210,253),(1260,253)])
    d.arrow([(1160,327),(1210,327),(1210,395),(1260,395)])
    d.text(660,395,'若补冷后仍含气：先FLASH2-H分相，液体再分配。','small')
    d.text(660,427,'气相 → 指定回收/尾气系统；FSPLIT不分相。','small')
    d.text(660,459,'共享HX已全凝时，不重复计“剩余冷凝”。','small')
    d.box(50, 555, 205, 90, ['LP 总底抽液', 'L_LP · L'])
    d.box(340, 555, 205, 90, ['HX-DE 冷侧', '受热出口 L / V+L'])
    d.box(655, 555, 215, 90, ['HEAT-TRIM', '必要补热 → V+L'])
    d.box(970, 555, 190, 90, ['FLASH2-K', '平衡分相近似'])
    d.box(1260, 500, 275, 85, ['V_LP · V', '→ LP下部汽相返回'])
    d.box(1260, 665, 275, 65, ['B_LP · L → 净底边界'])
    d.arrow([(255,600),(340,600)],'L',288,584)
    d.arrow([(545,600),(655,600)])
    d.arrow([(870,600),(970,600)],'V+L',888,584)
    d.arrow([(1160,578),(1210,578),(1210,542),(1260,542)])
    d.arrow([(1160,622),(1210,622),(1210,697),(1260,697)])
    d.arrow([(442,350),(442,555)],heat=True)
    d.text(275,470,'仅传热 Q回收','small heat')
    d.footer(['热账：HP冷凝总量 = 回收热 + 外部补冷；LP再沸总量 = 回收热 + 外部补热（以正的热量大小记）。',
              '剩余服务：HP再沸外部供热；LP顶冷凝外部冷却及内部回流；LP净顶、HP净底及原料边界另列。',
              '这是完整外置替换下的局部trim候选；不据此断言内外端器混合方案已成立。',
              '未核同案物性、温差、压头、负荷匹配、面积与产品指标；启动/备用职责另审。'],
             'Aspen官方学习指南 p11；连接细化卡 §8')
    d.save('02-partial-heat-recovery-local.svg')

def circulation():
    d = Diagram('03  LP冷侧循环：自然循环与强制循环', '两种替代方案，按所选结构分别审查；不表示在同一回路中同时安装。')
    for idx, (y, title, forced) in enumerate([(170,'A  自然循环热虹吸：无外部循环泵',False),(467,'B  强制循环：液体泵位于受热之前',True)]):
        d.panel(y, 275, title)
        cy=y+113
        d.box(50, cy, 240, 84, ['LP底部集液区', '总抽液 L'])
        d.box(390, cy, 190, 84, ['FSPLIT-B', '液体分流'])
        if forced:
            d.box(690, cy, 185, 84, ['PUMP-C', '液体循环泵 L'])
            d.box(975, cy, 195, 84, ['HX-DE 冷侧', 'L → V+L'])
            d.arrow([(580,cy+42),(690,cy+42)],'CIRC-L',597,cy+22)
            d.arrow([(875,cy+42),(975,cy+42)],'L',915,cy+22)
        else:
            d.box(975, cy, 195, 84, ['HX-DE 冷侧', 'L → V+L'])
            d.arrow([(580,cy+42),(975,cy+42)],'CIRC-L · 液体循环支路（无泵）',625,cy+22)
        d.box(1280, cy, 260, 84, ['V+L 两相返回', '→ LP下部接收/集液区'])
        d.arrow([(290,cy+42),(390,cy+42)],'L',334,cy+22)
        d.arrow([(1170,cy+42),(1280,cy+42)],'V+L',1192,cy+22)
        d.arrow([(485,cy+84),(485,cy+119),(820,cy+119)],'B_LP · L → 指定净底产品边界',835,cy+126)
        d.text(975,y+83,'热侧来源：HP总顶汽；仅跨壁传热','small heat')
    d.footer(['两图均：净底采出在循环受热前分配；HX两相出口回LP，不把全部两相物流称作净底产品。',
              '自然循环：须核液位、密度差、位差与全回路压降；画低位置或指定流量都不证明热虹吸成立。',
              '强制循环：须核入口液态/NPSH、泵压头与轴功；泵不代替HX热量；不得无据把泵移到两相出口后。',
              '范围外服务：HP冷凝回流/净顶分配、HP再沸供热/净底，LP顶冷凝/回流/净顶、原料与跨塔边界。'],
             'HTRI Demystifying Thermosiphon Operation；连接细化卡 §4–5')
    d.save('03-thermosiphon-vs-forced-circulation-local.svg')

if __name__ == '__main__':
    once_through(); partial(); circulation()
    for p in sorted(ROOT.glob('*.svg')):
        ET.parse(p)
        print(p.name)
