#!/usr/bin/env python3
import os
from dataclasses import dataclass, field
from typing import Any, List
import yaml
from graphviz import Graph

COLOR_CODES = {'DIN': ['WH','BN','GN','YE','GY','PK','BU','RD','BK','VT'], # ,'GYPK','RDBU','WHGN','BNGN','WHYE','YEBN','WHGY','GYBN','WHPK','PKBN'],
               'IEC': ['BN','RD','OG','YE','GN','BU','VT','GY','WH','BK'],
               'BW':  ['BK','WH']}

color_hex = {
             'BK': '#000000',
             'WH': '#ffffff',
             'GY': '#999999',
             'PK': '#ff66cc',
             'RD': '#ff0000',
             'OG': '#ff8000',
             'YE': '#ffff00',
             'GN': '#00ff00',
             'TQ': '#00ffff',
             'BU': '#0066ff',
             'VT': '#8000ff',
             'BN': '#666600',
              }

color_full = {
             'BK': 'black',
             'WH': 'white',
             'GY': 'grey',
             'PK': 'pink',
             'RD': 'red',
             'OG': 'orange',
             'YE': 'yellow',
             'GN': 'green',
             'TQ': 'turquoise',
             'BU': 'blue',
             'VT': 'violet',
             'BN': 'brown',
}

color_ger = {
             'BK': 'sw',
             'WH': 'ws',
             'GY': 'gr',
             'PK': 'rs',
             'RD': 'rt',
             'OG': 'or',
             'YE': 'ge',
             'GN': 'gn',
             'TQ': 'tk',
             'BU': 'bl',
             'VT': 'vi',
             'BN': 'br',
}

