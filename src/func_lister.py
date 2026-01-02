import project_crawler
import os
from dataclasses import dataclass
from msl.odt import Document

@dataclass
class Description:
    name: str
    description: str
    params: list[str] | None
    returns: str | None
    file: str

@dataclass
class Table:
    names: list[str]
    params: list[str]
    returns: list[str]
    descriptions: list[str]

def new_table() -> Table:
    return Table(list(), list(), list(), list())

def add_row(table, description):
    table.names.append(description.name)

    if description.params is not None:
        str_params = [param_to_string(p) for p in description.params]
        table.params.append(", ".join(str_params))
    else:
        table.params.append("N/A")

    if description.returns is not None:
        table.returns.append(description.returns)
    else:
        table.returns.append("N/A")

    table.descriptions.append(description.description)

def get_data(table):
    return table.names, table.params, table.returns, table.descriptions

def process_doxygen(report):
    description = ""
    params = list()
    throws = list()
    returns = ""
    for line in report.doxygen_comment:
        if line.startswith("/**") or line.startswith(" */"):
            continue
        if line.startswith(" * "):
            line = line[3:]

        if line.startswith("@brief"):
            line = line.removeprefix("@brief")
            description += line
        elif line.startswith("@note"):
            line = line.removeprefix("@note")
            description += " NOTE:" + line
        elif line.startswith("@param"):
            params.append(line.removeprefix("@param ").removeprefix("@param[in] ").removeprefix("@param[out] ").removeprefix("@param[in/out] "))
        elif line.startswith("@throws"):
            throws.append(line.removeprefix("@throws "))
        elif line.startswith("@return"):
            returns = line.removeprefix("@return ").removeprefix("@returns ").removesuffix(".").removesuffix(". ")
        else:
            description += " " + line

    description.strip()

    returns += ": " + report.returns

    if report.returns in ("void", "exception", "", "tek_init"):
        returns = None

    len_params = len(params)
    r_params = list()
    if len_params == 0:
        params = None
    else:
        for param in report.params:
            if param.name != "<unknown>":
                r_params.append(param)

        if len(r_params) != len_params:
            for param in params:
                p_name = param.split(" ")[0]
                found = False
                for r_param in r_params:
                    if p_name == r_param.name:
                        found = True
                        break
                if not found:
                    r_params.append(project_crawler.Parameter(
                        name=p_name,
                        type="?"
                    ))

    return Description(
        name=report.name,
        description=description,
        params=r_params if len(r_params) > 0 else None,
        returns=returns,
        file=report.file
    )

def process_file(f_path, f_list, f_ignore):
    f_data = project_crawler.read_file(f_path)
    f_lines = f_data.split("\n")
    for i in range(len(f_lines)):
        report = project_crawler.generate_function_report(f_path, f_lines, i)
        if report is None:
            continue

        if project_crawler.generate_report_hash(report) in f_ignore:
            continue

        f_list.append(report)

def param_to_string(param):
    return f"{param.name}: {param.type}"

def create_document(function_list: list[Description], filename="res/test.odt"):
    doc = Document(filename)
    header_row = ["Name", "Parameters", "Return", "Description"]

    files = dict()

    for description in function_list:
        if description.file not in files:
            files[description.file] = new_table()

        add_row(files[description.file], description)

    for file, table in files.items():
        table_data = doc.maketabledata(*get_data(table), header_row=header_row)

        doc.addtext("\n" + os.path.basename(file).split(".")[0])
        doc.addtable(table_data, column_width=[3.5, 3.5, 3, 7])

def main():
    ignore = list()
    with open("res/ignorefile.txt") as f_ptr:
        ignorefile = f_ptr.read().split("\n")
    for line in ignorefile:
        ignore.append(line)

    file_tree = project_crawler.generate_file_tree(project_root=os.path.expanduser("~/CLionProjects/TekPhysics/"))

    file_queue = list()
    file_queue.append(file_tree)
    file_list: list[project_crawler.Report] = list()
    while len(file_queue) > 0:
        file_tree = file_queue.pop(-1)
        for file_name, file_data in file_tree.items():
            if type(file_data) == dict:
                file_queue.append(file_data)
            else:
                process_file(file_data, file_list, ignore)

    doxy_list = list()
    for file in file_list:
        doxy_list.append(process_doxygen(file))

    create_document(doxy_list)

if __name__ == "__main__":
    main()