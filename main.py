import argparse
import autopep8
import json
from dataclasses import dataclass, field
from typing import Any, Union
import keyword

keywords = [word.lower() for word in keyword.kwlist]


def main():
    parser = argparse.ArgumentParser(description='Build dataclasses from example json.')
    parser.add_argument('--name', '-n', help='name of structure')
    parser.add_argument('--filename', '-f', help='filename of input')
    parser.add_argument('--text', '-t', help='text input')
    parser.add_argument('--output', '-o', help='output destination file')
    args = parser.parse_args()

    filename = args.filename
    text = args.text
    name = args.name
    output = args.output

    data = None
    if filename:
        with open(filename) as file:
            data = json.load(file)
    elif text:
        data = json.loads(text)
    else:
        print("enter filename or text")
        exit(1)

    if name is None:
        print("include a name")
        exit(1)

    res = build_dataclass_from_data(name, data)
    res = autopep8.fix_code(res)
    with open(output, 'w') as file:
        print(file.write(res))


@dataclass
class Node:
    parent: Union['Node', None]
    data: Any
    type: str
    subtype: str = None
    name: str = None
    subnodes: list = field(default_factory=list)
    type_: str = field(init=False, repr=False)

    @property
    def type(self) -> str:
        return self.type_

    @type.setter
    def type(self, v: str):
        self.type_ = v if v.lower() not in keywords else v + "_"


def node_generator(node, head_first=False):
    if head_first:
        yield node
    for s in node.subnodes:
        for n in node_generator(s, head_first=head_first):
            yield n
    if not head_first:
        yield node


def get_base_node(name, data):
    if type(data) is list:
        type_ = "list"
    else:
        type_ = name.capitalize()

    node = Node(None, type=type_, data=data, subtype=name)
    return node


def build_tree(node):
    type_ = type(node.data).__name__
    if type_ == "list":
        if len(node.data) == 0:
            new_node = Node(node, type="Any", data=None)
            node.subtype = "Any"
            node.subnodes.append(new_node)
        else:
            value = node.data[0]
            new_type = type(value).__name__
            if new_type == "dict":
                if node.name is not None:
                    new_type = node.name.capitalize()
                    if new_type[-1:] == 's':
                        new_type = new_type[:-1]
                else:
                    new_type = node.subtype.capitalize()
            new_node = Node(node, type=new_type, data=value)
            node.subtype = new_type
            node.subnodes.append(new_node)
            build_tree(new_node)
    elif type_ == "dict":
        for key, value in node.data.items():
            new_type = type(value).__name__
            if new_type == "dict":
                new_type = key.capitalize()
            new_node = Node(node, type=new_type, name=key, data=value)
            node.subnodes.append(new_node)
            build_tree(new_node)


def get_node_class(node):
    content = "@dataclass\n"
    content += f"class {node.type}:\n"
    for n in node.subnodes:
        if n.type == "NoneType":
            content += f"\t{n.name}: Any = None\n"
        elif n.type == "list":
            content += f"\t{n.name}: List[{n.subtype}] = field(default_factory=list)\n"
        else:
            content += f"\t{n.name}: {n.type} = None\n"
    if len(node.subnodes) == 0:
        content += "\tpass\n"
    return content + '\n\n'


def get_node_classes_list(node):
    content = list()
    for s_node in node.subnodes:
        content += get_node_classes_list(s_node)
    if node.type not in ['int', 'bool', 'float', 'str', 'NoneType', 'list', 'Any']:
        content.append(get_node_class(node))
    return content


def get_node_classes(node):
    class_list = get_node_classes_list(node)
    unique_list = list()
    for class_ in class_list:
        if class_ not in unique_list:
            unique_list.append(class_)
    return ''.join(unique_list)


def get_basic_node_definition(node, var=None):
    content = f".get('{node.name}')"
    parent = node.parent
    while parent is not None and parent.type != "list":
        if parent.name:
            content = f".get('{parent.name}', {{}})" + content
        parent = parent.parent
    if parent is None:
        var = var or "response"
        content = var + content
    elif parent.type == "list":
        var = var
        content = var + content
    return content


def get_object_node_definition(node, var=None):
    content = f"{node.type}("
    for s in node.subnodes:
        content += f"{s.name}={get_node_definition(s, var)},"
    content += ")"
    return content


def get_list_node_definition(node, var=None):
    nvar = node.subtype.lower()
    if node.parent:
        baselist = f".get('{node.name}', [])"
    else:
        baselist = ""
    parent = node.parent
    while parent is not None and parent.type != "list":
        if parent.name:
            baselist = f".get('{parent.name}', {{}})" + baselist
        parent = parent.parent
    if parent is None:
        baselist = "response" + baselist
    elif parent.type == "list":
        baselist = var + baselist
    content = f"[{get_node_definition(node.subnodes[0], nvar)} for {nvar} in {baselist}]"
    return content


def get_node_definition(node, var=None):
    if node.type in ['str', 'int', 'float', 'bool', 'NoneType']:
        return get_basic_node_definition(node, var)
    elif node.type == "list":
        return get_list_node_definition(node, var)
    elif node.type == "Any":  # special case for a json file containing an empty list we can't infer about
        return "any"
    else:
        return get_object_node_definition(node, var)


def build_dataclass_from_data(name, data):
    base_node = get_base_node(name, data)
    build_tree(base_node)
    specify_duplicate_types(base_node)
    models = get_node_classes(base_node)
    translate_line = get_node_definition(base_node)
    translate_func = f"def translate(response):\n\treturn {translate_line}\n"
    header = "from dataclasses import dataclass, field\nfrom typing import List"
    if "Any" in models:
        header += ", Any"
    header += '\n\n\n'
    result = header + models + translate_func
    return result


def specify_duplicate_types(base_node):
    type_list = [node.type for node in node_generator(base_node)]
    basic_types = ['str', 'int', 'float', 'bool', 'NoneType', 'Any', 'list']
    dup_types = [type_ for type_ in type_list if type_ not in basic_types and type_list.count(type_) > 1]
    for n in node_generator(base_node):
        if n.type in dup_types and n.parent is not None:
            if n.parent.type == "list":
                n.type = f"{n.parent.subtype.capitalize()}{n.type.capitalize()}"
                n.parent.subtype = n.type
            else:
                n.type = f"{n.parent.type.capitalize()}{n.type.capitalize()}"


if __name__ == "__main__":
    main()