class Harness:

    def __init__(self):
        self.color_mode = 'SHORT'
        self.nodes = {}
        self.cables = {}

    def add_node(self, name, *args, **kwargs):
        self.nodes[name] = Node(name, *args, **kwargs)

    def add_cable(self, name, *args, **kwargs):
        self.cables[name] = Cable(name, *args, **kwargs)

    def loop(self, node_name, from_pin, to_pin):
        self.nodes[node_name].loop(from_pin, to_pin)

    def connect(self, from_name, from_pin, via_name, via_pin, to_name, to_pin):
        self.cables[via_name].connect(from_name, from_pin, via_pin, to_name, to_pin)

    def create_graph(self):
        dot = Graph()
        dot.body.append('// Graph generated by WireViz')
        dot.body.append('// https://github.com/formatc1702/WireViz')
        font = 'arial'
        dot.attr('graph', rankdir='LR',
                          ranksep='2',
                          bgcolor='white',
                          nodesep='0.33',
                          fontname=font)
        dot.attr('node', shape='record',
                         style='filled',
                         fillcolor='white',
                         fontname=font)
        dot.attr('edge', style='bold',
                         fontname=font)

        # prepare ports on connectors depending on which side they will connect
        for k, c in self.cables.items():
            for x in c.connections:
                if x.from_port is not None: # connect to left
                    self.nodes[x.from_name].ports_right = True
                if x.to_port is not None: # connect to right
                    self.nodes[x.to_name].ports_left = True

        for k, n in self.nodes.items():
            if n.category == 'ferrule':
                infostring = '{type} {color}'.format(type=n.type,
                                                     color=translate_color(n.color, self.color_mode) if n.color else '')
                infostring_l = infostring if n.ports_right else ''
                infostring_r = infostring if n.ports_left else ''

                dot.node(k, shape='none',
                            style='filled',
                            margin='0',
                            orientation = '0' if n.ports_left else '180',
                            label='''<

                <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR>
                <TD PORT="p1l"> {infostring_l} </TD>
                {colorbar}
                <TD PORT="p1r"> {infostring_r} </TD>
                </TR></TABLE>


                >'''.format(infostring_l=infostring_l,
                            infostring_r=infostring_r,
                            colorbar='<TD BGCOLOR="{}" BORDER="1" SIDES="LR" WIDTH="4"></TD>'.format(translate_color(n.color, 'HEX')) if n.color else ''))
                # dot.node(k, label='{<p1l>A|B|{C|<p1r>D|E}}')
            else:
                # a = attributes
                a = [n.type,
                     n.gender,
                     '{}-pin'.format(len(n.pinout)) if n.show_num_pins else '']
                # p = pinout
                p = [[],[],[]]
                p[1] = list(n.pinout)
                for i, x in enumerate(n.pinout, 1):
                    if n.ports_left:
                        p[0].append('<p{portno}l>{portno}'.format(portno=i))
                    if n.ports_right:
                        p[2].append('<p{portno}r>{portno}'.format(portno=i))
                # l = label
                l = [n.name if n.show_name else '', a, p]
                dot.node(k, label=nested(l))

                if len(n.loops) > 0:
                    dot.attr('edge',color='#000000')
                    if n.ports_left:
                        loop_side = 'l'
                        loop_dir = 'w'
                    elif n.ports_right:
                        loop_side = 'r'
                        loop_dir = 'e'
                    else:
                        raise Exception('No side for loops')
                    for loop in n.loops:
                        dot.edge('{name}:p{port_from}{loop_side}:{loop_dir}'.format(name=n.name, port_from=loop[0], port_to=loop[1], loop_side=loop_side, loop_dir=loop_dir),
                                 '{name}:p{port_to}{loop_side}:{loop_dir}'.format(name=n.name, port_from=loop[0], port_to=loop[1], loop_side=loop_side, loop_dir=loop_dir))

        for k, c in self.cables.items():
            # a = attributes
            a = ['{}x'.format(len(c.colors)) if c.show_num_wires else '',
                 '{} mm\u00B2{}'.format(c.mm2, ' ({} AWG)'.format(awg_equiv(c.mm2)) if c.show_equiv else '') if c.mm2 is not None else '',
                 c.awg,
                 '+ S' if c.shield else '',
                 '{} m'.format(c.length) if c.length > 0 else '']
            # print(a)
            a = list(filter(None, a))
            # print(a)

            html = '<table border="0" cellspacing="0" cellpadding="0"><tr><td>' # main table

            html = html + '<table border="0" cellspacing="0" cellpadding="3" cellborder="1">' # name+attributes table
            if (not c.show_name) or c.type != 'bundle':
                html = html + '<tr><td colspan="{colspan}">{name}</td></tr>'.format(colspan=len(a), name=c.name)
            html = html + '<tr>' # attribute row
            for attrib in a:
                html = html + '<td>{attrib}</td>'.format(attrib=attrib)
            html = html + '</tr>' # attribute row
            html = html + '</table></td></tr>' # name+attributes table

            html = html + '<tr><td>&nbsp;</td></tr>' # spacer between attributes and wires

            html = html + '<tr><td><table border="0" cellspacing="0" cellborder="0">' # conductor table

            for i, x in enumerate(c.colors,1):
                p = []
                p.append('<!-- {}_in -->'.format(i))
                p.append(translate_color(x, self.color_mode))
                p.append('<!-- {}_out -->'.format(i))
                html = html + '<tr>'
                for bla in p:
                    html = html + '<td>{}</td>'.format(bla)
                html = html + '</tr>'
                html = html + '<tr><td colspan="{colspan}" cellpadding="0" height="6" bgcolor="{bgcolor}" border="2" sides="tb" port="{port}"></td></tr>'.format(colspan=len(p), bgcolor=translate_color(x, 'hex'), port='w{}'.format(i))

            if c.shield:
                p = ['<!-- s_in -->', 'Shield', '<!-- s_out -->']
                html = html + '<tr><td>&nbsp;</td></tr>' # spacer
                html = html + '<tr>'
                for bla in p:
                    html = html + '<td>{}</td>'.format(bla)
                html = html + '</tr>'
                html = html + '<tr><td colspan="{colspan}" cellpadding="0" height="6" border="2" sides="b" port="{port}"></td></tr>'.format(colspan=len(p), bgcolor=translate_color(x, 'hex'), port='ws')

            html = html + '<tr><td>&nbsp;</td></tr>' # spacer at the end

            html = html + '</table>' # conductor table

            html = html + '</td></tr></table>'  # main table

            # print(html)

            # connections
            for x in c.connections:
                if isinstance(x.via_port, int): # check if it's an actual wire and not a shield
                    search_color = c.colors[x.via_port-1]
                    if search_color in color_hex:
                        dot.attr('edge',color='#000000:{wire_color}:#000000'.format(wire_color=color_hex[search_color]))
                    else: # color name not found
                        dot.attr('edge',color='#000000')
                else: # it's a shield connection
                    dot.attr('edge',color='#000000')

                if x.from_port is not None: # connect to left
                    from_ferrule = self.nodes[x.from_name].category is 'ferrule'
                    code_left_1 = '{from_name}{from_port}:e'.format(from_name=x.from_name, from_port=':p{}r'.format(x.from_port) if not from_ferrule else '')
                    code_left_2 = '{via_name}:w{via_wire}:w'.format(via_name=c.name, via_wire=x.via_port, via_subport='i' if c.show_pinout else '')
                    dot.edge(code_left_1, code_left_2)
                    from_string = '{}:{}'.format(x.from_name, x.from_port) if not from_ferrule else ''
                    html = html.replace('<!-- {}_in -->'.format(x.via_port), from_string)
                if x.to_port is not None: # connect to right
                    to_ferrule = self.nodes[x.to_name].category is 'ferrule'
                    code_right_1 = '{via_name}:w{via_wire}:e'.format(via_name=c.name, via_wire=x.via_port, via_subport='o' if c.show_pinout else '')
                    code_right_2 = '{to_name}{to_port}:w'.format(to_name=x.to_name, to_port=':p{}l'.format(x.to_port) if not to_ferrule else '')
                    dot.edge(code_right_1, code_right_2)
                    to_string = '{}:{}'.format(x.to_name, x.to_port) if not to_ferrule else ''
                    html = html.replace('<!-- {}_out -->'.format(x.via_port), to_string)

            dot.node(c.name, label='<{html}>'.format(html=html), shape='box', style='filled,dashed' if c.type=='bundle' else '', margin='0', fillcolor='white')

        return dot

    def output(self, filename, directory='_output', view=False, cleanup=True, format='pdf'):
        d = self.create_graph()
        for f in format:
            d.format = f
            d.render(filename=filename, directory=directory, view=view, cleanup=cleanup)
        d.save(filename='{}.gv'.format(filename), directory=directory)

