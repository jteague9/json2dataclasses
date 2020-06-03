from importlib.util import spec_from_file_location, module_from_spec
import json
import keyword
import main
import os
import pytest


@pytest.fixture
def github_json():
    with open('test/github.json') as file:
        m = json.load(file)
    return m


@pytest.fixture
def articles_json():
    with open('test/articles.json') as file:
        m = json.load(file)
    return m


@pytest.fixture
def errors_json():
    with open('test/errors.json') as file:
        m = json.load(file)
    return m


@pytest.fixture
def name():
    return "Test"


@pytest.fixture
def data_dict():
    return {"field1": {'field2': {"field3": "fin"}}}


@pytest.fixture
def data_list():
    return [{"field1": {'field2': {"field3": "fin1"}}}, {"field1": {'field2': {"field3": "fin2"}}}]


@pytest.fixture
def empty_list_dict():
    return {"members": []}


def test_get_base_node_dict(name, data_dict):
    node = main.get_base_node(name, data_dict)
    assert node.data == data_dict
    assert node.type == name.capitalize()


def test_get_base_node_list(name, data_list):
    node = main.get_base_node(name, data_list)
    assert node.data == data_list
    assert node.type == "list"
    assert node.subtype == name.capitalize()


def test_get_base_node_empty_list_dict(name, empty_list_dict):
    node = main.get_base_node(name, empty_list_dict)
    assert node.data == empty_list_dict
    assert node.type == name.capitalize()


def test_get_base_node_reserved_name(data_dict):
    for reserved_name in keyword.kwlist:
        node = main.get_base_node(reserved_name, data_dict)
        assert node.data == data_dict
        assert node.type != reserved_name.capitalize()


def test_node_generator(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    names = ['str', 'Field2', 'Field1', 'Test']
    count = len(names)
    for n in main.node_generator(node, head_first=False):
        assert n.type == names.pop(0)
        count -= 1
    assert count == 0


def test_node_generator_reverse(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    names = ['Test', 'Field1', 'Field2', 'str']
    count = len(names)
    for n in main.node_generator(node, head_first=True):
        assert n.type == names.pop(0)
        count -= 1
    assert count == 0


def test_build_tree_dict(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    s_node = node.subnodes[0].subnodes[0].subnodes[0]
    assert s_node.name == "field3"
    assert s_node.parent.name == "field2"
    assert s_node.parent.parent.name == "field1"
    assert s_node.parent.parent.parent.parent is None
    assert s_node.data == "fin"


def test_build_tree_list(name, data_list):
    node = main.get_base_node(name, data_list)
    main.build_tree(node)
    s_node = node.subnodes[0].subnodes[0].subnodes[0].subnodes[0]
    assert s_node.name == "field3"
    assert s_node.parent.name == "field2"
    assert s_node.parent.parent.name == "field1"
    assert s_node.parent.parent.parent.parent.parent is None
    assert s_node.data == "fin1"


def test_build_tree_empty_list_dict(name, empty_list_dict):
    node = main.get_base_node(name, empty_list_dict)
    main.build_tree(node)
    assert node.subnodes[0].name == "members"


def test_get_node_class(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    s_node = node.subnodes[0].subnodes[0]
    assert main.get_node_class(s_node) == "@dataclass\nclass Field2:\n\tfield3: str = None\n\n\n"
    assert main.get_node_class(s_node.parent) == "@dataclass\nclass Field1:\n\tfield2: Field2 = None\n\n\n"


def test_get_node_classes(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    expected = "@dataclass\nclass Field2:\n\tfield3: str = None\n\n\n" \
               "@dataclass\nclass Field1:\n\tfield2: Field2 = None\n\n\n" \
               "@dataclass\nclass Test:\n\tfield1: Field1 = None\n\n\n"
    assert main.get_node_classes(node) == expected


def test_get_node_classes_empty_list_dict(name, empty_list_dict):
    node = main.get_base_node(name, empty_list_dict)
    main.build_tree(node)
    assert main.get_node_classes(node) == "@dataclass\nclass Test:\n\tmembers: List[Any] = " \
                                          "field(default_factory=list)\n\n\n"


def test_get_node_definition(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    assert main.get_node_definition(node) == "Test(field1=Field1(field2=Field2(field3=response.get('field1', " \
                                             "{}).get('field2', {}).get('field3'),),),)"


def test_get_node_definition_empty_list_dict(name, empty_list_dict):
    node = main.get_base_node(name, empty_list_dict)
    main.build_tree(node)
    assert main.get_node_definition(node) == "Test(members=[any for any in response.get('members', [])],)"


def test_get_object_node(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    s_node = node.subnodes[0]
    assert main.get_object_node_definition(s_node) == "Field1(field2=Field2(field3=response.get('field1', " \
                                                      "{}).get('field2', {}).get('field3'),),)"


def test_get_list_node(name, data_list):
    node = main.get_base_node(name, data_list)
    main.build_tree(node)
    assert main.get_list_node_definition(node) == "[Test(field1=Field1(field2=Field2(field3=test.get('field1', " \
                                                  "{}).get('field2', {}).get('field3'),),),) for test in response]"


def test_get_basic_node(name, data_dict):
    node = main.get_base_node(name, data_dict)
    main.build_tree(node)
    s_node = node.subnodes[0].subnodes[0].subnodes[0]
    assert main.get_basic_node_definition(s_node) == "response.get('field1', {}).get('field2', {}).get('field3')"


@pytest.mark.slow
def test_build_translate_example(articles_json, tmp_path):
    final = main.build_dataclass_from_data("Example", articles_json)
    module_name = "Articles"
    d = tmp_path / (module_name + ".py")
    d.write_text(final)
    spec = spec_from_file_location(module_name, d)
    out = module_from_spec(spec)
    spec.loader.exec_module(out)
    example = out.translate(articles_json)
    assert example.data[0].type == articles_json['data'][0]['type']


@pytest.mark.slow
def test_build_translate_example(github_json, tmp_path):
    final = main.build_dataclass_from_data("EventList", github_json)
    module_name = "eventlist"
    d = tmp_path / (module_name + ".py")
    d.write_text(final)
    spec = spec_from_file_location(module_name, d)
    out = module_from_spec(spec)
    spec.loader.exec_module(out)
    eventlist = out.translate(articles_json)
    assert eventlist[0].type == github_json[0]['type']
    assert eventlist[1].actor.id == github_json[1]['actor']['id']


@pytest.mark.slow
def test_build_translate_example(errors_json, tmp_path):
    final = main.build_dataclass_from_data("Example", errors_json)
    module_name = "Errors"
    d = tmp_path / (module_name + ".py")
    d.write_text(final)
    spec = spec_from_file_location(module_name, d)
    out = module_from_spec(spec)
    spec.loader.exec_module(out)
    example = out.translate(errors_json)
    assert example.errors[0].status == errors_json['errors'][0]['status']
    assert example.errors[1].source.pointer == errors_json['errors'][1]['source']['pointer']


@pytest.mark.slow
def test_cli_run(tmp_path, articles_json):
    module_name = "Articles"
    fileloc = tmp_path / (module_name + ".py")
    res = os.system(f"python main.py -f test/articles.json -n {module_name} -o {fileloc}")
    assert res == 0
    spec = spec_from_file_location(module_name, fileloc)
    out = module_from_spec(spec)
    spec.loader.exec_module(out)
    articles = out.translate(articles_json)
    assert articles.data[0].type == articles_json['data'][0]['type']