@dataclass
class Node:
    name: str
    category: str = None
    type: str = None
    gender: str = None
    num_pins: int = None
    pinout: List[Any] = field(default_factory=list)
    color: str = None
    show_name: bool = True
    show_num_pins: bool = True

    def __post_init__(self):
        self.ports_left = False
        self.ports_right = False
        self.loops = []

        if self.pinout:
            if self.num_pins is not None:
                raise Exception('You cannot specify both pinout and num_pins')
        else:
            if not self.num_pins:
                self.num_pins = 1
            self.pinout = ['',] * self.num_pins

    def loop(self, from_pin, to_pin):
        self.loops.append((from_pin, to_pin))

@dataclass
class Cable:
    name: str
    type: str = None
    mm2: float = None
    awg: int = None
    show_equiv: bool = False
    length: float = 0
    num_wires: int = None
    shield: bool = False
    colors: List[Any] = field(default_factory=list)
    color_code: str = None
    show_name: bool = True
    show_pinout: bool = False
    show_num_wires: bool = True

    def __post_init__(self):
        if self.mm2 and self.awg:
            raise Exception('You cannot define both mm2 and awg!')
        self.connections = []

        if self.num_wires: # number of wires explicitly defined
            if self.colors: # use custom color palette (partly or looped if needed)
                pass
            elif self.color_code: # use standard color palette (partly or looped if needed)
                if self.color_code not in COLOR_CODES:
                    raise Exception('Unknown color code')
                self.colors = COLOR_CODES[self.color_code]
            else: # no colors defined, add dummy colors
                self.colors = [''] * self.num_wires

            # make color code loop around if more wires than colors
            if self.num_wires > len(self.colors):
                 m = self.num_wires // len(self.colors) + 1
                 self.colors = self.colors * int(m)
            # cut off excess after looping
            self.colors = self.colors[:self.num_wires]

        else: # num_wires implicit in length of color list
            if not self.colors:
                raise Exception('Unknown number of wires. Must specify num_wires or colors (implicit length)')
            self.num_wires = len(self.colors)

    def connect(self, from_name, from_pin, via_pin, to_name, to_pin):
        from_pin = int2tuple(from_pin)
        via_pin  = int2tuple(via_pin)
        to_pin   = int2tuple(to_pin)
        if len(from_pin) != len(to_pin):
            raise Exception('from_pin must have the same number of elements as to_pin')
        for i, x in enumerate(from_pin):
            # self.connections.append((from_name, from_pin[i], via_pin[i], to_name, to_pin[i]))
            self.connections.append(Connection(from_name, from_pin[i], via_pin[i], to_name, to_pin[i]))

@dataclass
class Connection:
    from_name: Any
    from_port: Any
    via_port:  Any
    to_name:   Any
    to_port:   Any

def nested(input):
    l = []
    for x in input:
        if isinstance(x, list):
            if len(x) > 0:
                n = nested(x)
                if n != '':
                    l.append('{' + n + '}')
        else:
            if x is not None:
                if x != '':
                    l.append(str(x))
    s = '|'.join(l)
    return s

def int2tuple(input):
    if isinstance(input, tuple):
        output = input
    else:
        output = (input,)
    return output

def translate_color(input, color_mode):
    if input == '':
        output = ''
    else:
        if color_mode == 'full':
            output = color_full[input].lower()
        elif color_mode == 'FULL':
            output = color_full[input].upper()
        elif color_mode == 'hex':
            output = color_hex[input].lower()
        elif color_mode == 'HEX':
            output = color_hex[input].upper()
        elif color_mode == 'ger':
            output = color_ger[input].lower()
        elif color_mode == 'GER':
            output = color_ger[input].upper()
        elif color_mode == 'short':
            output = input.lower()
        elif color_mode == 'SHORT':
            output = input.upper()
        else:
            raise Exception('Unknown color mode')
    return output

def awg_equiv(mm2):
    awg_equiv_table = {
                        '0.09': 28,
                        '0.14': 26,
                        '0.25': 24,
                        '0.34': 22,
                        '0.5': 21,
                        '0.75': 20,
                        '1': 18,
                        '1.5': 16,
                        '2.5': 14,
                        '4': 12,
                        '6': 10,
                        '10': 8,
                        '16': 6,
                        '25': 4,
                        }
    k = str(mm2)
    if k in awg_equiv_table:
        return awg_equiv_table[k]
    else:
        return None

def parse(file_in, file_out=None):

    file_in = os.path.abspath(file_in)
    if not file_out:
        file_out = file_in
        pre, ext = os.path.splitext(file_out)
        file_out = pre # extension will be added by graphviz output function
    file_out = os.path.abspath(file_out)

    with open(file_in, 'r') as stream:
        try:
            input = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    def expand(input):
        # input can be:
        # - a singleton (normally str or int)
        # - a list of str or int
        # if str is of the format '#-#', it is treated as a range (inclusive) and expanded
        output = []
        if not isinstance(input, list):
            input = [input,]
        for e in input:
            e = str(e)
            if '-' in e: # list of pins
                a, b = tuple(map(int, e.split('-')))
                if a < b:
                    for x in range(a,b+1):
                        output.append(x)
                elif a > b:
                    for x in range(a,b-1,-1):
                        output.append(x)
                elif a == b:
                    output.append(a)
            else:
                try:
                    x = int(e)
                except:
                    x = e
                output.append(x)
        return output

    def check_designators(what, where):
        for i, x in enumerate(what):
            # print('Looking for {} in {}'.format(x,where[i]))
            if x not in input[where[i]]:
                return False
        return True

    h = Harness()

    # add items
    sections = ['nodes','wires','ferrules','connections']
    types    = [dict, dict, dict, list]
    for sec, ty in zip(sections, types):
        if sec in input and type(input[sec]) == ty:
            if len(input[sec]) > 0:
                if ty == dict:
                    for k, o in input[sec].items():
                        if sec == 'nodes':
                            h.add_node(name=k, **o)
                        elif sec == 'wires':
                            h.add_cable(name=k, **o)
                        elif sec == 'ferrules':
                            pass
                            # h.add_node(name=k, category='ferrule', **o)
            else:
                print('{} section empty'.format(sec))
        else:
            print('No {} section found'.format(sec))
            if ty == dict:
                input[sec] = {}
            elif ty == list:
                input[sec] = []

    # add connections
    ferrule_counter = 0
    for con in input['connections']:
        if len(con) == 3: # format: connector -- wire -- conector

            for c in con:
                if len(list(c.keys())) != 1: # check that each entry in con has only one key, which is the designator
                    raise Exception('Too many keys')

            from_name = list(con[0].keys())[0]
            via_name  = list(con[1].keys())[0]
            to_name   = list(con[2].keys())[0]

            if not check_designators([from_name,via_name,to_name],('nodes','wires','nodes')):
                raise Exception('Bad connection definition (3)')

            from_pins = expand(con[0][from_name])
            via_pins  = expand(con[1][via_name])
            to_pins   = expand(con[2][to_name])

            if len(from_pins) != len(via_pins) or len(via_pins) != len(to_pins):
                raise Exception('List length mismatch')

            for (from_pin, via_pin, to_pin) in zip(from_pins, via_pins, to_pins):
                h.connect(from_name, from_pin, via_name, via_pin, to_name, to_pin)

        elif len(con) == 2:

            for c in con:
                if type(c) is dict:
                    if len(list(c.keys())) != 1: # check that each entry in con has only one key, which is the designator
                        raise Exception('Too many keys')

            # hack to make the format for ferrules compatible with the formats for connectors and wires
            if type(con[0]) == str:
                name = con[0]
                con[0] = {}
                con[0][name] = name
            if type(con[1]) == str:
                name = con[1]
                con[1] = {}
                con[1][name] = name

            from_name = list(con[0].keys())[0]
            to_name   = list(con[1].keys())[0]

            n_w = check_designators([from_name, to_name],('nodes','wires'))
            w_n = check_designators([from_name, to_name],('wires','nodes'))
            n_n = check_designators([from_name, to_name],('nodes','nodes'))


            f_w = check_designators([from_name, to_name],('ferrules','wires'))
            w_f = check_designators([from_name, to_name],('wires','ferrules'))

            if not n_w and not w_n and not n_n and not f_w and not w_f:
                raise Exception('Wrong designators')

            from_pins = expand(con[0][from_name])
            to_pins  = expand(con[1][to_name])

            if n_w or w_n or n_n:
                if len(from_pins) != len(to_pins):
                    raise Exception('List length mismatch')

            if n_w or w_n:
                for (from_pin, to_pin) in zip(from_pins, to_pins):
                    if n_w:
                        h.connect(from_name, from_pin, to_name, to_pin, None, None)
                    else: # w_n
                        h.connect(None, None, from_name, from_pin, to_name, to_pin)
            elif n_n:
                con_name  = list(con[0].keys())[0]
                from_pins = expand(con[0][from_name])
                to_pins   = expand(con[1][to_name])

                for (from_pin, to_pin) in zip(from_pins, to_pins):
                    h.loop(con_name, from_pin, to_pin)
            if f_w or w_f:
                from_pins = expand(con[0][from_name])
                to_pins   = expand(con[1][to_name])

                if f_w:
                    ferrule_name = from_name
                    wire_name = to_name
                    wire_pins = to_pins
                else:
                    ferrule_name = to_name
                    wire_name = from_name
                    wire_pins = from_pins

                ferrule_params = input['ferrules'][ferrule_name]
                for wire_pin in wire_pins:
                    ferrule_counter = ferrule_counter + 1
                    ferrule_id = 'F{}'.format(ferrule_counter)
                    h.add_node(ferrule_id, category='ferrule', **ferrule_params)

                    if f_w:
                        h.connect(ferrule_id, 1, wire_name, wire_pin, None, None)
                    else:
                        h.connect(None, None, wire_name, wire_pin, ferrule_id, 1)


        else:
            raise Exception('Wrong number of connection parameters')

    h.output(filename=file_out, format=('png','svg'), view=False)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('file_input', nargs='?', default='_test/test.yml')
    ap.add_argument('file_output', nargs='?', default=None)
    args = ap.parse_args()

    parse(args.file_input, args.file_output)
